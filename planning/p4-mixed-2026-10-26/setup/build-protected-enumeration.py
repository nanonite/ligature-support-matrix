#!/usr/bin/env python3
"""Build the exact per-root protected-path enumeration for Chainlink #177.

Reads each root's analysis/setup/root-setup.json and expands the proposed
protected patterns against that root's actual crate directories. Writes JSON
to stdout; never writes inside the roots.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WS = Path(__file__).resolve().parents[3]
SETUP = WS / "planning" / "p4-mixed-2026-10-26" / "setup"
ROOTS = [
    "icl-creusot-verus",
    "tinyxml2-creusot-kani",
    "snappy-verus-kani",
    "leveldb-three-verifiers",
]

ROUTES = {
    "project-descriptor.json": (
        "Operator runs the approved `ligature.pyz init` in this root (T2/operator "
        "action); no path-specific grant exists in #177."
    ),
    ".ligature/**": "Created by the approved `ligature.pyz init`; operator-managed.",
    "schemas/**": "Supplied by the approved Ligature install/init; operator-managed.",
    "tools/ligature/**": (
        "Operator installs the approved bundle (1.4.3, SHA-256 "
        "1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1) with "
        "SHA256SUMS/PROVENANCE; no copy performed by #177."
    ),
    "rust/*/Cargo.toml": (
        "`ligature.pyz scaffold-crate --issue <N> --crate <name> --grant-id <id> "
        "--json` under an exact active manifest grant, or operator exact-path write."
    ),
    "rust/*/Cargo.lock": (
        "No sanctioned general lock writer in Ligature 1.4.3; operator exact-path "
        "action under an exact issue/path grant."
    ),
    "rust/*/rust-toolchain.toml": (
        "No sanctioned nested-toolchain writer; operator exact-path action under an "
        "exact issue/path grant."
    ),
    "rust/*/.cargo/config.toml": (
        "Operator exact-path action; carries verifier-specific config/patch."
    ),
    "rust/*/build.rs": "Operator exact-path action; protected by policy proposal.",
    "rust/*/specs/**": (
        "Ligature `draft`/promotion workflow under issue-specific grants; never "
        "hand-written."
    ),
    "ci/**": "Operator/sanctioned exact-path action; no grant in #177.",
    "scripts/**": "Operator/sanctioned exact-path action; no grant in #177.",
    "tests/harnesses/**": "Operator/sanctioned exact-path action; no grant in #177.",
    ".envrc": "Operator-managed local environment file.",
    ".mcp.json": "Operator-managed local MCP configuration.",
    ".github/**": "Operator-managed CI configuration.",
    ".codex/skills/ligature/**": "Managed with the approved Ligature install.",
    "outer-repository submodule registration": (
        "Operator action in the outer repository: `git submodule add` + pin. Not "
        "performed by #177."
    ),
}


def expand(entry: str, crates: list[str]) -> list[str]:
    if entry == "rust/*/Cargo.toml":
        return [f"{c}/Cargo.toml" for c in crates]
    if entry == "rust/*/Cargo.lock":
        return [f"{c}/Cargo.lock" for c in crates]
    if entry == "rust/*/rust-toolchain.toml":
        return [f"{c}/rust-toolchain.toml" for c in crates]
    if entry == "rust/*/.cargo/config.toml":
        return [f"{c}/.cargo/config.toml" for c in crates]
    if entry == "rust/*/build.rs":
        return [f"{c}/build.rs" for c in crates]
    if entry == "rust/*/specs/**":
        return [f"{c}/specs/**" for c in crates]
    return [entry]


def matches(root: Path, rel: str) -> bool:
    if rel.endswith("/**"):
        return (root / rel[:-3]).is_dir() and any((root / rel[:-3]).iterdir())
    return (root / rel).exists()


def main() -> int:
    roots = {}
    total = 0
    present = []
    for name in ROOTS:
        base = WS / name
        setup = json.loads((base / "analysis/setup/root-setup.json").read_text())
        crates = [c["path"] for c in setup["crates"]]
        entries = []
        for item in setup["protected_paths"]:
            pattern = item["path"]
            for rel in expand(pattern, crates):
                total += 1
                exists = matches(base, rel)
                if exists:
                    present.append(f"{name}/{rel}")
                entries.append(
                    {
                        "path": rel,
                        "status": "present" if exists else "absent",
                        "creation_route": ROUTES[pattern],
                        "grant_required": True,
                        "grant_issued_in_177": False,
                    }
                )
        roots[name] = {
            "project": setup["project"],
            "verifiers": setup["verifiers"],
            "paths": entries,
        }

    payload = {
        "schema": "p4-protected-write-enumeration/1",
        "issue": 177,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": (
            "Enumeration only. #177 issues no grant and performs no protected "
            "write. Each entry needs an exact operator action or sanctioned "
            "command with an issue/path grant before creation."
        ),
        "total_entries": total,
        "present_entries": present,
        "all_absent": not present,
        "roots": roots,
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
