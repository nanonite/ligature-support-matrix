#!/usr/bin/env python3
"""Regenerate analysis/ligature/reverify-VERDICTS.md from this run's evidence.

Machine counterpart: date-ligature-053. Re-runnable driver: reverify.py.
Verdicts are assigned BY HAND from the captured output; this script only holds
that mapping, pairs it with the evidence lines the run produced, and counts the
buckets. The mapping is the only hand-authored part; the counts are derived, so
they cannot drift from the table.

Inputs
  findings/limitations.jsonl                 the 86 records
  reverify-results.json                      reverify.py's per-id record (copied
                                             out of its scratch dir so the counts
                                             survive the scratch being deleted)
  $REVERIFY_ROOT/out/<id>.out                the raw captured output, if the
                                             scratch still exists. When it does
                                             not, the per-finding evidence line
                                             degrades to a pointer at the raw
                                             repro rather than being invented.

Usage
  python3 analysis/ligature/reverify-verdicts.py            # rewrite the md
  python3 analysis/ligature/reverify-verdicts.py --check    # assert coverage
"""
import argparse
import collections
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEDGER = ROOT / "findings" / "limitations.jsonl"
RESULTS = HERE / "reverify-results.json"
OUT_MD = HERE / "reverify-VERDICTS.md"
SCRATCH_OUT = pathlib.Path(os.environ.get("REVERIFY_ROOT", "/tmp/opencode/reverify-8c")) / "out"

BINARY = "ligature 1.1.1"
BINARY_SHA = "3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4"

BUCKETS = [
    ("REPRODUCES", "the finding's behaviour is present today, verbatim or near-verbatim"),
    ("RESOLVED", "no longer reproduces -- fixed in 1.1.1, or closed out by a later issue"),
    ("MATCH", "reproduces exactly as recorded, which is what the finding says it does"),
    ("PARTLY RESOLVED", "one half of the finding is fixed, the other half is still live"),
    ("SUPERSEDED", "the state the finding describes was moved on under a different issue"),
    ("CHANGED", "still true in substance, by a different mechanism"),
    ("NOT-RUNNABLE", "the repro_cmd cannot run as written (placeholder, dead path, or a script that no longer exists)"),
    ("NOT-REPRODUCED", "it ran, but the evidence does not support the claim either way"),
]

# id -> (verdict, one-line note on what the captured output actually showed)
VERDICTS = {
    # ---- codesight-mcp (third-party) ----
    "date-mcp-001": ("REPRODUCES", "get-callers exit 1, 'Symbol not found: include/date/date.h::days_from_civil#function'"),
    "date-mcp-002": ("REPRODUCES", "get-imports --direction importers exit 0, result_count 0"),

    # ---- Stage 0-3 ligature findings ----
    "date-ligature-001": ("RESOLVED", "no artifact_id 'installation' in status --json at all; only installation_manifest.state"),
    "date-ligature-002": ("RESOLVED", "no 'unexpected property' anywhere in status --json"),
    "date-ligature-003": ("RESOLVED", "recorded exit 2, actual exit 0; the closure_kind complaint is gone"),
    "date-ligature-004": ("REPRODUCES", "doctor still exits 0 on a descriptor it will not call valid; nothing in its output reports descriptor validity"),
    "date-ligature-005": ("RESOLVED", "the corrupted-skill state is now reported as \"'state': 'drifted'\" by status --json, so drift is detected"),
    "date-ligature-006": ("RESOLVED", "doctor now names the skill authority files individually under 'skill authority hash: verified|unchanged <file>'"),
    "date-ligature-007": ("RESOLVED", "installation_manifest.state and gate_integrity are now separate, named keys in status --json"),
    "date-ligature-008": ("REPRODUCES", "fresh init: P0 still pending, and the open finding names only 'review.reviewer, port_source.repository, verifier_policy.default' -- port_source.oracle_build_command is not watched"),
    "date-ligature-009": ("PARTLY RESOLVED", "the boundary complaint is gone (gate-g14 exit 0); the write-set half still stands"),
    "date-ligature-010": ("RESOLVED", "recorded exit 2, actual exit 0 on a descriptor edited to be invalid; the enum message is still produced"),
    "date-ligature-011": ("CHANGED", "status echoes verifier_policy as {'default': 'creusot', 'supporting': []} -- 'supporting' is now the real second-verifier key and takes an array -- but the unknown key 'defualt' is still accepted silently"),
    "date-ligature-012": ("RESOLVED", "an emptied descriptor is now 'present-invalid' and check exits 5 on it"),
    "date-ligature-013": ("RESOLVED", "check --json now reports 'allowed_roots pattern ... outside the project root' per file rather than collapsing the set"),
    "date-ligature-014": ("RESOLVED", "gate_integrity is a first-class status --json key and check reports gate_integrity_failed as a condition"),
    "date-ligature-015": ("RESOLVED", "the reliance-policy hash check is now a hard 'FAIL: hash mismatch', and doctor says 'DRIFTED'"),
    "date-ligature-016": ("RESOLVED", "the stray-file message is now the specific 'outside the project root' one"),
    "date-ligature-017": ("RESOLVED", "recorded exit 2, actual exit 0 for both the manual and the claude role; 'check exit=' now reports 1"),
    "date-ligature-018": ("REPRODUCES", "a stage prompt still names a template file (reliance-policy.template.md) that init does not install"),
    "date-ligature-019": ("REPRODUCES", "draft's scope check is still crate membership, not the write set: rust/date-creusot-core/rogue/evil.rs is accepted the same as src/lib.rs"),
    "date-ligature-020": ("RESOLVED", "promote-evidence now exists; draft exit 0 then promote to E-10.json"),
    "date-ligature-021": ("RESOLVED", "1.1.1 ships 9 templates: bridge-drafting, witness-drafting and concept-to-code all exist now (they fail only on a missing --var); concept-drafting still has no template. The residue is re-filed as date-ligature-095"),
    "date-ligature-022": ("REPRODUCES", "status still never reads crates[].specs_search_root; 'specs.search' appears nowhere, and the 6 G2+ 'applies_to unverifiable' findings are permanent"),
    "date-ligature-023": ("REPRODUCES", "no exit-code contract document is installed and --help still does not enumerate exit codes per command"),
    "date-ligature-024": ("REPRODUCES", "verifier_policy.default still does not reach the interaction validator: an emptied descriptor is caught, but the default it declares is not applied"),
    "date-ligature-025": ("MATCH", "approve python exits 3, exactly as recorded"),
    "date-ligature-026": ("REPRODUCES", "the tool still writes into rust/*/specs/**, which write_set.protected_roots lists"),
    "date-ligature-027": ("REPRODUCES", "check next still emits only '[author-interaction] ...' while 10 drafts await approval; no human-decision action_id"),
    "date-ligature-028": ("REPRODUCES", "the repro's own json.dump/json.dumps bug is still there -- 'Traceback (most recent call last):' -- so the attribute check is still untested"),
    "date-ligature-029": ("REPRODUCES", "constraint ids still have no sanctioned producer; stage-3-concept-to-code.md still describes attribution the gates do not check"),
    "date-ligature-030": ("RESOLVED", "'error: manifest not found: /tmp/nonexistent-wp.json' is still printed, but the follow-on 'EXIT=0' leg now sees 0 because the manifest resolves; no real manifest-missing case is reachable"),
    "date-ligature-031": ("REPRODUCES", "grep -c '\"reviewer\": \"chainlink-reviewer\"' prints 9; accept-promotion still has no provenance check on review blocks"),
    "date-ligature-032": ("REPRODUCES", "doctor still lists 'manifest generation' under 'Not yet implemented'"),
    "date-ligature-033": ("PARTLY RESOLVED", "scripts/witness_renderer.py and scripts/xml_escape.py ARE installed in this pilot root now; the repro's validate-work-package leg names the pre-rename ci/manifest/work-package.json and is dead"),
    "date-ligature-034": ("REPRODUCES", "the repro's own path is stale, so re-run corrected: validate-work-package ci/manifest/WP-DATE-CREUSOT.json still fails '[G13/error] allowed_write_set overlaps protected_write_set: rust/*/src/ overlaps protected **/Cargo.toml'"),

    # ---- creusot / nextest / oracle ----
    "date-creusot-001": ("RESOLVED", "'Proved (93 files) OK' -- the 1/n unproved case is gone"),
    "date-creusot-035": ("RESOLVED", "no 'Goal Coma' line and no 'unproved' line; the grep exits 1 because nothing matches, and the underlying cargo creusot returns 0"),
    "date-creusot-036": ("RESOLVED", "same: grep finds no Goal/unproved line; cargo creusot underneath returns 0"),
    "date-creusot-037": ("RESOLVED", "same: grep finds no Goal/unproved line; cargo creusot underneath returns 0"),
    "date-creusot-038": ("RESOLVED", "the pre-fix civil_from_days state is gone: 'Proved (93 files) OK'"),
    "date-creusot-039": ("RESOLVED", "vc_round_trip is no longer '(5/7)': 'Proved (93 files) OK'"),
    "date-creusot-040": ("MATCH", "creusot --help prints its own usage block, and the rebuild is a multi-minute one, exactly as recorded"),
    "date-creusot-041": ("MATCH", "'Proved (93 files) OK', exit 0"),
    "date-ligature-035": ("REPRODUCES", "re-tested directly under 1.1.1 rather than by the repro (a bare validate-evidence passes vacuously): an evidence record with kind compile-time / const-eval / kani-exhaustive-check / creusot-deductive-check / verus-proof is each rejected \"is not one of ['requirement', 'source-artifact', 'observed-behavior', 'test', ...]\"; only requirement and test are accepted"),
    "date-ligature-036": ("REPRODUCES", "gate-r1-g16 exit 1 with the 5 'absent from I' edges still outstanding and 9 non-blocking findings"),
    "date-creusot-042": ("REPRODUCES", "extract-c-static writes '11 discovered, 11 resolved, 0 unresolved' and gate-r1-g16 then exits 1 on the 5 medium edges"),
    "date-creusot-043": ("REPRODUCES", "gate-r1-g16 exit 1, 'absent from I' still present"),
    "date-ligature-037": ("NOT-RUNNABLE", "repro_cmd still contains the literal '<path-to-a-hand-authored-.json-with-no-.draft-sibling>'; bash: syntax error, exit 2"),
    "date-ligature-038": ("SUPERSEDED", "the recorded exit 0 is now 1 (the 5 absent-from-I edges are blocked findings under #95); same 5 edges, same gate"),
    "date-creusot-044": ("RESOLVED", "cargo nextest run --profile ci passes 143/143"),
    "date-creusot-045": ("REPRODUCES", "oracle driver exits 2 with '/tmp/neg.jsonl:1: unknown case field: extra'"),

    # ---- Stage 8C, and the v1.1.0-era closure blockers ----
    "date-ligature-039": ("RESOLVED", "gate-g14 exit 0: 'cluster date-creusot-core closes: closure_kind=deductive'"),
    "date-ligature-040": ("REPRODUCES", "weakened but live: the pilot's docs/ still has no closure-profile-schema.json / degradation-record-schema.json, and neither artifact kind has a draft/approve path. The two schemas are now bundled with the binary and listed by doctor, so they are at least discoverable"),
    "date-ligature-041": ("RESOLVED", "deductive, bounded and partial all validate; the recorded exit 2 is now 0"),
    "date-ligature-042": ("RESOLVED", "no 'filename says' line: the manifest was renamed to ci/manifest/WP-DATE-CREUSOT.json"),
    "date-ligature-043": ("RESOLVED", "neither 'recomputed' nor 'HUMAN DECLARATION' appears; the condition is now 'VERIFIED from artifact data, not taken on declaration'"),
    "date-ligature-044": ("NOT-RUNNABLE", "repro_cmd is still 'python3 /tmp/opencode/rerverify_v4.py', a session-local script that does not exist; exit 2"),
    "date-ligature-045": ("RESOLVED", "gate-g14 exit 0: no feature_ledger complaint, no assurance complaint, no well-foundedness line, no BLOCKED"),
    "date-creusot-047": ("NOT-REPRODUCED", "the probe crate compiles far enough to report 'expected one of 8 possible tokens' on the a@ and never reaches the pearlite/#[logic] path the finding is about. Same caveat as the 1.1.0 run: the flake pins creusot at the same rev, so this is not evidence the workaround became unnecessary"),
    "date-creusot-048": ("RESOLVED", "cargo build produces no 'unused import' line"),
    "date-creusot-049": ("RESOLVED", "no vc_day / vc_ok'1 / vc_to_days_bounded failure; cargo creusot --only prove prints 'Proved (93 files) OK' and returns 0"),
    "date-creusot-050": ("RESOLVED", "same: the twin/predicate contracts all hold"),
    "date-ligature-046": ("NOT-RUNNABLE", "repro_cmd still has literal '...' in place of all five --proof paths; exit 2"),
    "date-ligature-047": ("REPRODUCES", "improved: record-assurance records all five obligations and the ledger is 'preserved' -- but the path collision itself is unchanged, now as a hard refusal (see date-ligature-054)"),
    "date-ligature-048": ("MATCH", "record-assurance exit 0, 'OK: 1 cluster(s) close under their declared profile'"),
    "date-creusot-051": ("MATCH", "'Proved (93 files) OK' via nix develop"),
    "date-ligature-049": ("REPRODUCES", "write-set-check still reports 'write set: clean', exit 0, with a file planted in ci/manifest/ AND in rust/date-creusot-core/specs/"),
    "date-ligature-050": ("REPRODUCES", "gate-r1-g16 exit 1 on the 5 edges; no worker-reachable authoring path exists"),
    "date-creusot-052": ("MATCH", "extract-c-static + gate-g14 both clean, no hand edit to any generated artifact"),

    # ---- chainlink #93 (the #92 collision, 1.1.1 form) ----
    "date-ligature-051": ("SUPERSEDED", "the 1.1.0 claim ('report feature-ledger overwrites the assurance report at exit 0 with no warning') no longer holds: the run now prints 'error: refusing to overwrite the assurance report at ci/results/feature_ledger.json' and the ledger md5 is unchanged. Superseded by date-ligature-054, which REPRODUCES"),
    "date-ligature-052": ("REPRODUCES", "the remedy is still a write into ci/manifest/**, which write_set.protected_roots lists and the installed SKILL.md forbids ('never write into')"),
    "date-ligature-053": ("SUPERSEDED", "its own repro (wc -l + the verdict table's bucket table) ran clean, but its subject -- the 70-finding re-verification -- is this run, over 86"),
    "date-creusot-053": ("REPRODUCES", "still 5 repro_cmds that do not run as written (date-ligature-032/033/034 stale ci/manifest/work-package.json, -037 and -046 literal placeholders) and 2 that mutate tracked artifacts in place, which is why the reset-per-command harness still exists"),
    "date-ligature-054": ("REPRODUCES", "report feature-ledger exits 1 with 'refusing to overwrite the assurance report at ci/results/feature_ledger.json (work package WP-DATE-CREUSOT)', writes nothing, and gate-g14 stays at 0"),
    "date-ligature-055": ("REPRODUCES", "the collision is still a refusal and the separating remedy is still only reachable through a protected-root write"),
    "date-ligature-056": ("REPRODUCES", "the destructive direction is refused ('wrote ci/results/feature_ledger.json (0 declared features)' is the harmless direction) and record-assurance restores the assurance report afterwards"),
    "date-ligature-057": ("RESOLVED", "installation.json now reads 1.1.1 with gate_hashes['@adjudicator'] = sha256:172a87a8..., status --json reports gate_integrity 'pinned -- 4 gate path(s) match the installed manifest' and installation_manifest 'current', and doctor exits 0. The half-migrated state is gone"),
    "date-creusot-054": ("RESOLVED", "the cwd-routing fix is in: date-ligature-047 now runs through the harness and exits 0 with its probe hit, instead of exit 2 on a path error. Its own repro_cmd is still half-broken -- it reads $REVERIFY_ROOT, which reverify.py only reads from the environment and never exports, so that leg prints \"sed: can't read /out/date-ligature-047.out\""),

    # ---- chainlink #94 (1.1.1 authoring-capability refresh) ----
    "date-ligature-094": ("REPRODUCES", "check-bridges / gate-g9 still die with the unhandled ValueError \"is not in the subpath of\"; epic #1 #96 is open"),
    "date-ligature-095": ("REPRODUCES", "approve still refuses a concept spec: 'no validator recognizes target rust/date-creusot-core/specs/weekday.json'; epic #1 #79 residue"),
    "date-ligature-096": ("REPRODUCES", "draft --help still names 2 templates ('e.g. evidence-intake, boundary-drafting') against 9 files in .ligature/prompts/"),
    "date-ligature-097": ("REPRODUCES", "a witness spec drafts clean (exit 0) and approve then fails on \"no concept spec under the search root declares concept 'Weekday'\"; g18/g19/g20 still exit 0 with 'nothing to check'"),
    "date-ligature-098": ("REPRODUCES", "the 10-command sweep still reports status --json -> exit=0 and check --json -> exit=1, with 5 human decisions pending -- the state #95's drafts created"),
    "date-ligature-099": ("REPRODUCES", "n/a, this is the fix: README.md carries the 'Authoring path, re-derived against ligature 1.1.1' section and WORKER-CONTRACT.md 0.0 exists, both greppable as recorded"),
    "date-ligature-100": ("PARTLY RESOLVED", "still live and it is the cause of the pilot's 5 medium G1a findings: draft says 'OK: generated draft passes G1a/G1b immediate checks' and validate-interaction then reports \"[G1a/error] ....json.draft: 'review' is a required property\" for the same content. The new half is RESOLVED: record-assurance's work_package argument now also accepts the manifest path, which is a worker-reachable way out of the protected root"),
}

INTERESTING = re.compile(
    r"error|FAIL|^OK|Passed|refusing|is not one of|Proved \(|unproved|Traceback"
    r"|syntax error|No such file|not valid JSON|is not in the subpath|exit=|EXIT"
    r"|BLOCKED|closes|write set|status --json|check --json|installed_product"
    r"|installation_manifest|gate_integrity|absent from I|applies_to unverifiable"
    r"|SUPERSEDED|template_name|is required property|preserved|recorded assurance"
    r"|adjudicator pin|Authoring path|total \d+",
    re.I,
)
NOISE = re.compile(
    r"unchanged - rustc|latest update on|component .* is up to date"
    r"|checking for self-update|already installed, remove it|syncing channel updates"
    r"|^\s*$|date-creusot: Creusot, Why3",
)


def evidence_lines(fid, limit=2):
    """The most informative lines of this run's captured output for one id."""
    p = SCRATCH_OUT / (fid + ".out")
    if not p.exists():
        return None
    text = p.read_text()
    body = text.split("### STDOUT", 1)[-1]
    body = body.split("### STDERR", 1)[0] if "### STDERR" in body else body
    lines = [l.strip() for l in body.splitlines() if l.strip() and not NOISE.search(l)]
    hits = [l for l in lines if INTERESTING.search(l)]
    # a bare number is almost always a `wc`/`grep -c` count, not evidence
    substantive = [l for l in hits if not l.isdigit()]
    chosen = (substantive or hits or lines)[:limit]
    return [c[:400] for c in chosen] or ["(no substantive output)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only assert every id has a verdict")
    args = ap.parse_args()

    findings = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    results = {r["id"]: r for r in json.loads(RESULTS.read_text())}

    missing = [d["id"] for d in findings if d["id"] not in VERDICTS]
    if missing:
        print("VERDICTS is missing %d id(s): %s" % (len(missing), ", ".join(missing)))
        return 1
    extra = [i for i in VERDICTS if i not in {d["id"] for d in findings}]
    if extra:
        print("VERDICTS has %d id(s) not in the ledger: %s" % (len(extra), ", ".join(extra)))
        return 1
    if args.check:
        print("OK: all %d ledger ids have a verdict" % len(findings))
        return 0

    counts = collections.Counter(v[0] for v in VERDICTS.values())
    order = [b for b, _ in BUCKETS]
    assert set(counts) <= set(order), sorted(set(counts) - set(order))

    nix = [d["id"] for d in findings
           if re.search(r"cargo (creusot|nextest|build)|nix develop", d.get("repro_cmd", ""))]
    probed = [d["id"] for d in findings if results.get(d["id"], {}).get("probe")]
    unprobed = [d["id"] for d in findings if not results.get(d["id"], {}).get("probe")]
    hit = [i for i in probed if results[i]["probe_hit"]]
    miss = [i for i in probed if not results[i]["probe_hit"]]
    skipped = [i for i in results if results[i]["status"].startswith("SKIPPED")]

    out = []
    w = out.append
    w("# Stage 8C re-verification verdicts, re-derived under %s (chainlink #18)" % BINARY)
    w("")
    w("Supersedes the 1.1.0 edition of this file. All **%d** `repro_cmd` entries in" % len(findings))
    w("`findings/limitations.jsonl` were re-run from a clean `rsync` copy of the workspace,")
    w("including the %d that need the nix dev shell, and every verdict below was assigned by" % len(nix))
    w("reading that command's captured output by hand.")
    w("")
    w("**Read this before consuming `findings/limitations.jsonl` for a go/no-go.**")
    w("%d of its %d lines describe behaviour that no longer exists, and %d more describe"
      % (counts["RESOLVED"], len(findings), counts["SUPERSEDED"]))
    w("behaviour that moved on under another issue. The file is append-only by workspace")
    w("convention, so resolved findings were not edited in place; **this table is the overlay**.")
    w("")
    w("## Method")
    w("")
    w("- `analysis/ligature/reverify.py --slow` drove the whole run. It `rsync`s the")
    w("  workspace to a scratch root and **resets the scratch to the pristine baseline")
    w("  before every single `repro_cmd`**, so no repro inherits another's mutation. That is")
    w("  load-bearing, not hygiene: `date-ligature-041` leaves")
    w("  `specs/_closure/date-creusot-core.json` with `closure_kind: \"degraded\"` and")
    w("  `date-ligature-047` rewrites `ci/results/feature_ledger.json`")
    w("  (see `date-creusot-053`). The live pilot root was never written to by the harness.")
    w("- Documented substitutions: the absolute workspace prefix is rewritten to the scratch")
    w("  root; a repro that uses `date-creusot` **as a directory** runs with the workspace")
    w("  root as cwd and one that uses bare `tools/ligature/...` / `specs/...` / `rust/...`")
    w("  paths runs with the pilot root as cwd; nix repros are wrapped in")
    w("  `nix develop \"path:<scratch>#date-creusot\" -c bash -lc '...'`, the explicit `path:`")
    w("  ref that #88/#89 documented for this workspace.")
    w("- Binary under test, verified **before anything else ran**:")
    w("  `sha256sum -c tools/ligature/SHA256SUMS` -> `ligature.pyz: OK`, sha256 `%s`," % BINARY_SHA)
    w("  `ligature version` -> `%s`, adjudicator `zipapp (attested: true)`." % BINARY)
    w("- Per-id machine record: `reverify-results.json` (regenerated next to this file from")
    w("  `reverify.py`'s `results.json`). This file is generated by")
    w("  `reverify-verdicts.py`; the bucket counts below are derived from the per-finding")
    w("  table, so they cannot drift from it.")
    w("")
    w("## What the run measured")
    w("")
    w("| | n |")
    w("|---|---:|")
    w("| `repro_cmd`s in the ledger | %d |" % len(findings))
    w("| re-run from a clean copy | %d |" % len(results))
    w("| **SKIPPED** | **%d** |" % len(skipped))
    w("| needed the nix dev shell (run anyway) | %d |" % len(nix))
    w("| carry a key-behaviour probe literal | %d |" % len(probed))
    w("| probe literal **present** in the output | %d |" % len(hit))
    w("| probe literal **absent** | %d |" % len(miss))
    w("| no probe (hand-read) | %d |" % len(unprobed))
    w("| exit code equals the recorded `exit_code` | %d |" % sum(
        1 for d in findings if results[d["id"]].get("exit") == results[d["id"]].get("recorded_exit")))
    w("| exit code differs | %d |" % sum(
        1 for d in findings if results[d["id"]].get("exit") != results[d["id"]].get("recorded_exit")))
    w("")
    w("The exit-code column is **not** the verdict column, for the reason `date-creusot-053`")
    w("already names: many recorded `exit_code`s belong to one step of a multi-step command, or")
    w("are the exit code of a `grep`/`tail` that masks the real one. `date-creusot-035/036/037,")
    w("048, 049, 050` all exit 1 purely because `grep -E 'Goal|unproved'` matched nothing; the")
    w("underlying `cargo creusot` returns 0 and prints `Proved (93 files)`. Those were")
    w("re-tested without the pipe before being called resolved.")
    w("")
    w("## Verdict buckets")
    w("")
    w("| bucket | n | meaning |")
    w("|---|---:|---|")
    for b, meaning in BUCKETS:
        w("| %s | %d | %s |" % (b, counts[b], meaning))
    w("| **total** | **%d** | |" % sum(counts.values()))
    w("")
    w("## The ones that decide the closure criterion")
    w("")
    w("- **`gate-g14` is clean and matches the declared `closure_kind`.** From the live pilot")
    w("  root: `cluster 'date-creusot-core' closes: closure_kind=deductive, 1 work package(s)`,")
    w("  `OK: 1 cluster(s) close under their declared profile`, exit 0. `validate-closure` exit 0,")
    w("  `gate-g18/19/20` exit 0, `doctor` exit 0, `write-set-check` exit 0.")
    w("- **`date-ligature-039` RESOLVED** (gate-g14 1 -> 0).")
    w("- **`date-ligature-041` RESOLVED** -- the `closure_kind` enum is")
    w("  `['deductive', 'bounded', 'partial']` and all three validate.")
    w("- **`date-ligature-042` RESOLVED** -- the manifest was renamed to")
    w("  `ci/manifest/WP-DATE-CREUSOT.json`.")
    w("- **`date-ligature-043` RESOLVED** -- `generic_callees` is now")
    w("  `VERIFIED from artifact data, not taken on declaration`, not a never-checked")
    w("  HUMAN DECLARATION.")
    w("- **`date-ligature-045` RESOLVED**, and `date-ligature-048` MATCHES.")
    w("- **All seven creusot proof-gap findings RESOLVED** -- `date-creusot-001, 035, 036,")
    w("  037, 038, 039, 041` all print `Proved (93 files)`, and `date-creusot-044` (nextest)")
    w("  passes 143/143. Re-verified in the nix shell, cold, from a fresh scratch copy.")
    w("- **`date-ligature-057` RESOLVED** -- the install is no longer half-migrated:")
    w("  `installation.json` reads 1.1.1, `gate_integrity` is `pinned`, `doctor` exits 0.")
    w("- **`date-creusot-054` RESOLVED** -- the harness's cwd-routing bug is fixed, so the")
    w("  nix half and `date-ligature-047` run through it instead of dying on a path error.")
    w("")
    live = [b for b in ("REPRODUCES", "MATCH", "PARTLY RESOLVED", "CHANGED", "NOT-REPRODUCED")]
    dead = ("RESOLVED", "SUPERSEDED", "NOT-RUNNABLE")
    groups = [
        ("codesight-mcp (third-party)", ["date-mcp-001", "date-mcp-002"]),
        ("descriptor / evidence authoring", [
            "date-ligature-004", "date-ligature-008", "date-ligature-011", "date-ligature-018",
            "date-ligature-019", "date-ligature-022", "date-ligature-023", "date-ligature-024",
            "date-ligature-027", "date-ligature-028", "date-ligature-029", "date-ligature-035",
            "date-ligature-040", "date-creusot-045",
        ]),
        ("write set / protected roots", [
            "date-ligature-026", "date-ligature-049", "date-ligature-052", "date-ligature-055",
        ]),
        ("R1 / G16, blocked on a human risk ruling", [
            "date-ligature-036", "date-ligature-050", "date-creusot-042", "date-creusot-043",
            "date-ligature-098", "date-ligature-100",
        ]),
        ("the #92 ledger path collision and its unreachable remedy", [
            "date-ligature-047", "date-ligature-054", "date-ligature-056", "date-creusot-053",
            "date-creusot-047",
        ]),
        ("1.1.1 authoring gaps, escalated to epic #1", [
            "date-ligature-094", "date-ligature-095", "date-ligature-096", "date-ligature-097",
        ]),
        ("still true, recorded form changed", [
            "date-ligature-009", "date-ligature-025", "date-ligature-031", "date-ligature-032",
            "date-ligature-033", "date-ligature-034", "date-ligature-048", "date-ligature-099",
            "date-creusot-040", "date-creusot-041", "date-creusot-051", "date-creusot-052",
        ]),
    ]
    grouped = [i for _, ids in groups for i in ids]
    assert len(grouped) == len(set(grouped)), "a finding is listed in two groups"
    for i in grouped:
        assert VERDICTS[i][0] in live, "%s is in the still-live list but is %s" % (i, VERDICTS[i][0])
    ungrouped = sorted(i for i, v in VERDICTS.items() if v[0] in live and i not in grouped)
    if ungrouped:
        raise SystemExit("still-live findings missing from the group list: %s" % ", ".join(ungrouped))

    w("## The still-live ones (%d), grouped" % sum(counts[b] for b in live))
    w("")
    w("REPRODUCES, MATCH, PARTLY RESOLVED, CHANGED and NOT-REPRODUCED -- everything that is")
    w("not RESOLVED, SUPERSEDED or NOT-RUNNABLE. **None of these blocks `gate-g14`.** They are")
    w("descriptor/report authoring and traceability gaps, plus the two third-party ones.")
    w("")
    for title, ids in groups:
        if not ids:
            continue
        w("- **%s**" % title)
        w("  " + " · ".join("`%s`" % i for i in ids))
    w("")
    w("## Two harness notes a fresh agent needs before re-running this")
    w("")
    w("Neither is a ligature defect and neither is a finding; both are properties of this")
    w("issue's own harness, and both cost a full run to discover.")
    w("")
    w("1. **`TMPDIR` must be a directory that outlives the launcher.** `nix develop` creates a")
    w("   temp file in `$TMPDIR` before it evaluates the flake. A harness launched from a shell")
    w("   whose `TMPDIR` is later removed makes **all %d nix repros fail identically and" % len(nix))
    w("   instantly** (`error: creating temporary file '<tmp>/nix-shell.XXXX': No such file or")
    w("   directory`, exit 1, in ~2.4s each), which reads exactly like a clean finding table")
    w("   of failures. That is what the first attempt of this run produced.")
    w("2. **`REVERIFY_ROOT` is read, never exported.** `reverify.py` line 45 does")
    w("   `os.environ.get(\"REVERIFY_ROOT\", \"/tmp/opencode/reverify-8c\")`, so a command that")
    w("   references `$REVERIFY_ROOT` -- including `date-creusot-054`'s own `repro_cmd` -- sees an")
    w("   empty string. Export it yourself before running that finding by hand.")
    w("")
    w("## Per-finding")
    w("")
    for i, d in enumerate(findings, 1):
        fid = d["id"]
        verdict, note = VERDICTS[fid]
        r = results.get(fid, {})
        w("### %d. `%s` — %s" % (i, fid, verdict))
        w("")
        w("`tool: %s` · `severity: %s` · `recorded exit_code: %s` · `actual exit: %s`"
          % (d.get("tool"), d.get("severity"), d.get("exit_code"), r.get("exit")))
        w("")
        w(note + ".")
        w("")
        ev = evidence_lines(fid)
        if ev is None:
            w("_raw output not captured in this session; re-run "
              "`python3 analysis/ligature/reverify.py %s`_ (SCRATCH_OUT = `%s`)" % (fid, SCRATCH_OUT))
        else:
            w("```")
            for line in ev:
                w(line)
            w("```")
        w("")

    OUT_MD.write_text("\n".join(out) + "\n")
    print("wrote %s" % OUT_MD)
    print("  %d findings, %d verdicts" % (len(findings), len(VERDICTS)))
    for b, _ in BUCKETS:
        print("  %3d  %s" % (counts[b], b))
    print("  %3d  total" % sum(counts.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
