#!/usr/bin/env python3
"""Summarise a Verus transcript: results line, and primary error locations by file.

A Verus diagnostic prints several `-->` lines -- the failing span, then a note or a
recommendation that points at the callee which rejected the call.  Only the
*first* `-->` of each `error:` block is a location in this crate's own code, and
that is what this counts.  A `-->` that appears with no `error:` above it belongs
to a note attached to the previous block, so it is skipped.

    python3 analysis/verus/err-summary.py [transcript]
"""
import collections
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "verus-transcript.txt"
CRATE = "rust/swisstable-verus-core/"
RESULTS = re.compile(r"verification results::\s*\d+ verified,\s*\d+ errors")
ANY_LOC = re.compile(r"-->\s+(\S+\.rs):(\d+):(\d+)")


def parse(text):
    """-> (results_line, [(kind, file, line)], per-file counts, per-kind counts)"""
    lines = text.splitlines()
    results = None
    errs = []
    kinds = collections.Counter()
    files = collections.Counter()
    for i, line in enumerate(lines):
        m = RESULTS.search(line)
        if m:
            results = line.strip()
        if not line.startswith("error: "):
            continue
        kind = line[len("error: "):].strip()
        kinds[kind] += 1
        loc = None
        for j in range(i + 1, min(i + 4, len(lines))):
            m = ANY_LOC.search(lines[j])
            if m:
                loc = (m.group(1), int(m.group(2)))
                break
        if loc is None:
            continue
        files[loc[0].replace(CRATE, "")] += 1
        errs.append((kind, loc[0].replace(CRATE, ""), loc[1]))
    return results, errs, files, kinds


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    results, errs, files, kinds = parse(path.read_text())
    print(f"transcript: {path}")
    print(f"  {results}")
    print(f"  primary error locations: {len(errs)}")
    # A path that still begins with `rust/` after the crate prefix was stripped was
    # a nested path inside the crate; anything else resolved in vstd.
    ours = {f: n for f, n in files.items() if not f.startswith("rust/")}
    print("  by file (this crate's code):")
    for f, n in sorted(ours.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"    {n:>4}  {f}")
    outside = sum(n for f, n in files.items() if f.startswith("rust/"))
    if outside:
        print(f"    ({outside} more resolve inside vstd, i.e. a callee rejecting a call)")
    print("  by kind:")
    for k, n in kinds.most_common():
        print(f"    {n:>4}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())