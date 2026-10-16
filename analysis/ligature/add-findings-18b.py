#!/usr/bin/env python3
"""Append this session's findings to date-creusot/findings/limitations.jsonl.

Append-only by workspace convention: the file is re-read immediately before the
write and the write is a single `>>` append, so a concurrent agent's lines are
never rewritten (only clobbered if both of us append in the same microsecond,
which the exclusive lock below makes impossible).

Run from anywhere:  python3 analysis/ligature/add-findings-18b.py
"""
import fcntl
import json
import os
import pathlib

PILOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = PILOT / "findings" / "limitations.jsonl"
LOCK = PILOT / "analysis" / "ligature" / ".limitations.lock"

PYZ = "9c921eeb1bbb858c0041e49f07cf5d06988eb798ba60b9207f7576cba430637c"

NEW = [
 {
  "id": "date-ligature-101",
  "pilot": "date-creusot",
  "stage": "stage-3-draft-approve",
  "command": "python3 tools/ligature/ligature.pyz approve <target> --reviewer <human> --reviewed-at <date>",
  "tool": "ligature",
  "chain": "new",
  "symptom": (
   "All three review checkpoints answer 'the target has no staged .draft' with an "
   "UNHANDLED FileNotFoundError traceback instead of a diagnostic. `approve` reads "
   "<target>.json.draft unconditionally, so the failure fires not only when the draft "
   "is missing but for the two mistakes a human is most likely to make: naming an "
   "already-promoted artifact (re-approving it) and naming a path that does not exist "
   "at all. exit 1, no message on stdout, ~15 frames of Python on stderr, and the "
   "user-visible text is a bare path to a file they were never asked about. "
   "approve-pair and approve-exemption-pair do the same on their first (interaction) "
   "target. The identical condition in a sibling verb is already handled: "
   "`promote-evidence evidence/E-99.json` prints 'error: no staged draft at "
   "evidence/E-99.json.draft -- run `pipeline.py draft 0 evidence-intake "
   "evidence/E-99.json` first' and exits 1. So the fix is a one-line guard that the "
   "release already writes elsewhere. Reproduced 5/5 across boundaries, interactions "
   "and a nonexistent path, on ligature 1.1.1 (3edfd03c) AND on 1.2.0 (9c921eeb), so "
   "it is not a regression of the recent releases -- it is old. This is the residue of "
   "date-ligature-025, whose own repro hit this exact traceback and was recorded under "
   "the wrong shape ('approve exits 3, a state dependency') because that was the "
   "1.0.0-era behaviour."
  ),
  "repro_cmd": (
   "cd \"$([ -d date-creusot ] && echo date-creusot || echo .)\" && rsync -a --delete "
   "--exclude upstream/ --exclude .git . /tmp/dc-approve-crash/ && cd /tmp/dc-approve-crash "
   "&& for t in rust/date-creusot-core/specs/_interactions/I-year-month-day-to-days-to-year-month-day-from-days.json "
   "rust/date-creusot-core/specs/_boundaries/year_month_day_to_days__to__year_month_day_from_days.json "
   "rust/date-creusot-core/specs/_boundaries/does-not-exist.json; do "
   "python3 tools/ligature/ligature.pyz approve $t --reviewer chainlink-reviewer "
   "--reviewed-at 2026-10-01 2>&1 | tail -1; echo \"  approve $t -> exit=${PIPESTATUS[0]}\"; done; "
   "python3 tools/ligature/ligature.pyz approve-pair "
   "rust/date-creusot-core/specs/_interactions/I-probe.json "
   "rust/date-creusot-core/specs/_protocol_debt/D-probe.json --reviewer x --reviewed-at 2026-10-01 "
   "2>&1 | tail -1; echo \"  approve-pair -> exit=${PIPESTATUS[0]}\"; "
   "python3 tools/ligature/ligature.pyz promote-evidence evidence/E-99.json"
   "   # CONTROL, and the last command, so it IS the exit code (1): the identical "
   "missing-draft condition in a sibling verb exits 1 WITH a message -- "
   "'error: no staged draft at evidence/E-99.json.draft -- run <draft cmd> first'. "
   "The four approve invocations above print a FileNotFoundError traceback instead."
  ),
  "exit_code": 1,
  "expected": (
   "each verb answers a missing or nonsensical target with one line naming the artifact, "
   "the reason and the command that would fix it -- the shape promote-evidence already "
   "uses, and the shape every other verb in this release uses (validate-work-package: "
   "'error: manifest not found: ...'; accept-promotion: 'error: refusing to mint a "
   "promotion receipt: ...'; gate-g14: 'a declared depends_on names X, which resolves to "
   "no schema-valid work-package manifest')"
  ),
  "actual": (
   "an unhandled FileNotFoundError traceback for all three approve verbs. Tail of the "
   "traceback, verbatim: 'File \"/usr/lib/python3.12/pathlib.py\", line 182, in approve / "
   "File \"/usr/lib/python3.12/pathlib.py\", line 1029, in read_text / ... / "
   "FileNotFoundError: [Errno 2] No such file or directory: "
   "'rust/date-creusot-core/specs/_interactions/I-year-month-day-to-days-to-year-month-day-from-days.json.draft'. "
   "The control `promote-evidence` on the same tree, same release, same missing-draft "
   "condition, exits 1 with a proper diagnostic. Deterministic 5/5. Reachable from a "
   "typo, from re-running a command whose draft was already approved, and from any "
   "pipeline that would call approve in a loop until it succeeds -- i.e. an agent "
   "following 'keep retrying on failure' guidance gets a stack trace instead of a "
   "reason it can act on."
  ),
  "workaround": (
   "check for the .draft sibling before calling any approve verb, and treat exit 1 "
   "with a non-zero stderr line count as 'target not staged' rather than as a crash. "
   "Do not retry blindly."
  ),
  "severity": "blocker",
  "revisit_trigger": (
   "next ligature release; if approve/approve-pair/approve-exemption-pair still reach "
   "Path.read_text() before any existence check, keep this open"
  ),
  "pyz_sha256": PYZ,
  "tool_path": "date-creusot/tools/ligature/ligature.pyz",
  "tool_version": "1.2.0"
 },
 {
  "id": "date-ligature-102",
  "pilot": "date-creusot",
  "stage": "stage-8c-reverification",
  "command": "python3 analysis/ligature/reverify.py --slow",
  "tool": "ligature",
  "chain": "new",
  "symptom": (
   "RESOLVES date-creusot-054 (the harness's cwd-routing defect), and fixes a second, "
   "undocumented one in the same pass. (1) cwd: the routing test was the bare substring "
   "'date-creusot' in repro_cmd, which also matches the crate name 'date-creusot-core' "
   "and the nix flake ref '...#date-creusot'. Five repros were therefore run from the "
   "WORKSPACE root, where rust/, tools/ligature/ and ci/ do not exist: date-ligature-047 "
   "died with \"can't open file <scratch>/ws/tools/ligature/ligature.pyz\" and the four "
   "nix repros date-creusot-038/039/047/051 died with 'cd: rust/date-creusot-core: No "
   "such file or directory'. Both look like a broken finding; neither is. The test is "
   "now 'is date-creusot used as a DIRECTORY' -- followed by / or by a shell delimiter "
   "-- applied after neutralising the flake ref and any trailing '#' comment. "
   "(2) baseline content: make_baseline() excluded analysis/codesight/index/, so both "
   "tool:mcp repros (date-mcp-001/002) failed with 'Repository not indexed' -- a "
   "harness artefact that would have been recorded as a codesight regression. The index "
   "is 1.6M; it is now copied. Verified: routing is 70 workspace-root / 16 pilot-root "
   "across the 92 findings, date-ligature-047 runs to completion, and date-mcp-001 now "
   "reproduces ('Symbol not found: include/date/date.h::days_from_civil#function'). "
   "The defect was recorded but deliberately not fixed in the previous session, on the "
   "reason that fixing cwd routing would re-run and re-label the whole hand-assigned "
   "table. That was right when the table was a convenience and wrong now: under 1.2.0 "
   "the table had to be rebuilt anyway, and the harness was failing the half of the "
   "task this issue exists to satisfy."
  ),
  "repro_cmd": (
   "cd \"$([ -d date-creusot ] && echo date-creusot || echo .)\" && "
   "grep -n 'date-creusot(?=' analysis/ligature/reverify.py; "
   "grep -n 'analysis/codesight/index' analysis/ligature/reverify.py; "
   "echo '  ^ first grep = the fixed cwd regex (found); second grep = the codesight baseline exclusion (must be ABSENT)'; "
   "REVERIFY_ROOT=/tmp/opencode/rv-cwd-regression python3 analysis/ligature/reverify.py date-ligature-047 2>&1 | tail -3 "
   "# the regression: date-ligature-047 used to exit 2 with \"can't open file <scratch>/ws/tools/ligature/ligature.pyz\"; "
   "# it now prints 'recorded assurance: ci/results/feature_ledger.json (work package WP-DATE-CREUSOT)'"
  ),
  "exit_code": 0,
  "expected": (
   "a re-verification harness reports SKIPPED only for findings it was not asked to run, "
   "and every finding it does run is either executed or explicitly marked; a harness that "
   "cannot execute a repro must say so rather than emitting a plausible-looking failure"
  ),
  "actual": (
   "92/92 findings executed, 0 skipped. 15 of the 92 fail for an environment reason that "
   "is NOT the harness's: the pinned nix dev shell no longer builds (date-creusot-060), "
   "so every cargo creusot / cargo nextest repro runs and dies in the shell before "
   "reaching the tool under test. Those are bucketed NOT-RUNNABLE(ENV) in "
   "analysis/ligature/reverify-VERDICTS.md, which is the distinction this finding is "
   "about: 'the harness ran it and the environment could not' is not 'the finding is "
   "wrong', and the previous three passes conflated the two."
  ),
  "workaround": (
   "none needed; use `python3 analysis/ligature/reverify.py --slow` for a complete run "
   "and `verdicts-8c.py` to re-render the verdict table"
  ),
  "severity": "friction",
  "revisit_trigger": "next re-verification pass; if any finding is again unrun without a bucket, fix the harness first",
  "pyz_sha256": PYZ,
  "tool_path": "date-creusot/analysis/ligature/reverify.py",
  "tool_version": "1.2.0"
 },
]


def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = set()
        for line in LEDGER.read_text().splitlines():
            line = line.strip()
            if line:
                existing.add(json.loads(line)["id"])
        todo = [d for d in NEW if d["id"] not in existing]
        if not todo:
            print("nothing to append: %s already present" % ", ".join(d["id"] for d in NEW))
            return 0
        before = len(existing)
        with open(LEDGER, "a") as fh:
            for d in todo:
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        after = len([l for l in LEDGER.read_text().splitlines() if l.strip()])
        print("appended %d line(s): %s" % (len(todo), ", ".join(d["id"] for d in todo)))
        print("ledger: %d -> %d lines" % (before, after))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())