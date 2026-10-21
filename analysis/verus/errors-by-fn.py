#!/usr/bin/env python3
"""Group a Verus transcript's errors by the function they occur in.

    python3 analysis/verus/errors-by-fn.py [transcript]

Verus's diagnostic blocks do not name the enclosing function, so this maps each
`file:line` back to the nearest preceding `fn` declaration in that source file.
"""
import collections
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent.parent
CRATE = PILOT / "rust" / "swisstable-verus-core"

spec = importlib.util.spec_from_file_location("err_summary", HERE / "err-summary.py")
err_summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(err_summary)

FNS = re.compile(r"\b(?:pub(?:\([a-z]+\))?\s+)?(?:open |closed |exec |proof )*fn\s+(\w+)")


def function_index() -> dict:
    """-> {(relative path, line): (fn name, start line)}"""
    index = {}
    for src in sorted(CRATE.rglob("*.rs")):
        rel = str(src.relative_to(CRATE))
        lines = src.read_text().splitlines()
        starts = []
        for i, line in enumerate(lines, start=1):
            m = FNS.search(line)
            if m and not line.strip().startswith("//"):
                starts.append((i, m.group(1)))
        for i, line in enumerate(lines, start=1):
            owner = None
            for start, name in starts:
                if start > i:
                    break
                owner = (name, start)
            if owner:
                index[(rel, i)] = owner
    return index


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "verus-transcript.txt"
    _results, errs, _files, _kinds = err_summary.parse(path.read_text())
    index = function_index()
    grouped = collections.defaultdict(list)
    for kind, file, line in errs:
        name = index.get((file, line), ("<unknown>", 0))[0]
        grouped[name].append((file, line, kind))
    total = sum(len(v) for v in grouped.values())
    print(f"{total} error locations in {len(grouped)} functions "
          f"(ordered by count; file:line shown for each)")
    for name, v in sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"{len(v):>3}  {name}")
        for f, l, k in v:
            print(f"       {f}:{l}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())