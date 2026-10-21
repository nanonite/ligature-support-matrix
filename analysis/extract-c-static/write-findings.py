#!/usr/bin/env python3
"""Append chainlink #108's comparison findings to findings/limitations.jsonl.

Every entry is `tool: "mcp"` because the task is the codesight-mcp vs ligature
cross-check: what is recorded here is what codesight-mcp got wrong or could not
answer about the subset, measured against the pinned C++ and against
ligature extract-c-static.  Field order and names follow findings-schema.md at
the workspace root.

Run from swisstable-verus/:  analysis/extract-c-static/write-findings.py
"""
import json
import pathlib
import sys

PILOT = pathlib.Path(__file__).resolve().parents[2]
OUT = PILOT / "findings" / "limitations.jsonl"

PYZ_SHA = "9c921eeb1bbb858c0041e49f07cf5d06988eb798ba60b9207f7576cba430637c"
CODESIGHT = "/home/goya/storage/full-ligature-port-workspace/tools/codesight-mcp/.venv/bin/codesight-mcp"
CODESIGHT_VER = ("codesight-mcp 0.6.0 (git 816d523a1126b210afffa8a422760bbfce42f5f6); "
                 "tree-sitter 0.26.0, tree-sitter-c 0.24.2, tree-sitter-cpp 0.23.4")
LIGATURE = str(PILOT / "tools" / "ligature" / "ligature.pyz")
LIGATURE_VER = "ligature 1.2.0"

ENV = (f"CODE_INDEX_PATH={PILOT}/analysis/codesight/index "
       f"CODESIGHT_ALLOWED_ROOTS={PILOT}/upstream:{PILOT}/rust {CODESIGHT}")

FINDINGS = [
    {
        "id": "swisstable-mcp-013",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{PILOT}/analysis/extract-c-static/compare.py "
                   "(edge-truth.tsv x codesight recorded artefacts)",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "Of the 63 hand-verified true C++ call edges in the subset "
            "(edge-truth.tsv, every one cited to a line in upstream/abseil-cpp "
            "2065f4de), codesight-mcp's 101 recorded caller/callee artefacts "
            "recover 28. Five more it answers with an explicit `Symbol not "
            "found` at exit 1. The remaining 30 it never asks about at all: no "
            "recorded artefact covers them, so the index gap is silent -- there "
            "is no error and no zero-count answer to distinguish them from "
            "'the relationship does not exist'. The worst-covered area is "
            "tombstones: 6 of 19. The rehash area loses its hub "
            "DropDeletesWithoutResizeAndPrepareInsert (raw_hash_set.cc:593) "
            "entirely, so the 6 edges through it are all silent."),
        "repro_cmd": f"cd {PILOT}/analysis/extract-c-static && ./compare.py",
        "exit_code": 0,
        "expected": ("get-callers / get-callees over the subset returns the real "
                     "call graph of raw_hash_set.{h,cc} and "
                     "hashtable_control_bytes.h."),
        "actual": ("28 of 63 true edges recovered; 30 true edges never "
                   "probed by any of the 101 recorded artefacts; 3 recorded "
                   "edges hand-verified false (see swisstable-mcp-014). Full "
                   "table at analysis/extract-c-static/comparison-report.txt."),
        "workaround": ("Treat the codesight graph as a lower bound on the C++ "
                       "call graph and re-derive every edge from the pinned "
                       "source before using it in a reliance graph."),
        "severity": "scope-cut",
        "revisit_trigger": ("Re-run compare.py after any codesight-mcp or "
                            "tree-sitter-cpp update, or after the P3 pilot "
                            "needs the same edges."),
        "pyz_sha256": PYZ_SHA,
        "tool_path": CODESIGHT,
        "tool_version": CODESIGHT_VER,
    },
    {
        "id": "swisstable-mcp-014",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{ENV} get-callees --repo local/upstream-757424f7156f "
                   "--symbol abseil-cpp/absl/container/internal/raw_hash_set.cc::find_first_non_full",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "A third hand-verified false edge, independent of the two #26 "
            "recorded. get-callees for raw_hash_set.cc::find_first_non_full "
            "returns `absl/strings/internal/cord_rep_btree.h::index` (L300) as "
            "a callee at depth 2, alongside the two real ones "
            "(raw_hash_set.h::offset L1783, ::next L1785). "
            "find_first_non_full (raw_hash_set.cc:207-210) calls "
            "find_first_non_full_from_h1, H1 and capacity_impl, and nothing "
            "named index; cord_rep_btree.h is outside the subset entirely. "
            "Exit 0, no warning, and the false peer sits in the same list as "
            "two correct ones, so it is not separable by exit code. Same root "
            "cause as swisstable-mcp-003: the .h parse keeps no class scope, so "
            "the match is on a bare file-level name."),
        "repro_cmd": (f"cd {PILOT}/analysis/codesight && tail -n +2 "
                      "get-callees-group-probing-find_first_non_full.json | "
                      "python3 -c 'import json,sys; d=json.load(sys.stdin); "
                      "print([c[\"id\"].split(chr(10))[1] for c in d[\"callees\"]])'"),
        "exit_code": 0,
        "expected": ("only symbols actually called from find_first_non_full: "
                     "find_first_non_full_from_h1 and H1 at depth 1, and "
                     "seq.offset()/seq.next() at depth 2."),
        "actual": ("cord_rep_btree.h::index (L300) appears in the callee list "
                   "instead of a depth-1 find_first_non_full_from_h1 / H1 "
                   "pairing; find_first_non_full_from_h1 and H1 are missing "
                   "from this artefact entirely even though the get-callers "
                   "artefact for the same function resolves them."),
        "workaround": ("Reject any callee whose file is outside the subset, "
                       "and reject any edge whose endpoints are bare .h names "
                       "-- the rule analysis/codesight/README.md already "
                       "adopts, now with three verified counterexamples."),
        "severity": "blocker",
        "revisit_trigger": ("Codesight-mcp gains scoped resolution, or "
                            "tree-sitter-cpp is used for .h (see "
                            "swisstable-mcp-001)."),
        "pyz_sha256": PYZ_SHA,
        "tool_path": CODESIGHT,
        "tool_version": CODESIGHT_VER,
    },
    {
        "id": "swisstable-mcp-015",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{LIGATURE} extract-c-static --target x86_64-unknown-linux-gnu",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "SCOPE CUT on the comparison this issue asks for, now measured "
            "rather than assumed: extract-c-static scans Rust only. Its own "
            "report says so (coverage_scope.extractor "
            "'coarse-syntactic-callgraph', backing 'syntactic', "
            "scanned_item_kinds ['inherent-impl-method','trait-impl-method'], "
            "unsupported_call_forms ['macro-expanded-call','generated-code',"
            "'ffi-callback','call-to-non-local-type']), and swisstable-verus/"
            "rust/ still contains only .gitkeep because no crate exists yet. "
            "So there is no input on which ligature and codesight-mcp are both "
            "answering the same question: ligature cannot see the C++ subset "
            "and codesight-mcp cannot see the Rust side. Any claim that the two "
            "'agree' or 'disagree about the C++ call sites' would be "
            "meaningless. The fixture in analysis/extract-c-static/subset-port/ "
            "is a hand-written transcription of the pinned C++; running "
            "extract-c-static over it measures the extractor's coverage, not "
            "agreement about abseil."),
        "repro_cmd": (f"cd {PILOT}/analysis/extract-c-static && "
                      "./run-subset-port.sh && cat subset-port-run.txt"),
        "exit_code": 0,
        "expected": ("a comparison of the same C++ call graph from both tools, "
                     "or a documented statement that the two tools cover "
                     "disjoint languages."),
        "actual": ("extract-c-static refuses to look at C++ at all and produced "
                   "43 discovered / 25 resolved / 18 unresolved purely over "
                   "Rust sources supplied by hand. commands: exit 0, report "
                   "written to ci/results/c_static/."),
        "workaround": ("Record the two axes separately, as this directory "
                       "does: axis 1 codesight-mcp vs the pinned C++ source "
                       "(ground truth in edge-truth.tsv), axis 2 ligature "
                       "extract-c-static vs the Rust transcription. Do not "
                       "quote a single combined agreement number."),
        "severity": "scope-cut",
        "revisit_trigger": ("Once the P2 crate exists under rust/ and real "
                            "Rust code exists, re-run both axes; and re-check "
                            "whether a later ligature release adds a C-side "
                            "extractor."),
        "pyz_sha256": PYZ_SHA,
        "tool_path": LIGATURE,
        "tool_version": LIGATURE_VER,
    },
    {
        "id": "swisstable-mcp-016",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{LIGATURE} extract-c-static --target x86_64-unknown-linux-gnu",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "The extractor's blind spot is the *shape* of the call, not the "
            "code, and for this subset that means most of the graph. Over the "
            "transcription: all 35 true edges it fails to record at all touch "
            "a free function on one side, and all 13 it resolves touch none "
            "(derived, not asserted: comparison-report.txt, 'ligature verdict "
            "vs the shape of the call'). A 24-probe matrix "
            "(analysis/extract-c-static/probes/, results/) pins each cause: "
            "free functions and trait default bodies produce 0 callsites and "
            "are counted only in unattributed_call_sites (probe 06, 2 dropped "
            "of 2; probe 07, 1 of 1); a call on any receiver other than `self` "
            "-- a local binding (03), a field (09), an array element "
            "(`self.ctrl[i].is_empty()`), a trait parameter (`policy."
            "is_deleted()`) -- is recorded as "
            "call_class 'possible-dispatch' with the callee dropped (03, 09); "
            "and a call to a method that does not exist anywhere in the crate "
            "is dropped with no record at all: probe 04 reports 0 discovered, "
            "0 resolved, 0 unresolved, exit 0 (04-missing-callee). So for the "
            "exact port shape P2 needs -- `seq.next()`, `g.MaskFull()`, "
            "`policy.hash_fn()`, which is how raw_hash_set.cc:184, "
            "hashtable_control_bytes.h:310 and raw_hash_set.cc:623 are written "
            "-- the C_static report is empty at exit 0."),
        "repro_cmd": (f"cd {PILOT}/analysis/extract-c-static && "
                      "./run-probes.sh && python3 -m json.tool "
                      "results/04-missing-callee.json | grep -A4 "
                      "callsite_coverage"),
        "exit_code": 0,
        "expected": ("a call graph over the Rust port that includes free "
                     "functions, cross-receiver calls and calls to methods that "
                     "are declared but not yet implemented."),
        "actual": ("43 discovered, 25 resolved, 18 unresolved, "
                   "attribution_scope.unattributed_call_sites 45 and "
                   "out_of_scope_call_sites 16 over a 6-module transcription "
                   "of the subset; probe 04 shows a missing callee is not even "
                   "counted as unresolved."),
        "workaround": ("Every call site that matters to the port must be on "
                       "`self` or written `Type::method(...)` for it to appear; "
                       "cross-check the port's shape against probes/ before "
                       "trusting the report's discovered count."),
        "severity": "scope-cut",
        "revisit_trigger": ("When the P2 crate exists, and again at any "
                            "ligature release that changes "
                            "coverage_scope.unsupported_call_forms."),
        "pyz_sha256": PYZ_SHA,
        "tool_path": LIGATURE,
        "tool_version": LIGATURE_VER,
    },
    {
        "id": "swisstable-mcp-017",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{LIGATURE} extract-c-static --target x86_64-unknown-linux-gnu",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "attribution_scope.unattributed_call_sites cannot be reconciled "
            "with the report's own callsites list, so the one number in the "
            "report that is supposed to quantify what was dropped cannot be "
            "audited. Probe 19-no-calls-at-all has zero call sites in the "
            "source and still reports unattributed_call_sites 2; probes 23 "
            "(`ensures (c as int < 256)`) and 24 (`ensures (forall|c: u8| "
            "true)`) show a spec-clause expression each contribute 1, while "
            "probes 06 and 07 show dropped free-function and trait-default "
            "calls also land in the same counter. Two different populations, "
            "one counter, no per-site record anywhere in the schema. "
            "contradiction_claim: the field name says call sites and the "
            "counters do not."),
        "repro_cmd": (f"cd {PILOT}/analysis/extract-c-static && ./run-probes.sh "
                      "&& for p in 19-no-calls-at-all 23-ensures-cast "
                      "24-forall-quantifier; do echo \"== $p\"; python3 -m "
                      "json.tool results/$p.json | grep -A6 "
                      "attribution_scope; done"),
        "exit_code": 0,
        "expected": ("unattributed_call_sites equals the number of call sites "
                     "the extractor saw and could not attribute, and is "
                     "derivable from the report."),
        "actual": ("2 in a file with no calls at all (probe 19); 1 per "
                   "spec-clause expression (probes 23, 24); 2 for 2 dropped "
                   "free-function calls (probe 06); 1 for 1 dropped "
                   "trait-default-body call (probe 07)."),
        "workaround": ("Do not use unattributed_call_sites as a coverage "
                       "measure. Use callsite_coverage plus the probe matrix, "
                       "both of which are reproducible from the report."),
        "severity": "friction",
        "revisit_trigger": "Any ligature release that changes the C_static "
                           "report schema or the extractor's attribution.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": LIGATURE,
        "tool_version": LIGATURE_VER,
    },
    {
        "id": "swisstable-mcp-018",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": (f"cd {PILOT}/analysis/extract-c-static && "
                    "./classify-not-found.py"),
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "A `Symbol not found` at exit 1 is only evidence of a tree-sitter "
            "gap if the symbol exists in the pinned source at all, and at "
            "2065f4de (tag 20260817.0) a large part of what #26 probed is gone: "
            "the 2026 LTS branch renamed the resize layer "
            "(GrowToNextCapacity cc:1615 / GrowToNextCapacityAndPrepareInsert "
            "cc:1778 / DropDeletesWithoutResizeAndPrepareInsert cc:593), the "
            "erase layer (erase_meta_only h:3482 and friends) and the SIMD "
            "group API (Match hcb:291, no MatchFull/MatchEmptyOrDeleted). "
            "Derived by classify-not-found.py over all 48 `Symbol not found` "
            "artefacts, which ask for 32 distinct symbols: 13 symbols / 19 "
            "artefacts have ZERO occurrences anywhere under absl/ (EraseImpl, "
            "EraseSingleElement, EraseWithRehash, EraseWithoutRehash, "
            "GroupImpl, MakeDeleted, MakeEmpty, MatchEmptyOrDeleted, "
            "MatchFull, ResizeAllowedWithoutRehash, ResizeImpl, "
            "ResizeWithoutDeletingOrCreatingNewSlots, Simd) so codesight-mcp is "
            "CORRECT and these are not gaps; 1 symbol / 2 artefacts (Resize) "
            "has a whole-word hit only outside the subset "
            "(inlined_vector.h:621, a different container); 1 (resize_impl) is "
            "substring-only in a Bazel target name; and 17 symbols / 26 "
            "artefacts do have a whole-word definition in a subset file and are "
            "real index gaps. Per area, real gaps vs total not-found: erase "
            "4/8, group probing 8/16, tombstones 4/6, iteration 1/1, rehash "
            "9/17. So #26's rehash '17 gaps' is really 9 real gaps plus 5 "
            "absent and 3 borderline names."),
        "repro_cmd": (f"cd {PILOT}/analysis/extract-c-static && "
                      "./classify-not-found.py && head -8 not-found-absent.tsv "
                      "&& cat not-found-present.tsv"),
        "exit_code": 0,
        "expected": "the probed symbols exist at the pinned tag, so `Symbol "
                    "not found' isolates a tree-sitter failure.",
        "actual": ("13 of the 32 distinct requested symbols do not exist at "
                   "this tag (zero `git grep -F` hits under absl/), so for "
                   "those `Symbol not found` is the correct answer and #26's "
                   "reading of every negative as index damage over-counts. The "
                   "split is derived, not asserted: classify-not-found.py greps "
                   "each symbol three ways (whole-word over the five P2 subset "
                   "files, whole-word over absl/, substring over absl/) and "
                   "writes not-found-{absent,present,present-weak,out-of-"
                   "subset}.tsv plus not-found-classify.txt."),
        "workaround": ("Check every `Symbol not found` against the pinned "
                       "source before attributing it to codesight-mcp, and "
                       "scope the check to whole-word hits in the subset files "
                       "-- a bare `grep -F Resize` matches "
                       "inlined_vector.h:621 and `grep -F Match` matches "
                       "log_severity_test.cc:86, both false 'present's. "
                       "classify-not-found.py does this for the subset."),
        "severity": "friction",
        "revisit_trigger": ("If the upstream checkout is re-pinned to a tag "
                            "that restores Resize/ResizeImpl/EraseImpl/"
                            "MatchFull, re-run classify-not-found.py; the "
                            "absent list should shrink."),
        "pyz_sha256": PYZ_SHA,
        "tool_path": CODESIGHT,
        "tool_version": CODESIGHT_VER,
    },
    {
        "id": "swisstable-mcp-019",
        "pilot": "swisstable-verus",
        "stage": "phase-0-cross-check",
        "command": f"{LIGATURE} check --json",
        "tool": "mcp",
        "chain": "A.1",
        "symptom": (
            "`check --json` recommends `refresh-c-static` as the one "
            "automated next action (action_id refresh-c-static, command "
            "`ligature extract-c-static --target <target-triple>`), but "
            "running that exact command in this root fails at exit 1 with "
            "'crate rust/swisstable-verus-core in the project descriptor: "
            "crate root does not exist or is not a directory' -- the crate the "
            "#27 descriptor declares is a later issue, and its Cargo.toml is a "
            "protected_root so it cannot be created to satisfy the "
            "recommendation. The recommended action is therefore not "
            "performable at the point the gate recommends it. Not filed as an "
            "escalation: the message is graceful and names the missing path, so "
            "this is a lifecycle ordering observation, recorded so the P2 chain "
            "does not lose time to it."),
        "repro_cmd": (f"cd {PILOT} && {LIGATURE} check --json | python3 -m "
                      "json.tool | grep -A3 next_action; cd " + str(PILOT) +
                      f" && {LIGATURE} extract-c-static --target "
                      "x86_64-unknown-linux-gnu; echo exit=$?"),
        "exit_code": 1,
        "expected": "either the crate root exists when refresh-c-static is "
                    "recommended, or check recommends it only once it does.",
        "actual": ("check --json exit 0 recommends refresh-c-static; the named "
                   "command then exits 1 with 'crate root does not exist or is "
                   "not a directory: rust/swisstable-verus-core'."),
        "workaround": ("Run extract-c-static against an rsync copy of the "
                       "pilot that has the crate directory, as "
                       "analysis/extract-c-static/run-subset-port.sh does; "
                       "re-run it in place once the crate exists."),
        "severity": "friction",
        "revisit_trigger": "When the P2 crate is scaffolded, re-run "
                           "extract-c-static in place and drop this entry if "
                           "the recommendation becomes performable.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": LIGATURE,
        "tool_version": LIGATURE_VER,
    },
]

FIELDS = ("id pilot stage command tool chain symptom repro_cmd exit_code "
          "expected actual workaround severity revisit_trigger pyz_sha256 "
          "tool_path tool_version").split()


def main():
    """Rewrite this issue's findings, replacing any earlier version of them.

    --replace drops the ids this file owns and re-appends them, so a corrected
    finding never sits next to the superseded text it replaces.  Ids belonging
    to other issues (and #26's) are never touched.
    """
    replace = "--replace" in sys.argv
    owned = {finding["id"] for finding in FINDINGS}
    existing = [json.loads(line) for line in OUT.read_text().splitlines()
                if line.strip()]
    kept = [row for row in existing if row["id"] not in owned]
    replaced = len(existing) - len(kept)

    OUT.write_text("".join(json.dumps({k: row[k] for k in FIELDS}) + "\n"
                           for row in kept))
    for finding in FINDINGS:
        missing = set(FIELDS) - set(finding)
        assert not missing, f"{finding['id']} missing {missing}"
    with OUT.open("a") as handle:
        for finding in FINDINGS:
            handle.write(json.dumps({k: finding[k] for k in FIELDS}) + "\n")
            print(f"{'rewrote' if replace else 'appended'} "
                  f"{finding['id']} ({finding['severity']})")
    print(f"{len(FINDINGS)} from this issue, {len(kept)} pre-existing, "
          f"{len(kept) + len(FINDINGS)} total"
          + (f" ({replaced} superseded entr(y/ies) replaced)"
             if replaced else ""))


if __name__ == "__main__":
    main()
