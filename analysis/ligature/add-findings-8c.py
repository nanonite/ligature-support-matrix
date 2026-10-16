#!/usr/bin/env python3
"""Append the chainlink #18 (Stage 8C) findings to date-creusot/findings/limitations.jsonl.

Same convention as add-findings.py (that script's docstring): kept as a script
so this issue's entries are diffable against the ones before them, and a re-run
is idempotent (entries whose id already exists are skipped).

The file is append-only. Nothing here rewrites or reorders an existing line.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "findings" / "limitations.jsonl"
PYZ = str(ROOT / "tools" / "ligature" / "ligature.pyz")
SHA = "ede2514e9070a628b30fe3a0a3ead9e81574ac041f692b7c498a7fb88bd0883f"
VER = ("ligature 1.1.0; content hash "
       "sha256:29958eae2961d585dc19770b537a773c083d94315315113582df5d8f7ab8dc14")

# The four Stage 8C report commands, in the order this issue ran them.
# NOTE: the repro_cmd ends on the gate-g14 invocation, with no trailing `;` or
# `echo`, so the command's own exit code IS gate-g14's exit code. An earlier
# draft of this line ended `... ; echo "gate-g14 exit=$?"`, which makes the
# overall exit 0 while recording exit_code 1 -- the exact
# "the recorded exit_code refers to a specific step, not the overall command"
# defect this issue logs in date-creusot-053.
ORD = ("cd date-creusot && md5sum ci/results/feature_ledger.json && python3 "
       "tools/ligature/ligature.pyz report feature-ledger && md5sum "
       "ci/results/feature_ledger.json && python3 tools/ligature/ligature.pyz gate-g14")

NEW = [
    dict(
        id="date-ligature-051",
        pilot="date-creusot",
        stage="stage-8C-closure-gates",
        command="python3 tools/ligature/ligature.pyz report feature-ledger ; python3 tools/ligature/ligature.pyz gate-g14",
        tool="ligature",
        chain="new",
        symptom=(
            "Two Stage 8C commands write the same canonical path with incompatible schemas, so "
            "running the pipeline in its documented order silently destroys the evidence the "
            "closure gate reads. `report feature-ledger` writes a projection {features: [], "
            "generated_from: {...}, schema_version} to ci/results/feature_ledger.json; "
            "`record-assurance` writes an assurance report {obligation_records: [...5...], "
            "work_package: WP-DATE-CREUSOT, schema_version} to the SAME path, because the "
            "work-package manifest's report.emit names it. gate-g14 reads that path. On a tree "
            "where record-assurance has just populated it, gate-g14 exits 0 with 'OK: 1 "
            "cluster(s) close under their declared profile'; after a single "
            "`report feature-ledger` the identical tree gives gate-g14 exit 1 with six new "
            "errors: 'assurance report ci/results/feature_ledger.json is not schema-valid: "
            "'work_package' is a required property', one 'recorded no achieved assurance' error "
            "per manifest obligation (Weekday.C1/C2/C3, YearMonthDay.C2, YearMonthDayLast.C1), "
            "and generic_callees flipping from 'VERIFIED from artifact data' to 'cannot verify "
            "it: no achieved assurance record at all for WP-DATE-CREUSOT'. This issue hit it for "
            "real: running the four Stage 8C report commands before the gates broke gate-g14 in "
            "the live pilot root, and only `record-assurance` re-run restored it (byte-identical, "
            "md5 463583d9eda1ed0292800703bf2835cf). The trap is silent in the failure direction: "
            "`report feature-ledger` still prints 'wrote ci/results/feature_ledger.json' and "
            "exits 0. `record-assurance` is the only one that warns, and its warning is easy to "
            "miss because it names the collision without making it an error."),
        repro_cmd=ORD,
        exit_code=1,
        expected=(
            "The generated feature-ledger projection and the work package's assurance report are "
            "distinct artifacts at distinct paths, so regenerating one cannot invalidate the "
            "other; or `report feature-ledger` refuses to overwrite a path that holds an "
            "assurance report (or vice versa) instead of doing it silently at exit 0."),
        actual=(
            "`report feature-ledger` overwrites the assurance report at exit 0 with no warning, "
            "and gate-g14 then reports the whole cluster BLOCKED on 6 errors that were not true "
            "one command earlier. Confirmed on a clean rsync copy of this pilot: md5 "
            "463583d9eda1ed0292800703bf2835cf -> c8571e0944ad0eaefb60adf3a194bbea, gate-g14 0 -> 1, "
            "and the reverse is exactly recoverable by re-running record-assurance. Not a "
            "correctness bug in gate-g14 -- it is right to reject a schema-invalid report -- but "
            "an unrecoverable-by-default ordering trap in the Stage 8C command set. Extends "
            "date-ligature-047, which recorded the same collision from the record-assurance side "
            "and is now only half a picture: v1.1 DID fix the record-loss half ('preserved 4 "
            "existing obligation record(s) this run did not record') but the path collision "
            "itself is unchanged."),
        workaround=(
            "Run `report feature-ledger` BEFORE `record-assurance`, never after, and if gate-g14 "
            "reports 'is not schema-valid: work_package is a required property' or 'recorded no "
            "achieved assurance', re-run record-assurance with all five --proof flags before "
            "concluding anything about the closure. The full five-flag command is in this "
            "pilot's README under 'Current closure state'. The proper fix (pointing "
            "manifest.report.emit at a separate path) is not reachable by a worker -- see "
            "date-ligature-052."),
        severity="friction",
        revisit_trigger=(
            "Every issue that runs the Stage 8C report set: #18 here, and the P2/P3 equivalents. "
            "Also re-run on any ligature release; and it should be quoted in the Stage 8C runbook "
            "for P2 and P3 so neither pilot loses an hour to it."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-052",
        pilot="date-creusot",
        stage="stage-8C-closure-gates",
        command="python3 tools/ligature/ligature.pyz record-assurance WP-DATE-CREUSOT --proof Weekday.C1=<path>",
        tool="ligature",
        chain="new",
        symptom=(
            "The remedy `record-assurance` prints for the date-ligature-051 collision is "
            "forbidden by the same binary's own authority boundary. The warning says: 'point the "
            "manifest's report.emit at a free ci/results/*.json path (e.g. "
            "ci/results/<work-package>.json) to separate the two artifacts'. report.emit lives in "
            "ci/manifest/WP-DATE-CREUSOT.json, and this descriptor lists 'ci/manifest/**' in "
            "write_set.protected_roots, described in the hash-pinned SKILL.md authority boundary 5 "
            "as 'never write into protected_roots' with protected_roots glossed as 'specs, CI "
            "manifests, gate scripts, schemas, policy docs'. So the one fix the tool recommends "
            "is a write the tool's own rules prohibit an agent from making, and the pilot cannot "
            "separate the two artifacts at all. It is worse than merely unreachable: the same "
            "boundary is not enforced, because `write-set-check` reports state=clean for a file "
            "dropped into ci/manifest/ (date-ligature-049, escalated as epic #1 #90) -- its own "
            "details string says a file is 'accounted for by allowed_roots, protected_roots, the "
            "ownership manifest, a declared crate's specs/ tree, or a canonical pipeline "
            "location', i.e. protected roots ACCOUNT for a file rather than VIOLATE it. So the "
            "rule that blocks the fix is the same rule that cannot be broken, and neither half "
            "helps."),
        repro_cmd=("cd date-creusot && jq -r '.report.emit' ci/manifest/WP-DATE-CREUSOT.json && "
                   "jq -c '.write_set.protected_roots' project-descriptor.json | tr ',' '\\n' | "
                   "grep -n 'ci/manifest' && sed -n '69,77p' .codex/skills/ligature/SKILL.md && "
                   "printf '{}' > ci/manifest/PROBE.json && python3 tools/ligature/ligature.pyz "
                   "write-set-check | head -1; echo \"exit=$?\"; rm -f ci/manifest/PROBE.json"),
        exit_code=0,
        expected=(
            "A tool that diagnoses a path collision names a remedy the acting agent is permitted "
            "to take -- either report.emit is a worker-writable location, or the boundary is "
            "relaxed for it, or the tool separates the paths itself by default."),
        actual=(
            "The remedy is to edit a file in write_set.protected_roots, which the same "
            "installation's hash-pinned authority boundary 5 forbids. The whole pilot therefore "
            "runs on a permanently unsatisfiable configuration, kept working only by remembering "
            "an undocumented command order. And the boundary that forbids the fix is itself "
            "unverifiable (date-ligature-049), so this is not 'a rule we chose and must live "
            "with' -- it is a rule we cannot enforce and cannot obey here."),
        workaround=(
            "Nothing. This one is not worked around: it is reported. Operationally the pilot uses "
            "the ordering workaround from date-ligature-051 and keeps the single shared path, "
            "with ci/results/feature_ledger.json regenerated by record-assurance as the canonical "
            "state. The feature-ledger projection is treated as disposable output with no "
            "gate-reading role."),
        severity="scope-cut",
        revisit_trigger=(
            "Any human with descriptor or manifest authority, and the epic #1 #90 review, since "
            "both defects are the same enforcement hole seen from two sides. Also revisit if "
            "report.emit ever becomes configurable outside ci/manifest/."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-053",
        pilot="date-creusot",
        stage="stage-8C-closure-gates",
        command="python3 analysis/ligature/reverify.py",
        tool="ligature",
        chain="new",
        symptom=(
            "The Stage 8C re-verification of every findings/limitations.jsonl repro_cmd, run from "
            "a clean rsync copy of the workspace with the working copy reset to the baseline "
            "before each of the 70 commands so no repro inherits another's mutation. Supersedes "
            "date-ligature-044, whose repro_cmd pointed at a session-local script under /tmp that "
            "no longer exists and so is not re-runnable by a fresh agent; the harness now lives "
            "in the pilot. Verdict counts over all 70 findings: 32 RESOLVED (no longer reproduce "
            "-- almost all of them v1.0 descriptor/integrity defects fixed by the v1.1.0 upgrade "
            "and recorded as date-ligature-046, or proof gaps closed by #87/#88/#89), 22 STILL "
            "REPRODUCE, 7 MATCH (reproduce as recorded), 3 PARTLY RESOLVED, 2 SUPERSEDED (the "
            "state they described moved on, under another issue), 1 CHANGED, 3 NOT RUNNABLE / "
            "NOT REPRODUCED. Per-finding verdicts with the exact evidence line for each are in "
            "analysis/ligature/reverify-VERDICTS.md; the harness and its per-finding output are "
            "re-runnable. Nine of the 32 resolutions are closure-relevant: date-ligature-039 "
            "(gate-g14 exit 1) is now exit 0 with 'OK: 1 cluster(s) close under their declared "
            "profile'; 041 (closure_kind enum has no partial) is resolved, the enum is now "
            "['deductive', 'bounded', 'partial']; 043 (generic_callees is a never-checked HUMAN "
            "DECLARATION) is resolved, it is now 'VERIFIED from artifact data, not taken on "
            "declaration'; 045, 042, 040(partial) likewise; and all seven creusot proof-gap "
            "findings (date-creusot-001, 035, 036, 037, 038, 039, 041) are gone -- "
            "`cargo creusot` prints 'Proved (93 files)' for every variant tried."),
        # NOTE: this repro deliberately does NOT invoke analysis/ligature/reverify.py.
        # That would be self-referential -- the harness re-running its own repro_cmd
        # would re-rsync the workspace inside the harness that is already mid-run.
        # It reads the verdict table instead, which is the thing this finding is about.
        repro_cmd=("cd date-creusot && wc -l findings/limitations.jsonl && "
                   "grep -c '^### `' analysis/ligature/reverify-VERDICTS.md && "
                   "grep -A9 '^| bucket' analysis/ligature/reverify-VERDICTS.md | tail -7"),
        exit_code=0,
        expected=(
            "Every repro_cmd in the findings file runs as written from a clean copy and "
            "reproduces its recorded exit code and key behaviour, so a fresh agent can re-verify "
            "the whole record without the original session's /tmp state."),
        actual=(
            "70/70 were re-run; 51 reproduce in some form, 3 do not run as written (see "
            "date-creusot-053), and 2 describe a state that a later issue moved on from "
            "(date-ligature-036, date-ligature-038 -- both are about gate-r1-g16, whose exit code "
            "changed under #89). The single most important re-verification result for the "
            "pipeline: every v1.0 blocker-severity ligature finding from Stage 0-3 that was "
            "escalated to epic #1 is either fixed in v1.1.0 or explicitly still open, and the "
            "findings file does not currently distinguish the two."),
        workaround=(
            "The findings file is append-only by workspace convention, so resolved findings are "
            "not edited in place; the verdict table is the machine-readable overlay. Anyone "
            "consuming findings/limitations.jsonl for a go/no-go must read "
            "analysis/ligature/reverify-VERDICTS.md first -- 32 of the 70 lines describe v1.0.0 "
            "behaviour that no longer exists."),
        severity="friction",
        revisit_trigger=(
            "Any later re-verification issue, and every consumer of the findings file that needs "
            "the CURRENT state rather than the recorded one. Re-run before the chainlink #55-#66 "
            "cross-cutting re-checks, which will otherwise re-encounter 22 already-known live "
            "defects and possibly re-file them."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-creusot-053",
        pilot="date-creusot",
        stage="stage-8C-closure-gates",
        command="python3 -c \"import json;[print(json.loads(l)['id'], repr(json.loads(l)['repro_cmd'])[:90]) for l in open('findings/limitations.jsonl') if l.strip()]\"",
        tool="ligature",
        chain="new",
        symptom=(
            "The findings file is only as good as its repro_cmds, and five of this pilot's 70 "
            "are not runnable as written -- and two of those would CORRUPT the live pilot if run "
            "there, which is the whole point of a re-verification. (1) date-ligature-041 loops "
            "`for k in deductive bounded mixed partial degraded` rewriting "
            "specs/_closure/date-creusot-core.json in place with `open(p,'w')` and never restores "
            "it: run against date-creusot/ it leaves closure_kind: 'degraded' and the cluster "
            "profile invalid. (2) date-ligature-047 runs `record-assurance ... --proof "
            "Weekday.C1=<one path>` against ci/results/feature_ledger.json; on v1.0.0 that wiped "
            "the other four obligation records, and even on v1.1.0 (which now preserves them) it "
            "rewrites a protected pipeline artifact. (3) date-ligature-024's repro has a python "
            "bug -- `json.dump(d,indent=2)` instead of `json.dumps`, which truncates the "
            "descriptor to zero bytes, so the three ligature calls that follow all fail on "
            "'project descriptor ... is not valid JSON: Expecting value: line 1 column 1' and the "
            "finding is untested by its own command. (4) date-ligature-037's repro contains the "
            "literal placeholder `<path-to-a-hand-authored-.json-with-no-.draft-sibling>`, and "
            "date-ligature-046's contains literal `...` for all five --proof paths. (5) "
            "date-ligature-032/033/034 name `ci/manifest/work-package.json`, which was renamed to "
            "WP-DATE-CREUSOT.json in #64, so those three now fail with 'error: manifest not "
            "found'. All five were worked around here by running every repro against a throwaway "
            "rsync copy, which is the only safe way to re-verify this file as it stands."),
        # Single-line python (no embedded newlines) so the command survives JSON
        # escaping unchanged. An earlier draft of this repro used \n inside a
        # `python3 -c` string and died with "unexpected character after line
        # continuation character" -- the very class of defect this finding is
        # about, found by running it.
        repro_cmd=("cd date-creusot && python3 -c \"import json;rs=[json.loads(l) for l "
                   "in open('findings/limitations.jsonl') if l.strip()];print('total',len(rs));"
                   "[print(d['id'],'->',b) for d in rs if d['id']!='date-creusot-053' for b in "
                   "('...','<path-to-','work-package.json') if b in d['repro_cmd']];"
                   "print('--- the two that would "
                   "corrupt the live tree ---');[print(d['id'],d['repro_cmd'][:120]) for d in rs "
                   "if d['id'] in ('date-ligature-041','date-ligature-047')]\""),
        exit_code=0,
        expected=(
            "Every repro_cmd in the findings file is copy-paste-runnable against a clean copy of "
            "the pilot without hand-editing, and none of them mutates a tracked artifact in "
            "place -- findings-schema.md promises 'repro_cmd' as a first-class field and this "
            "issue's acceptance criterion is literally that a fresh agent re-runs every one of "
            "them."),
        actual=(
            "5 of 70 are unrunnable as written (2 literal placeholders, 1 broken python call, 3 "
            "stale paths) and 2 more mutate tracked pipeline artifacts in place without "
            "restoring them. The only safe procedure is the one used here: copy the whole "
            "workspace, reset the copy to a baseline before every single command, and rewrite the "
            "absolute path prefix. That is a harness of ~80 lines and it is now kept at "
            "analysis/ligature/reverify.py, but it did not exist when it was needed and the "
            "findings-schema.md gives no warning that some entries require it."),
        workaround=(
            "analysis/ligature/reverify.py copies the workspace to a scratch root, restores the "
            "baseline before every repro, and rewrites the absolute path prefix. Its per-finding "
            "output is written to a scratch out/ directory; nothing in the live pilot is touched. "
            "The five broken repro_cmds are NOT rewritten in place, because the findings file is "
            "append-only; the corrected forms are in analysis/ligature/reverify-VERDICTS.md and "
            "should be folded in whenever the file is next allowed to be edited."),
        severity="friction",
        revisit_trigger=(
            "Any future re-verification of this pilot, and the schema question belongs to whoever "
            "owns findings-schema.md: either it should say a repro_cmd may need a scratch copy, "
            "or a repro that mutates a tracked artifact should be required to restore it. Also "
            "revisit at the chainlink #67 deliverables roll-up, which will read all three pilots' "
            "findings files and will hit the same five dead commands."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
]


def main() -> int:
    text = LEDGER.read_text() if LEDGER.exists() else ""
    existing = {json.loads(l)["id"] for l in text.splitlines() if l.strip()}
    before = len(text.splitlines())
    added = [e for e in NEW if e["id"] not in existing]
    with LEDGER.open("a") as fh:
        for e in added:
            fh.write(json.dumps(e, sort_keys=False) + "\n")
    after = len(LEDGER.read_text().splitlines())
    print(f"ledger: {before} lines before, {len(added)} added, {after} total")
    for e in added:
        print("  +", e["id"], e["severity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
