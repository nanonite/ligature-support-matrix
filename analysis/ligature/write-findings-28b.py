#!/usr/bin/env python3
"""Append the chainlink #28 second-pass findings, idempotently.

Every id already present is left alone, so re-running this is safe and never
rewrites another issue's line. Written as one read-modify-write of the whole
file so the append is atomic with respect to the line count.
"""
import json
import pathlib

PATH = pathlib.Path(__file__).resolve().parents[2] / "findings" / "limitations.jsonl"
PYZ = "/home/goya/storage/full-ligature-port-workspace/swisstable-verus/tools/ligature/ligature.pyz"
COMMON = {
    "pilot": "swisstable-verus",
    "tool": "ligature",
    "pyz_sha256": "30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd",
    "tool_path": PYZ,
    "tool_version": "ligature 1.2.1 (content hash sha256:2f607615543ca2670829989d5654f73b95a2474ca7763d4e644ce9af73218cd3, adjudicator zipapp attested)",
}

NEW = [
    dict(
        COMMON,
        id="swisstable-ligature-012",
        stage="stage-4",
        chain="C.1",
        command="cd /tmp/opencode/s2/v121 && python3 tools/ligature/ligature.pyz check-bridges   # one bridge re-cut to the only grammar G9 accepts",
        symptom="Fixing swisstable-ligature-010 is necessary but NOT sufficient: G9 has a second, independent precondition that no re-cut can satisfy. With `bridge_logic.bindings` {\"self\": \"RawTable\", \"slot\": \"usize\"} and `bridge_logic.premises` [\"self.is_full_ctrl(slot)\", \"self.is_not_sentinel_ctrl(slot)\"], BR-CONTROLBYTES-SETDEAD-001's grammar error disappears and is replaced by: `[G9/error] BR-CONTROLBYTES-SETDEAD-001: harness generated for verus at ci/harness/BR-CONTROLBYTES-SETDEAD-001.verus.rs, but the project descriptor configures no verifier_backends.verus command -- nothing was checked, so no result is recorded (the ceiling here is harness-tested, never bridge-checked)`. `project-descriptor.json` declares `verifier_policy.default: \"verus\"` and no `verifier_backends` key at all, and it is a user-owned protected file. So the remediation recorded for #113 and repeated in README.md:930-932 -- re-cut the 6 bridges, then require `gate-g9` exit 0 -- cannot succeed as written: an operator must add `verifier_backends.verus.command` to the descriptor AND the bridges must be re-cut, and the two are independent.",
        repro_cmd="rsync -a --delete --exclude 'analysis/codesight/index/' --exclude 'upstream/' --exclude 'rust/*/target/' /home/goya/storage/full-ligature-port-workspace/swisstable-verus/ /tmp/opencode/s2/v121/ && cd /tmp/opencode/s2/v121 && for f in rust/swisstable-verus-core/specs/_boundaries/*.json.draft rust/swisstable-verus-core/specs/_interactions/*.json.draft rust/swisstable-verus-core/specs/_bridges/*.json.draft; do python3 tools/ligature/ligature.pyz approve \"${f%.draft}\" --reviewer scratch-grammar-probe >/dev/null 2>&1; done && python3 -c \"import json,pathlib;p=pathlib.Path('rust/swisstable-verus-core/specs/_bridges/BR-CONTROLBYTES-SETDEAD-001.json');d=json.loads(p.read_text());d['bridge_logic']['bindings']={'self':'RawTable','slot':'usize'};d['bridge_logic']['premises']=['self.is_full_ctrl(slot)','self.is_not_sentinel_ctrl(slot)'];p.write_text(json.dumps(d,indent=2))\" && python3 tools/ligature/ligature.pyz check-bridges; echo exit=$?",
        exit_code=1,
        expected="`gate-g9` exit 0 once the bridge's premises are predicate applications and its bindings are snake_case.",
        actual="The grammar error clears and a different [G9/error] appears: the harness is generated but no verifier backend is configured, so nothing is checked and no bridge-check record exists. Epic #1 #113 names two G9 rules and does not mention verifier_backends, the generated ci/harness/ path, or this second failure; recorded as a comment on #113 rather than a duplicate subissue.",
        workaround="Treat G9 as having two preconditions: (1) the artifact shape, which a bridge re-draft fixes, and (2) a `verifier_backends.verus.command` in project-descriptor.json, which only an operator can add. Never read a `validate-bridge` exit 0, or a `check-bridges` 'OK: 0 artifact(s) written', as G9 passing: the first does not run G9 at all, and the second is printed when there are zero promoted bridges.",
        severity="blocker",
        revisit_trigger="When `project-descriptor.json` gains a verifier_backends.verus command, or when epic #1 #113 is closed, re-cut the 6 bridges and re-run analysis/ligature/stage4-7/stage45-scratch-proof.sh requiring `gate-g9` exit 0.",
    ),
    dict(
        COMMON,
        id="swisstable-ligature-013",
        stage="stage-4",
        chain="C.1",
        command="cd /tmp/opencode/s2/v121 && python3 - <<'PY' ... rewrite bridge_logic.premises ... PY && python3 tools/ligature/ligature.pyz check-bridges",
        symptom="The accepted language of G9's `bridge_logic.premises` is narrower than the error message states, and its boundary has now been mapped term by term on 1.2.1. ACCEPTED: a bare declared binding (`self`), a dotted chain (`self.ctrl.len()`), a chain ending in calls (`self.foo()`, `self.a.b.c()`), call arguments that are declared bindings (`self.foo(slot)`), and the empty string -- so G9 does not enforce the template's 'at least one premise'. REJECTED, each with its own message: every operator (`=`, `<`, `>`, `&&`, `||`, `+`, `-`), every literal (`1`, `0xFF`), every quantifier (`forall|i: u64|`), indexing (`self.ctrl[0]`), paths (`Self::f()`), and any term rooted outside the bindings -- `foo(self)` gives \"premise[0]: foo is rooted at 'foo', which bridge_logic.bindings does not declare (declared: [...]) -- a harness cannot pass a value it was never given\", where the declared set is the `bindings` keys PLUS every `required_local_facts[].fact_id`. Separately, a non-snake_case binding key is rejected with \"binding name 'GROUP_WIDTH' is not snake_case -- it becomes a harness parameter name\". `check-bridges` shows why the narrowness is load-bearing: it writes ci/harness/<id>.<verifier>.rs and pastes each premise verbatim into a Verus `requires` clause, so a premise must be a boolean-valued term for the harness to compile. A premise written as the template describes it (`slot < self.capacity()`) is a valid boolean and is rejected; one written as a term (`self.ctrl(slot)`) is accepted and is not a boolean. The only shape G9 admits is a call to a boolean-returning predicate over the bindings, which means that predicate has to exist as a method on the ported type.",
        repro_cmd="sed -n '/3. NEW: the exact grammar G9 accepts/,/^4\\. NEW/p' /home/goya/storage/full-ligature-port-workspace/swisstable-verus/analysis/ligature/stage0-3/recheck-1.2.1.txt",
        exit_code=1,
        expected="either the bridge template documents the exact accepted premise language, or G9 accepts a boolean premise expression as the template's 'premise expression' describes.",
        actual="The template's example shape is rejected by the gate; the accepted shape is not documented anywhere, so a bridge re-draft cannot be written correctly from the template alone. This is the concrete recipe for the #113 re-cut, and it belongs with it rather than as a separate defect.",
        workaround="Write each premise as `self.some_bool_predicate(arg)` where `some_bool_predicate` is a real method on the ported type returning bool, keep every binding name snake_case, and pass arguments that are declared bindings or declared `required_local_facts[].fact_id`s. Do not use literals, operators, quantifiers, indexing or paths.",
        severity="friction",
        revisit_trigger="When epic #1 #113 is closed, re-derive this table against the fixed binary and replace it with the template's own wording.",
    ),
    dict(
        COMMON,
        id="swisstable-ligature-014",
        stage="stage-4",
        chain="C.1",
        command="cd /tmp/opencode/s2/v121 && python3 tools/ligature/ligature.pyz check-bridges --workspace /tmp/opencode/s2/v121 ; echo $? ; python3 tools/ligature/ligature.pyz write-set-check ; echo $?",
        symptom="Two traps around G9 that cost a wrong conclusion and a stray write. (a) `check-bridges` is not read-only: it WRITES a generated harness to ci/harness/<id>.<verifier>.rs in the workspace, and `write-set-check` still reports `write set: clean` with that directory present, because `ci/harness/**` is in neither `allowed_roots` nor `protected_roots` of project-descriptor.json -- the same class as WORKER-CONTRACT §0.0's `ci/manifest/` observation, one directory over. (b) `--workspace` is a GLOBAL flag and must precede the subcommand: `check-bridges --workspace /abs` exits 2 with an argparse usage error, while `--workspace /abs check-bridges` is the form that runs. WORKER-CONTRACT §0.0 says 'pass an absolute --workspace' without saying where in the command line it goes. (1.2.1 has the relative-`--workspace` fix from #96, so the absolute form is no longer needed for correctness here -- recorded because getting the placement wrong is a silent-looking exit 2.)",
        repro_cmd="rsync -a --delete --exclude 'analysis/codesight/index/' --exclude 'upstream/' /home/goya/storage/full-ligature-port-workspace/swisstable-verus/ /tmp/opencode/s2/v121/ && cd /tmp/opencode/s2/v121 && python3 tools/ligature/ligature.pyz check-bridges; echo exit=$?; ls ci/harness 2>/dev/null; python3 tools/ligature/ligature.pyz write-set-check | head -1; python3 tools/ligature/ligature.pyz check-bridges --workspace \"$PWD\" >/dev/null 2>&1; echo after=$?; python3 tools/ligature/ligature.pyz --workspace \"$PWD\" check-bridges >/dev/null 2>&1; echo before=$?",
        exit_code=2,
        expected="`check-bridges` either writes only inside the declared write set or `write-set-check` reports the generated directory; and `--workspace` accepted in either position.",
        actual="The generated ci/harness/ directory is invisible to the write-set verdict, and `--workspace` after the subcommand is a usage error (exit 2) while before it is accepted.",
        workaround="Run G9 only on an rsync scratch copy and diff `ci/harness/` out afterwards; pass `--workspace` before the subcommand if you pass it at all; and do not treat `write-set-check: clean` as evidence that ci/harness/ is a declared location.",
        severity="friction",
        revisit_trigger="When `write_set` gains a `ci/harness/**` entry, or when check-bridges stops writing, re-check that the generated harness is either declared or gone.",
    ),
]


def main():
    lines = [l for l in PATH.read_text().splitlines() if l.strip()]
    have = {json.loads(l)["id"] for l in lines}
    added = []
    for rec in NEW:
        if rec["id"] in have:
            continue
        lines.append(json.dumps(rec, ensure_ascii=False, sort_keys=False))
        added.append(rec["id"])
    tmp = PATH.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(lines) + "\n")
    tmp.replace(PATH)
    print(f"findings: {len(lines)} lines, added {added or 'nothing (already present)'}")


if __name__ == "__main__":
    main()