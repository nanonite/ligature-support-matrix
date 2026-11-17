#!/usr/bin/env python3
"""Reusable per-root setup smoke check for the four P4 mixed-verifier roots.

Chainlink issue #177. This checker is read-only: it never creates, edits, or
deletes project files. It validates a root against the setup manifest produced
for #177 and prints a machine-readable result with --json.

Usage:
  smoke_check.py --plan [--manifest PATH]
  smoke_check.py --root PATH [--manifest PATH] [--json] [--hash-protected]

Checks in root mode:
  * the root is an independent Git work-tree root;
  * project-descriptor.json parses, names the root, declares the expected
    independent Cargo roots, and carries an allowed/protected write set;
  * the root-local Ligature bundle is present and its SHA256SUMS verify;
  * upstream/upstream-pin.json records the immutable pin from the manifest;
  * every verifier has its own Cargo.toml, Cargo.lock, rust-toolchain.toml,
    .cargo/config.toml, and no repository-local target/ tree;
  * oracle/, findings/limitations.jsonl, PORT-GAPS.md, and per-tool durable
    analysis results roots exist;
  * no Cargo target directory is shared by configuration.

Exit status is 0 only when there are no failed checks. Warnings are reported
but do not fail by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "protected-paths.json"
TIERS = {"operator", "human", "sanctioned", "worker"}
GRANTS = {"none", "required"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class Result:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, name: str, ok: bool, detail: str, warning: bool = False) -> None:
        self.checks.append(
            {"check": name, "status": "warn" if warning else ("pass" if ok else "fail"), "detail": detail}
        )

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if c["status"] == "fail"]

    @property
    def warnings(self) -> list[dict]:
        return [c for c in self.checks if c["status"] == "warn"]


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=120
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - environment failure
        return 127, str(exc)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_plan(manifest: dict) -> Result:
    result = Result()
    roots = manifest.get("roots", [])
    result.add("four planned roots", len(roots) == 4, f"found {len(roots)} roots")
    names = [r.get("root", "") for r in roots]
    expected = {
        "icl-creusot-verus",
        "tinyxml2-creusot-kani",
        "snappy-verus-kani",
        "leveldb-three-verifiers",
    }
    result.add("planned root names", set(names) == expected, ", ".join(names))

    catalog = manifest.get("route_catalog", {})
    for root in roots:
        rname = root.get("root", "<unnamed>")
        upstream = root.get("upstream", {})
        result.add(
            f"{rname}: immutable 40-hex pin",
            bool(HEX40.match(str(upstream.get("commit", "")))),
            str(upstream.get("commit")),
        )
        verifiers = root.get("verifiers", [])
        crates = root.get("crates", [])
        crate_verifiers = [c.get("verifier") for c in crates]
        result.add(
            f"{rname}: one independent Cargo root per verifier",
            sorted(crate_verifiers) == sorted(verifiers) and len(crates) == len(verifiers),
            f"verifiers={verifiers} crates={crate_verifiers}",
        )
        for c in crates:
            result.add(
                f"{rname}/{c.get('crate')}: crate name matches directory",
                c.get("crate") == Path(c.get("dir", "")).name,
                f"{c.get('crate')} vs {c.get('dir')}",
            )
            result.add(
                f"{rname}/{c.get('crate')}: pinned toolchain matches verifier",
                c.get("toolchain", {}).get("rust_channel")
                == manifest.get("toolchains", {}).get(c.get("verifier"), {}).get("rust_channel"),
                str(c.get("toolchain", {})),
            )

        write_set = root.get("proposed_write_set", {})
        allowed = set(write_set.get("allowed_roots", []))
        protected = set(write_set.get("protected_roots", []))
        result.add(
            f"{rname}: allowed/protected roots do not overlap exactly",
            not (allowed & protected),
            f"overlap={sorted(allowed & protected)}",
        )
        result.add(
            f"{rname}: root-level Cargo.toml is protected",
            "Cargo.toml" in protected,
            "root-level Cargo.toml must stay operator-managed",
        )
        targets = root.get("target_roots", {})
        result.add(
            f"{rname}: all build targets live under /tmp",
            bool(targets) and all(str(p).startswith("/tmp/") for p in targets.values()),
            str(targets),
        )
        proofs = root.get("proof_output_roots", {})
        result.add(
            f"{rname}: per-tool proof roots are distinct",
            len(set(proofs.values())) == len(proofs),
            str(proofs),
        )
        paths = root.get("paths", [])
        bad_paths = [
            p for p in paths if p.get("tier") not in TIERS or p.get("route") not in catalog
        ]
        result.add(
            f"{rname}: every enumerated path has a tier and creation route",
            not bad_paths,
            f"{len(paths)} paths; bad={bad_paths[:2]}",
        )
        bad_grants = [p for p in paths if p.get("grant") not in GRANTS]
        result.add(f"{rname}: every path declares grant status", not bad_grants, str(bad_grants[:2]))
        ungranted_protected = [
            p
            for p in paths
            if p.get("tier") in {"operator", "human", "sanctioned"}
            and p.get("route")
            in {
                "operator-ligature-bundle",
                "operator-source-pin",
                "sanctioned-scaffold-crate",
                "sanctioned-configure-crate-verus",
            }
            and p.get("grant") != "required"
        ]
        result.add(
            f"{rname}: grant-bearing creation routes are marked required",
            not ungranted_protected,
            str(ungranted_protected[:2]),
        )

    shared = manifest.get("shared_rules", {})
    result.add(
        "no flake edit rule recorded",
        "flake.nix" in shared.get("no_flake_edit", ""),
        shared.get("no_flake_edit", ""),
    )
    result.add(
        "baseline roots preserved",
        set(manifest.get("baseline_roots_preserved", []))
        == {"date-creusot/", "swisstable-verus/", "crypto-mixed/"},
        str(manifest.get("baseline_roots_preserved")),
    )
    result.add(
        "no path grants claimed",
        manifest.get("no_path_grants_issued") is True,
        str(manifest.get("no_path_grants_issued")),
    )
    return result


def read_toolchain_channel(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'^\s*channel\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def read_cargo_package_name(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^\s*name\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
    return match.group(1) if match else None


def check_root(root: Path, root_spec: dict, hash_protected: bool) -> Result:
    result = Result()
    root = root.resolve()
    rname = root_spec.get("root", root.name)
    result.add("root directory exists", root.is_dir(), str(root))
    if not root.is_dir():
        return result

    # Independent Git root.
    code, out = run(["git", "-C", str(root), "rev-parse", "--show-toplevel"])
    result.add(
        "independent Git work-tree root",
        code == 0 and Path(out).resolve() == root,
        out if code == 0 else f"git rev-parse failed: {out}",
    )
    code, out = run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"])
    result.add("git work-tree", code == 0 and out == "true", out)

    # Descriptor.
    descriptor_path = root / "project-descriptor.json"
    descriptor = None
    if descriptor_path.is_file():
        try:
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            result.add("descriptor parses", True, str(descriptor_path))
        except (OSError, json.JSONDecodeError) as exc:
            result.add("descriptor parses", False, str(exc))
    else:
        result.add("descriptor exists", False, str(descriptor_path))
    if descriptor:
        result.add(
            "descriptor project name matches root",
            descriptor.get("project", {}).get("name") == rname,
            str(descriptor.get("project", {}).get("name")),
        )
        declared = {
            entry.get("crate_dir")
            for entry in descriptor.get("crates", [])
            if isinstance(entry, dict)
        }
        expected = {c.get("dir") for c in root_spec.get("crates", [])}
        result.add(
            "descriptor declares every independent Cargo root",
            expected.issubset(declared),
            f"declared={sorted(declared)} expected={sorted(expected)}",
        )
        write_set = descriptor.get("write_set", {})
        result.add(
            "descriptor has allowed and protected roots",
            bool(write_set.get("allowed_roots")) and bool(write_set.get("protected_roots")),
            f"allowed={len(write_set.get('allowed_roots', []))} protected={len(write_set.get('protected_roots', []))}",
        )
        default = descriptor.get("verifier_policy", {}).get("default")
        result.add(
            "declared default verifier is assigned",
            default in root_spec.get("verifiers", []),
            str(default),
        )

    # Ligature bundle.
    bundle_dir = root / "tools" / "ligature"
    sums = bundle_dir / "SHA256SUMS"
    pyz = bundle_dir / "ligature.pyz"
    result.add("root-local Ligature bundle exists", pyz.is_file() and sums.is_file(), str(bundle_dir))
    if pyz.is_file() and sums.is_file():
        code, out = run(["sha256sum", "-c", "SHA256SUMS"], cwd=bundle_dir)
        result.add("Ligature bundle checksum verifies", code == 0, out)
        code, out = run([str(pyz), "version"], cwd=root)
        result.add("Ligature version runs", code == 0, out.splitlines()[0] if out else "")

    # Upstream pin.
    pin_path = root / "upstream" / "upstream-pin.json"
    expected_upstream = root_spec.get("upstream", {})
    if pin_path.is_file():
        try:
            pin = json.loads(pin_path.read_text(encoding="utf-8"))
            result.add("upstream pin parses", True, str(pin_path))
            result.add(
                "upstream pin commit matches manifest",
                str(pin.get("commit", "")) == str(expected_upstream.get("commit", "")),
                f"{pin.get('commit')} vs {expected_upstream.get('commit')}",
            )
            result.add(
                "upstream pin tag matches manifest",
                str(pin.get("tag", "")) == str(expected_upstream.get("tag", "")),
                f"{pin.get('tag')} vs {expected_upstream.get('tag')}",
            )
        except (OSError, json.JSONDecodeError) as exc:
            result.add("upstream pin parses", False, str(exc))
    else:
        result.add("upstream pin exists", False, str(pin_path))

    # Per-crate independent roots.
    expected_channels = {
        c.get("verifier"): c.get("toolchain", {}).get("rust_channel")
        for c in root_spec.get("crates", [])
    }
    for crate in root_spec.get("crates", []):
        cdir = root / crate.get("dir", "")
        cname = crate.get("crate", cdir.name)
        result.add(f"{cname}: crate directory exists", cdir.is_dir(), str(cdir))
        manifest = cdir / "Cargo.toml"
        lock = cdir / "Cargo.lock"
        toolchain = cdir / "rust-toolchain.toml"
        cargo_config = cdir / ".cargo" / "config.toml"
        for label, path in (
            ("Cargo.toml", manifest),
            ("Cargo.lock", lock),
            ("rust-toolchain.toml", toolchain),
            (".cargo/config.toml", cargo_config),
        ):
            result.add(f"{cname}: {label} exists", path.is_file(), str(path))
        if manifest.is_file():
            result.add(
                f"{cname}: Cargo package name matches crate",
                read_cargo_package_name(manifest) == cname,
                f"{read_cargo_package_name(manifest)} vs {cname}",
            )
        if toolchain.is_file():
            channel = read_toolchain_channel(toolchain)
            result.add(
                f"{cname}: toolchain channel matches verifier pin",
                channel == expected_channels.get(crate.get("verifier")),
                f"{channel} vs {expected_channels.get(crate.get('verifier'))}",
            )
        if cargo_config.is_file():
            text = cargo_config.read_text(encoding="utf-8", errors="replace")
            result.add(
                f"{cname}: .cargo/config.toml has no repository-local target dir",
                "target-dir" not in text,
                "shared target-directory override found" if "target-dir" in text else "no target-dir override",
            )
        result.add(
            f"{cname}: no repository-local target/ tree",
            not (cdir / "target").exists(),
            str(cdir / "target"),
        )
        if crate.get("verifier") == "creusot":
            verif = cdir / "verif"
            result.add(
                f"{cname}: verif/ is absent before the first proof",
                not verif.exists(),
                "created by the first Creusot run" if not verif.exists() else str(verif),
                warning=True,
            )

    result.add(
        "no root-level Cargo.toml workspace",
        not (root / "Cargo.toml").exists(),
        str(root / "Cargo.toml"),
    )

    # Worker-authorable support dirs.
    result.add("oracle/ exists", (root / "oracle").is_dir(), str(root / "oracle"))
    result.add(
        "findings/limitations.jsonl exists",
        (root / "findings" / "limitations.jsonl").is_file(),
        str(root / "findings" / "limitations.jsonl"),
    )
    result.add("PORT-GAPS.md exists", (root / "PORT-GAPS.md").is_file(), str(root / "PORT-GAPS.md"))

    analysis = root / "analysis"
    for verifier in root_spec.get("verifiers", []):
        found = sorted(analysis.glob(f"*/results-{verifier}")) if analysis.is_dir() else []
        result.add(
            f"{verifier}: durable per-tool evidence root exists",
            bool(found),
            ", ".join(str(p.relative_to(root)) for p in found) or f"missing analysis/*/results-{verifier}/",
        )

    # Forbidden shared state.
    shared_markers = [root / "ci" / "ledger", root / "specs" / "_closure" / "shared"]
    result.add(
        "no shared mutable ledger/closure marker",
        not any(p.exists() for p in shared_markers),
        str(shared_markers),
    )

    if hash_protected:
        hashes = {}
        candidates = [
            "project-descriptor.json",
            "rust-toolchain.toml",
            ".gitignore",
            ".envrc",
            ".mcp.json",
            "README.md",
        ]
        for crate in root_spec.get("crates", []):
            cdir = crate.get("dir", "")
            candidates.extend(
                [
                    f"{cdir}/Cargo.toml",
                    f"{cdir}/Cargo.lock",
                    f"{cdir}/rust-toolchain.toml",
                    f"{cdir}/.cargo/config.toml",
                ]
            )
        for rel in candidates:
            path = root / rel
            if path.is_file():
                hashes[rel] = sha256(path)
        result.add(
            "protected-file hashes captured",
            bool(hashes),
            json.dumps(hashes, sort_keys=True),
        )

    return result


def emit(result: Result, as_json: bool, context: dict) -> int:
    payload = {
        "context": context,
        "summary": {
            "pass": sum(1 for c in result.checks if c["status"] == "pass"),
            "warn": len(result.warnings),
            "fail": len(result.failed),
        },
        "checks": result.checks,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"# {context.get('mode')}: {context.get('root', context.get('manifest'))}")
        for check in result.checks:
            mark = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check["status"]]
            print(f"[{mark}] {check['check']}: {check['detail']}")
        print(
            f"\n{payload['summary']['pass']} passed, "
            f"{payload['summary']['warn']} warnings, {payload['summary']['fail']} failed"
        )
    return 0 if not result.failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--plan", action="store_true", help="validate the setup manifest only")
    parser.add_argument("--root", type=Path, help="validate one created project root")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--hash-protected", action="store_true", help="hash protected files")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if args.plan:
        return emit(
            check_plan(manifest),
            args.json,
            {"mode": "plan", "manifest": str(args.manifest.resolve())},
        )
    if not args.root:
        parser.error("pass --plan or --root PATH")
    specs = {r.get("root"): r for r in manifest.get("roots", [])}
    spec = specs.get(args.root.resolve().name)
    if not spec:
        print(f"root {args.root} is not one of the four planned P4 roots", file=sys.stderr)
        return 2
    return emit(
        check_root(args.root, spec, args.hash_protected),
        args.json,
        {"mode": "root", "root": str(args.root.resolve()), "issue": manifest.get("issue")},
    )


if __name__ == "__main__":
    raise SystemExit(main())
