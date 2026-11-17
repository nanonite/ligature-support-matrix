#!/usr/bin/env python3
"""Compare two protected-hashes.py snapshots.

Usage: protected-hashes-compare.py before.json after.json

Exit 0 when every pre-existing protected file is unchanged and no new-root
protected target was created. Exit 1 otherwise.
"""
import json
import sys


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    before = load(sys.argv[1])
    after = load(sys.argv[2])

    b = {e["path"]: e for e in before["entries"]}
    a = {e["path"]: e for e in after["entries"]}

    removed = sorted(set(b) - set(a))
    added = sorted(set(a) - set(b))
    changed = sorted(
        p for p in set(a) & set(b) if a[p]["sha256"] != b[p]["sha256"]
    )
    created_protected = [
        t for t in after["new_root_protected_targets"] if t["exists"]
    ]

    result = {
        "before_label": before["label"],
        "after_label": after["label"],
        "before_entry_count": before["entry_count"],
        "after_entry_count": after["entry_count"],
        "removed": removed,
        "added": added,
        "changed": changed,
        "created_new_root_protected_targets": created_protected,
        "ok": not (removed or added or changed or created_protected),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
