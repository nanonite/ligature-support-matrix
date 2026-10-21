#!/usr/bin/env python3
"""Read every recorded codesight-mcp caller/callee artefact back and print the
edges it returned, normalised.

Handles the two shapes #26 recorded:
  * the tool's `[codesight] <op>` header line, which is line 1 of every file,
  * the `<<<UNTRUSTED_CODE_*>>>` wrapper around every id/name/file string.

The `symbol_id` the tool answers with is `<repo>/<file>::<name>#<kind>`, which
is the only place the *subject's* file is recorded for get-callers /
get-callees, so it is parsed for both endpoints.

Usage:
    ./codesight-edges.py [area ...]      # areas: open-addressing group-probing
                                         # tombstones erase rehash iteration
    ./codesight-edges.py --json
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
CODESIGHT = HERE.parent / "codesight"
WRAP = re.compile(r"^<<<UNTRUSTED_CODE_[0-9a-f]+>>>\n(.*)\n<<<END_UNTRUSTED_CODE", re.S)

AREAS = ("open-addressing", "group-probing", "tombstones", "erase",
         "rehash", "iteration")


def body(path):
    """Line 1 is the tool's own `[codesight] <op>` header; the JSON starts at 2."""
    return json.loads(path.read_text().split("\n", 1)[1])


def unwrap(value):
    match = WRAP.match(value) if isinstance(value, str) else None
    return match.group(1) if match else value


def endpoint(symbol_id):
    """`<repo>/<file>::<name>#<kind>` -> (short file, name)."""
    raw = unwrap(symbol_id) or ""
    tail = raw.split("/", 1)[-1]           # drop the repo prefix
    file_part, _, name_part = tail.partition("::")
    name = name_part.split("#", 1)[0]
    return file_part.rsplit("/", 1)[-1] or "?", name or "?"


def area_of(stem):
    for area in AREAS:
        if f"-{area}-" in stem or stem.endswith(f"-{area}"):
            return area
    return "?"


def collect(area_filter):
    rows = []
    for path in sorted(CODESIGHT.glob("get-call*.json")):
        if path.name.endswith(".exit"):
            continue
        stem = path.stem
        if stem.startswith("get-call-chain"):
            # handled separately below; it is a path query, not an edge query
            continue
        op = "callers" if stem.startswith("get-callers") else "callees"
        area = area_of(stem)
        if area_filter and area not in area_filter:
            continue
        exit_file = path.with_suffix(path.suffix + ".exit")
        code = exit_file.read_text().strip() if exit_file.exists() else "?"
        row = {"area": area, "artefact": path.name, "op": op, "exit": code}
        try:
            data = body(path)
        except Exception as exc:  # noqa: BLE001
            rows.append({**row, "status": f"UNPARSEABLE {exc}"})
            continue
        subject_file, subject = endpoint(data.get("symbol_id"))
        requested = stem[len(op) + len("get-") + 1:].rsplit("-", 0)  # noqa: F841
        row.update({"status": "ok", "subject": subject,
                    "subject_file": subject_file})
        if "error" in data:
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else err
            # the requested target is the artefact name, the tool echoes none
            row.update({"status": "not-found", "detail": msg,
                        "requested": path.stem.split("-", 2)[-1].replace("-", "::", 1)})
            rows.append(row)
            continue
        key = "callers" if op == "callers" else "callees"
        peers = data.get(key, [])
        if not peers:
            # a zero-count answer is a real answer (a leaf has no callees) and
            # must stay distinguishable from `Symbol not found`, which is
            # absence.  Record it as an explicit empty result.
            rows.append({**row, "status": "empty",
                         "count": data.get(f"{op[:-1]}_count",
                                           data.get("result_count"))})
            continue
        for item in peers:
            peer_file, peer = endpoint(item.get("id"))
            # normalise every row to (caller, callee): a get-callers artefact
            # asks about the callee and lists the callers, so its direction is
            # the reverse of the truth table's.
            caller, callee = (peer, subject) if op == "callers" else (subject, peer)
            rows.append({**row, "caller": caller, "callee": callee,
                         "peer": peer, "peer_file": peer_file,
                         "peer_line": item.get("line"),
                         "depth": item.get("depth")})
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--json" in sys.argv:
        json.dump(collect(args), sys.stdout, indent=1)
        print()
        return

    rows = collect(args)
    resolved = [r for r in rows if r["status"] == "ok"]
    empty = [r for r in rows if r["status"] == "empty"]
    missing = [r for r in rows if r["status"] == "not-found"]
    print(f"artefacts: {len({r['artefact'] for r in rows})}  "
          f"resolved edges: {len(resolved)}  zero-count answers: {len(empty)}  "
          f"Symbol-not-found probes: {len(missing)}")
    print()
    for area in AREAS:
        if area not in args and args:
            continue
        print(f"--- {area}")
        for row in sorted((r for r in rows if r["area"] == area),
                          key=lambda r: (r["op"], r["artefact"])):
            if row["status"] == "not-found":
                print(f"  [exit {row['exit']}] Symbol not found: "
                      f"{row['requested']}")
            elif row["status"] == "empty":
                print(f"  {row['subject_file']}::{row['subject']:<34} "
                      f"{row['op']}: 0 (zero-count answer, exit {row['exit']})")
            else:
                arrow = "->" if row["op"] == "callees" else "<-"
                print(f"  {row['subject_file']}::{row['subject']:<34} {arrow} "
                      f"{row['peer_file']}::{row['peer']}"
                      f"(L{row['peer_line']}) depth={row['depth']}"
                      f"   [normalised: {row['caller']} -> {row['callee']}]")
        print()


if __name__ == "__main__":
    main()
