#!/usr/bin/env python3
"""Three-way comparison for chainlink #108: C++ ground truth vs codesight-mcp
vs ligature extract-c-static.

WHAT IS AND IS NOT BEING COMPARED -- read this before quoting any number
-------------------------------------------------------------------------
`ligature extract-c-static` scans **Rust only**.  It is the C_static arm of
the pipeline: it records which Rust call sites belong to which local concept.
It never opens the pinned C++ under upstream/abseil-cpp.  codesight-mcp, by
contrast, indexes the C++ tree and never sees Rust.  So there is no input on
which both tools are answering the same question.

This script therefore does NOT claim agreement about the C++ call sites.  It
answers two narrower, measurable questions:

  Q1 (codesight): of the true C++ edges in edge-truth.tsv, how many does
      codesight-mcp's recorded answers recover, and how many recorded edges of
      its own are not in the truth table?  This is a real measurement: the
      ground truth is the cited C++ source and the recorded artefacts are the
      tool's own output.

  Q2 (ligature): given the hand-written Rust transcription in subset-port/,
      which of the transcriptions' edges does extract-c-static recover as a
      resolved call site, which does it record as unresolved, and which does
      it not record at all?  This measures the extractor's coverage, not the
      C++ graph.

`scope-cut` is reported for any row whose C++ edge codesight never resolved,
and the disagreement rows are the ones that go into findings/limitations.jsonl.

Usage:
    ./compare.py            # the human table
    ./compare.py --json     # machine-readable
"""
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
# codesight-edges.py has a hyphen in its name, so load it by path
_spec = importlib.util.spec_from_file_location("codesight_edges",
                                              HERE / "codesight-edges.py")
codesight_edges = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codesight_edges)

TRUTH = HERE / "edge-truth.tsv"
LIGATURE = HERE / "subset-port-result.json"
NA = "-"

# Recorded codesight-mcp edges that are hand-verified FALSE against the pinned
# C++.  They cannot be derived mechanically -- each was read in the source --
# so they are carried here with the citation that refutes them.
#   (caller, callee) -> (callee site, why it is wrong, artefact)
VERIFIED_FALSE = {
    ("assert_is_full", "generation"): (
        "btree.h:1094",
        "raw_hash_set.h:2445 calls AssertIsFull (h:1586); generation() is an "
        "argument evaluated at the call site, and btree_iterator_generation_"
        "info_disabled::generation is a different symbol",
        "get-callees-iteration-assert_is_full.json"),
    ("find_first_non_full", "index"): (
        "cord_rep_btree.h:300",
        "raw_hash_set.cc:207-210 calls find_first_non_full_from_h1, H1 and "
        "capacity_impl; nothing named index, and cord_rep_btree.h is outside "
        "the subset",
        "get-callees-group-probing-find_first_non_full.json"),
    ("Incr", "next"): (
        "chunked_queue.h:148",
        "chunked_queue::Incr does not call probe_seq::next; the name collides "
        "because raw_hash_set.h has no class scope in the index",
        "get-callers-iteration-next.json"),
}


def load_truth():
    rows = []
    for line in TRUTH.read_text().splitlines():
        if not line or line.startswith("#") or line.startswith("area\t"):
            continue
        area, caller, callee, site, rcaller, rcallee = line.split("\t")
        rows.append({"area": area, "caller": caller, "callee": callee,
                     "site": site, "rust_caller": rcaller,
                     "rust_callee": rcallee})
    return rows


def load_codesight():
    rows = codesight_edges.collect([])
    edges, notfound, empty = {}, {}, {}
    for row in rows:
        if row["status"] == "ok":
            edges.setdefault((row["caller"], row["callee"]), []).append(row)
        elif row["status"] == "not-found":
            notfound.setdefault(row["requested"].rsplit("-", 1)[-1], []).append(row)
        elif row["status"] == "empty":
            empty.setdefault(row["subject"], []).append(row)
    return edges, notfound, empty


def load_ligature():
    report = json.loads(LIGATURE.read_text())
    resolved, unresolved = {}, {}
    for site in report["callsites"]:
        callee = site.get("callee")
        caller = f"{site['caller']['concept']}::{site['caller']['method']}"
        key = (caller, f"{callee['concept']}::{callee['method']}" if callee
               else site.get("unresolved_expression", "?"))
        (resolved if callee else unresolved)[key] = site
    return report, resolved, unresolved


def norm(name):
    """codesight-mcp qualifies a member with its class (`GrowthInfoAccessor::
    OverwriteFullAsEmpty`) while edge-truth.tsv uses the bare member name.
    Match on the last segment; record both spellings in the report."""
    return name.rsplit("::", 1)[-1] if name else name


def codesight_verdict(edge_key, edges, notfound):
    """recovered / recovered-at-depth-N+ / absent-but-probed / not-probed."""
    hits = edges.get(edge_key) or edges.get((norm(edge_key[0]), norm(edge_key[1])))
    if hits:
        depths = sorted({h["depth"] for h in hits})
        return ("recovered", depths[0], hits[0]["artefact"])
    if norm(edge_key[1]) in notfound:
        return ("symbol-not-found", None,
                notfound[norm(edge_key[1])][0]["artefact"])
    return ("silent", None, None)


def ligature_verdict(row, resolved, unresolved):
    caller, callee = row["rust_caller"], row["rust_callee"]
    if caller == NA or callee == NA:
        return "no-fixture-row"
    if (caller, callee) in resolved:
        return "resolved"
    prefix = caller + "\x00"
    for (rc, callee_name) in unresolved:
        if rc == caller and callee_name.endswith(callee.split("::")[-1]):
            return "unresolved"
    for (rc, _callee) in unresolved:
        if rc == caller:
            return "caller-present-callee-unresolved"
    for (rc, callee_name) in resolved:
        if rc == caller:
            return "caller-present-other-callee"
    return "not-recorded"


def main():
    truth = load_truth()
    edges, notfound, empty = load_codesight()
    report, resolved, unresolved = load_ligature()

    rows = []
    for row in truth:
        cs_state, cs_depth, cs_artefact = codesight_verdict(
            (row["caller"], row["callee"]), edges, notfound)
        row = {**row, "codesight": cs_state, "codesight_depth": cs_depth,
               "codesight_artefact": cs_artefact,
               "ligature": ligature_verdict(row, resolved, unresolved)}
        rows.append(row)

    # recorded codesight edges that are not in the truth table
    truth_edges = {(r["caller"], r["callee"]) for r in truth}
    truth_norm = {(norm(a), norm(b)) for a, b in truth_edges}
    extra = sorted(k for k in edges
                   if k not in truth_edges and (norm(k[0]), norm(k[1])) not in truth_norm)

    if "--json" in sys.argv:
        json.dump({"truth": rows, "codesight_edges_not_in_truth":
                   [list(k) for k in extra]}, sys.stdout, indent=1)
        print()
        return

    by_area = {}
    for row in rows:
        by_area.setdefault(row["area"], []).append(row)

    print("ligature extract-c-static over subset-port/ "
          f"(target {report['config_scope']['target']}): "
          f"{report['callsite_coverage']['discovered']} discovered, "
          f"{report['callsite_coverage']['resolved']} resolved, "
          f"{report['callsite_coverage']['unresolved']} unresolved; "
          f"attribution_scope unattributed="
          f"{report['attribution_scope']['unattributed_call_sites']}, "
          f"out_of_scope="
          f"{report['attribution_scope']['out_of_scope_call_sites']}")
    print()
    print(f"{'area':<16} {'true edges':>10} {'cs ok':>6} {'cs NF':>6} "
          f"{'cs silent':>10} | {'lig resolved':>12} {'lig unres':>9} "
          f"{'lig silent':>10} {'no row':>7}")
    for area, arows in by_area.items():
        n = len(arows)
        cs_ok = sum(r["codesight"] == "recovered" for r in arows)
        cs_nf = sum(r["codesight"] == "symbol-not-found" for r in arows)
        cs_s = sum(r["codesight"] == "silent" for r in arows)
        lg_r = sum(r["ligature"] == "resolved" for r in arows)
        lg_u = sum(r["ligature"] in ("unresolved", "caller-present-callee-unresolved")
                   for r in arows)
        lg_s = sum(r["ligature"] in ("not-recorded", "caller-present-other-callee")
                   for r in arows)
        lg_n = sum(r["ligature"] == "no-fixture-row" for r in arows)
        print(f"{area:<16} {n:>10} {cs_ok:>6} {cs_nf:>6} {cs_s:>10} | "
              f"{lg_r:>12} {lg_u:>9} {lg_s:>10} {lg_n:>7}")
    totals = {
        "true edges": len(rows),
        "cs recovered": sum(r["codesight"] == "recovered" for r in rows),
        "cs symbol-not-found": sum(r["codesight"] == "symbol-not-found"
                                   for r in rows),
        "cs silent": sum(r["codesight"] == "silent" for r in rows),
        "lig resolved": sum(r["ligature"] == "resolved" for r in rows),
        "lig unresolved": sum(r["ligature"] in ("unresolved",
                                                "caller-present-callee-unresolved")
                              for r in rows),
        "lig not recorded": sum(r["ligature"] in ("not-recorded",
                                                  "caller-present-other-callee")
                                for r in rows),
        "no fixture row": sum(r["ligature"] == "no-fixture-row" for r in rows),
    }
    print()
    for key, value in totals.items():
        print(f"{key:<22} {value}")
    print()

    # The single structural fact that matters for this pilot: extract-c-static's
    # blind spot is not the code, it is the *shape* -- a free function on either
    # side of the call, or a receiver that is not `self`.
    def touches_free_function(row):
        return any("free:" in name for name in (row["rust_caller"],
                                                row["rust_callee"]))

    buckets = {
        "resolved": [r for r in rows if r["ligature"] == "resolved"],
        "unresolved": [r for r in rows if r["ligature"] in (
            "unresolved", "caller-present-callee-unresolved")],
        "not recorded": [r for r in rows if r["ligature"] in (
            "not-recorded", "caller-present-other-callee")],
    }
    print("ligature verdict vs the shape of the call "
          "(free function on either side?):")
    for name, bucket in buckets.items():
        withfree = sum(touches_free_function(r) for r in bucket)
        print(f"  {name:<14} {len(bucket):>3} edges, {withfree:>3} "
              f"touch a free function, "
              f"{len(bucket) - withfree:>3} do not")
    print()

    print("--- codesight-mcp: true edge NOT recovered, with the reason")
    for row in rows:
        if row["codesight"] != "recovered":
            print(f"  {row['area']:<16} {row['caller']} -> {row['callee']}"
                  f"  ({row['site']})  [{row['codesight']}]")
    print()
    print("--- codesight-mcp: recorded edge NOT in the ground-truth table")
    seen = set()
    for caller, callee in extra:
        for hit in edges[(caller, callee)]:
            if hit["artefact"] in seen:
                continue
            seen.add(hit["artefact"])
            print(f"  {hit['area']:<16} {caller} -> {callee}"
                  f"  ({hit['peer_file']} L{hit['peer_line']}, "
                  f"depth {hit['depth']}, {hit['artefact']})")
    print()
    print("--- codesight-mcp: recorded edges hand-verified FALSE against the "
          "pinned C++")
    for (caller, callee), (site, why, artefact) in VERIFIED_FALSE.items():
        print(f"  {caller} -> {callee}")
        print(f"      codesight-mcp says: {callee} is at {site} "
              f"({artefact})")
        print(f"      pinned source says: {why}")
    print()
    print("--- ligature extract-c-static: verdict per true edge")
    for row in rows:
        print(f"  {row['area']:<16} {row['caller']} -> {row['callee']}"
              f"  rust={row['rust_caller']}->{row['rust_callee']}"
              f"  [{row['ligature']}]")


if __name__ == "__main__":
    main()
