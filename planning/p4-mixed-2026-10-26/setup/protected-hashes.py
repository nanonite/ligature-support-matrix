#!/usr/bin/env python3
"""Snapshot hashes of operator/protected paths for P4 setup issue #177.

Usage: protected-hashes.py <workspace-root> <label>

Only reads files. Never writes inside the workspace; the caller redirects
stdout to a file under planning/p4-mixed-2026-10-26/setup/.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_FILES = ["flake.nix", "flake.lock", ".gitmodules"]
PILOTS = ["date-creusot", "swisstable-verus", "crypto-mixed"]
PILOT_GLOBS = [
    "project-descriptor.json",
    ".envrc",
    ".mcp.json",
    ".gitignore",
    ".ligature/**/*",
    "ci/**/*",
    "scripts/**/*",
    "docs/*-schema.json",
    "docs/reliance-policy.md",
    ".codex/skills/ligature/SKILL.md",
    "rust/*/Cargo.toml",
    "rust/*/Cargo.lock",
    "rust/*/rust-toolchain.toml",
    "rust/*/build.rs",
    "rust/*/.cargo/config.toml",
    "rust/*/specs/**/*",
    "crates/*/Cargo.toml",
    "crates/*/Cargo.lock",
    "crates/*/rust-toolchain.toml",
    "crates/*/build.rs",
    "crates/*/.cargo/config.toml",
]

NEW_ROOTS = {
    "icl-creusot-verus": {
        "crates": ["rust/icl-creusot", "rust/icl-verus"],
    },
    "tinyxml2-creusot-kani": {
        "crates": ["rust/tinyxml2-creusot", "rust/tinyxml2-kani"],
    },
    "snappy-verus-kani": {
        "crates": ["rust/snappy-verus", "rust/snappy-kani"],
    },
    "leveldb-three-verifiers": {
        "crates": [
            "rust/leveldb-creusot",
            "rust/leveldb-verus",
            "rust/leveldb-kani",
        ],
    },
}

NEW_ROOT_PROTECTED = [
    "project-descriptor.json",
    ".ligature",
    ".envrc",
    ".mcp.json",
    "schemas",
    "ci",
    "scripts",
    "docs/reliance-policy.md",
    "docs/project-descriptor.schema.json",
    ".codex/skills/ligature/SKILL.md",
    "tools/ligature/ligature.pyz",
    "tools/ligature/SHA256SUMS",
    "tools/ligature/PROVENANCE.json",
    "tools/ligature/NOTICE",
    "tools/ligature/THIRD_PARTY_NOTICES.txt",
    "ci/manifest",
    "tests/harnesses",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    label = sys.argv[2]

    paths = []
    for rel in ROOT_FILES:
        p = root / rel
        if p.is_file():
            paths.append(p)
    for pilot in PILOTS:
        base = root / pilot
        for pattern in PILOT_GLOBS:
            for p in sorted(base.glob(pattern)):
                if p.is_file() and ".git" not in p.parts and "upstream" not in p.parts:
                    paths.append(p)

    seen = set()
    entries = []
    for p in sorted(set(paths)):
        rel = p.relative_to(root).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        entries.append(
            {
                "path": rel,
                "sha256": sha256(p),
                "bytes": p.stat().st_size,
            }
        )

    absent = []
    for new_root, meta in NEW_ROOTS.items():
        for rel in NEW_ROOT_PROTECTED:
            absent.append(f"{new_root}/{rel}")
        for crate in meta["crates"]:
            absent.extend(
                [
                    f"{new_root}/{crate}/Cargo.toml",
                    f"{new_root}/{crate}/Cargo.lock",
                    f"{new_root}/{crate}/rust-toolchain.toml",
                    f"{new_root}/{crate}/.cargo/config.toml",
                    f"{new_root}/{crate}/build.rs",
                ]
            )

    payload = {
        "label": label,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace_root": str(root),
        "workspace_head": subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "entry_count": len(entries),
        "entries": entries,
        "new_root_protected_targets": [
            {"path": rel, "exists": (root / rel).exists()} for rel in absent
        ],
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
