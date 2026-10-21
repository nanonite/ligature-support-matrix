#!/usr/bin/env python3
"""Classify every codesight-mcp `Symbol not found` probe against the pinned
upstream source (chainlink #108).  All tables this writes are derived; none is
hand-edited.

#26 read every `Symbol not found` at exit 1 as evidence that tree-sitter dropped
the symbol.  That only holds if the symbol exists in the source at all.  This
script derives the split, because at the pinned 2026 LTS commit several of the
probed names are gone.

Scope matters, and is the whole point.  Bare `grep -F` over `absl/` calls a
symbol "present" on a comment, on a longer identifier, or on an unrelated test
file -- e.g. `IsEmpty` matches `btree_test.cc:64 using ::testing::IsEmpty` and
`Resize` matches `chunked_queue.h:317 'Resizes the container'`.  So each
requested symbol is grepped three ways and bucketed:

  absent        zero substring hits anywhere under absl/
  present-weak  hits somewhere, but NO whole-word hit in the subset files
  present       at least one whole-word hit in a subset file
  out-of-subset a whole-word hit elsewhere under absl/ but none in a subset file

SUBSET_FILES is the five files the P2 subset is made of; a symbol that only
turns up in a test or in absl/strings is not evidence about the subset.

The `hit_kind` column is a stated heuristic (definition / call / mention), not a
parse: a whole-word occurrence is `definition` if the line, with comments
stripped, has the name followed by `(` and not preceded by `.` or `->`.

Usage:  ./classify-not-found.py
Writes: not-found-absent.tsv, not-found-present-weak.tsv,
        not-found-present.tsv, not-found-out-of-subset.tsv,
        not-found-classify.txt
"""
import importlib.util
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent.parent
UPSTREAM = PILOT / "upstream" / "abseil-cpp"

SUBSET_FILES = (
    "absl/container/internal/raw_hash_set.h",
    "absl/container/internal/raw_hash_set.cc",
    "absl/container/internal/hashtable_control_bytes.h",
    "absl/container/internal/raw_hash_set_resize_impl.h",
    "absl/container/internal/node_slot_policy.h",
)

_spec = importlib.util.spec_from_file_location("codesight_edges",
                                               HERE / "codesight-edges.py")
codesight_edges = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codesight_edges)


def git(*args):
    return subprocess.run(["git", *args], cwd=UPSTREAM,
                          capture_output=True, text=True)


def grep(symbol, paths, whole_word):
    cmd = ["grep", "-n", "-F"]
    if whole_word:
        cmd.append("-w")
    proc = git(*cmd, "--", symbol, *paths)
    return proc.returncode, [ln for ln in proc.stdout.splitlines() if ln.strip()]


def strip_comments(code):
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    return re.sub(r"//.*$", "", code)


def hit_kind(line, symbol):
    """Stated heuristic -- see the module docstring.

    Comments are stripped first, then each occurrence is classified by its
    syntactic position: an occurrence nested inside parentheses or brackets is
    an argument, not a declaration, so `find_first_non_full_from_h1(c, H1(hash))`
    reads `H1` as a call.  Only a top-level occurrence followed by `(` is
    reported as `definition`.
    """
    code = strip_comments(line.split(":", 2)[-1])
    depth = 0
    for index, char in enumerate(code):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        if not code.startswith(symbol, index):
            continue
        before = code[max(0, index - 2):index]
        after = code[index + len(symbol):index + len(symbol) + 1]
        if before.endswith((".", "->")):
            return "call"
        if depth > 0:
            return "call"
        if after == "(":
            return "definition"
    return "mention"


def best_evidence(lines, symbol):
    """Prefer a definition site; fall back to the first whole-word hit."""
    for line in lines:
        if hit_kind(line, symbol) == "definition":
            return line
    return lines[0]


# #26 named its artefacts `<get-callers|get-callees>-<area>-<qual>-<symbol>`.
# <qual> is the file the symbol lives in, not part of the name asked for.
FILE_QUALIFIERS = ("resize-impl", "ctrl", "cc", "h", "internal",
                   "container-internal")


def strip_qualifier(symbol):
    changed = True
    while changed:
        changed = False
        for qual in FILE_QUALIFIERS:
            if symbol.startswith(qual + "-"):
                symbol = symbol[len(qual) + 1:]
                changed = True
    return symbol


def requested_symbols():
    """The distinct symbol each `Symbol not found` artefact asked for."""
    found = {}
    for row in codesight_edges.collect([]):
        if row["status"] != "not-found":
            continue
        stem = row["artefact"][:-len(".json")]
        area = codesight_edges.area_of(stem)
        assert area != "?", stem
        symbol = strip_qualifier(
            stem[stem.index(area) + len(area):].lstrip("-"))
        assert symbol, stem
        found.setdefault(symbol, []).append(row["artefact"])
    return found


def main():
    symbols = requested_symbols()
    buckets = {"absent": [], "present": [], "present-weak": [],
               "out-of-subset": []}
    transcript = [f"# upstream/abseil-cpp HEAD {git('rev-parse', 'HEAD').stdout.strip()}",
                  f"# subset files: {', '.join(SUBSET_FILES)}",
                  f"# {len(symbols)} distinct symbols across "
                  f"{sum(len(v) for v in symbols.values())} `Symbol not found` "
                  f"artefacts", ""]

    for symbol in sorted(symbols):
        n_artefacts = len(symbols[symbol])
        _, anywhere = grep(symbol, ["absl"], whole_word=False)
        _, subset_word = grep(symbol, SUBSET_FILES, whole_word=True)
        _, absl_word = grep(symbol, ["absl"], whole_word=True)

        transcript.append(f"$ git grep -n -w -F -- {symbol!r} "
                          f"{' '.join(SUBSET_FILES)}")
        transcript.extend(subset_word) if subset_word else transcript.append(
            "(no whole-word hit in the subset files)")
        transcript.append("")

        if not anywhere:
            bucket, note = "absent", "zero hits anywhere under absl/"
        elif subset_word:
            first = best_evidence(subset_word, symbol)
            kinds = {hit_kind(line, symbol) for line in subset_word}
            bucket = "present"
            note = (f"{first} [{hit_kind(first, symbol)}]"
                    + ("" if kinds == {"definition"}
                       else f"; {len(subset_word)} whole-word hit(s), kinds="
                            f"{sorted(kinds)}"))
        elif absl_word:
            first = absl_word[0]
            bucket = "out-of-subset"
            note = f"{first} [{hit_kind(first, symbol)}] (not a subset file)"
        else:
            bucket = "present-weak"
            note = (f"{anywhere[0]} -- substring only, no whole-word hit; "
                    f"the symbol does not exist under this name")
        buckets[bucket].append((symbol, n_artefacts, note))

    header = ("# DERIVED by classify-not-found.py -- do not hand-edit.\n"
              "# `git grep -w -F` over the five P2 subset files.\n"
              "# hit_kind is a stated heuristic, NOT a parse: it reports\n"
              "# `definition` for any top-level occurrence followed by `(`, so a\n"
              "# constructor call (`Group(ctrl).MaskEmpty()`) or an argument\n"
              "# (`= Group(...)`) can read as `definition`.  Every row therefore\n"
              "# also lists every kind found and how many whole-word hits there\n"
              "# were, so the evidence line can be checked, not trusted.\n"
              "# columns: requested symbol | artefacts that asked | evidence\n")
    for name, rows in (("absent", buckets["absent"]),
                       ("present-weak", buckets["present-weak"]),
                       ("out-of-subset", buckets["out-of-subset"]),
                       ("present", buckets["present"])):
        (HERE / f"not-found-{name}.tsv").write_text(
            header + "".join(f"{s}\t{n}\t{note}\n" for s, n, note in rows))
    (HERE / "not-found-classify.txt").write_text("\n".join(transcript) + "\n")

    total = sum(len(v) for v in symbols.values())
    print(f"{total} `Symbol not found` artefacts, {len(symbols)} distinct "
          f"symbols")
    for name in ("absent", "out-of-subset", "present-weak", "present"):
        rows = buckets[name]
        print(f"  {name:<14} {len(rows):>2} symbols "
              f"({sum(n for _, n, _ in rows):>2} artefacts)")
    print()
    for name in ("absent", "out-of-subset", "present-weak"):
        print(f"{name}:")
        for s, n, note in buckets[name]:
            print(f"  {s}  ({n} artefact(s))  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
