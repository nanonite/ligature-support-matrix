#!/usr/bin/env python3
"""Hash the workspace protected surface before/after a P4 setup attempt.

Chainlink #177. Read-only. Covers the root flake inputs and the descriptor /
manifest / lock / toolchain surface of the three preserved baseline pilots.
The four planned mixed roots are not created, so they are listed as absent by
design rather than silently omitted.

Usage:
  hash_protected.py [--root PATH] [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PROTECTED = [
    "flake.nix",
    "flake.lock",
    ".gitmodules",
    "crypto-mixed/project-descriptor.json",
    "crypto-mixed/.envrc",
    "crypto-mixed/crates/crypto-mixed-core/Cargo.toml",
    "crypto-mixed/crates/crypto-mixed-core/Cargo.lock",
    "crypto-mixed/oracle/rust-check/Cargo.toml",
    "crypto-mixed/oracle/rust-check/Cargo.lock",
    "date-creusot/project-descriptor.json",
    "date-creusot/.envrc",
    "date-creusot/rust/date-creusot-core/Cargo.toml",
    "date-creusot/rust/date-creusot-core/Cargo.lock",
    "date-creusot/oracle/rust-check/Cargo.toml",
    "date-creusot/oracle/rust-check/Cargo.lock",
    "swisstable-verus/project-descriptor.json",
    "swisstable-verus/.envrc",
    "swisstable-verus/rust/swisstable-verus-core/Cargo.toml",
    "swisstable-verus/rust/swisstable-verus-core/Cargo.lock",
]

PLANNED = [
    "icl-creusot-verus/project-descriptor.json",
    "tinyxml2-creusot-kani/project-descriptor.json",
    "snappy-verus-kani/project-descriptor.json",
    "leveldb-three-verifiers/project-descriptor.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    files = {}
    for rel in PROTECTED:
        path = root / rel
        files[rel] = {"exists": path.is_file(), "sha256": sha256(path) if path.is_file() else None}

    planned = {rel: (root / rel).is_file() for rel in PLANNED}

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()

    payload = {
        "root": str(root),
        "files": files,
        "planned_roots_present": planned,
        "git_status_short": status,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
