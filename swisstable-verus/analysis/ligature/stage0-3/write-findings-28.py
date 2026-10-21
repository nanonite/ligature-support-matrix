#!/usr/bin/env python3
"""Append chainlink #28's findings to swisstable-verus/findings/limitations.jsonl.

Idempotent: re-running leaves the file byte-identical. Field shape is
findings-schema.md's, verbatim.
"""
import json
import os

PILOT = "swisstable-verus"
PYZ_SHA = "30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd"
PYZ = f"/home/goya/storage/full-ligature-port-workspace/{PILOT}/tools/ligature/ligature.pyz"
PYZ_VER = "ligature 1.2.1 (content hash sha256:2f607615543ca2670829989d5654f73b95a2474ca7763d4e644ce9af73218cd3, adjudicator zipapp attested)"

NEW = [
    {
        "id": "swisstable-ligature-005",
        "pilot": PILOT,
        "stage": "stage-0-3",
        "command": "cd swisstable-verus && python3 tools/ligature/ligature.pyz validate-bridge",
        "tool": "ligature",
        "chain": "C.1",
        "symptom": "Four validators collect a staged `<target>.json.draft` of their own kind and fail closed on it: validate-bridge, validate-witness, validate-exemption and validate-conflict-resolution each exit 1 with `[G1a/error] <draft>: 'review' is a required property`, and `check --json` goes to exit 3 / conditions ['human_decision_required']. `validate` (boundary contracts) and `validate-interaction` skip drafts correctly, so chainlink #97's 1.2.0 fix reached only two of the six validators that share the discovery pattern. Measured one kind at a time from a clean tree: boundary->validate exit 0, interaction->validate-interaction exit 0, bridge/witness/exemption/conflict exit 1 with check --json exit 3 in all four cases. Filed as epic #1 #110. Consequence for this pilot: while #28's 6 bridges, 2 witnesses and 1 conflict resolution sit staged, `validate-bridge` exits 1, `validate-witness` exits 1, `validate-conflict-resolution` exits 1 and `check --json` exits 3 in the live root, so a clean pre-approval baseline cannot be reported and 'a human decision is outstanding' is indistinguishable from 'the artifact is malformed'.",
        "repro_cmd": "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && bash analysis/ligature/stage0-3/run-proofs.sh && cat analysis/ligature/stage0-3/draft-collection.txt",
        "exit_code": 1,
        "expected": "staging a draft is the tool-sanctioned way to hold an artifact for review, so the validator that owns that kind must skip the draft exactly as validate and validate-interaction now do.",
        "actual": "four validators collect it, fail closed on the absent `review` block, and turn a legitimate review-in-progress into a blocking G1a error plus a human_decision_required condition.",
        "workaround": "Treat `check --json` exit 3 with nine findings all reading `'review' is a required property` on `.draft` subjects as the expected pre-approval state, not a defect; approve the drafts (the operator runbook in README.md) and the condition disappears. Do not delete or rename the drafts to get a green run -- they are the reviewable artifacts.",
        "severity": "friction",
        "revisit_trigger": "When ligature ships #110, re-run analysis/ligature/stage0-3/run-proofs.sh; validate-bridge/validate-witness/validate-conflict-resolution should exit 0 with drafts staged, and check --json should reach exit 0 once the last human checkpoint is not represented by a draft.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": PYZ,
        "tool_version": PYZ_VER,
    },
    {
        "id": "swisstable-ligature-006",
        "pilot": PILOT,
        "stage": "stage-0-3",
        "command": "cd swisstable-verus && python3 tools/ligature/ligature.pyz approve --reviewer <human> rust/swisstable-verus-core/specs/group_probe.json",
        "tool": "ligature",
        "chain": "C.1",
        "symptom": "A concept spec has a draft path but no promotion path. `draft 3 concept-to-code` stages `rust/swisstable-verus-core/specs/<snake>.json.draft` cleanly (exit 0, 'OK: generated draft passes G1a/G1b immediate checks'), and then nothing in the pipeline can consume it: `approve` exits 1 with 'error: no validator recognizes target .../specs/group_probe.json -- this pipeline only validates boundary contracts at <crate_dir>/specs/_boundaries/*.json, interactions at .../_interactions/*.json, exemptions .../_exemptions/*.json, protocol-debt .../_protocol_debt/*.json, bridges .../_bridges/*.json, witnesses .../_witnesses/*.json, conflict-resolution records at specs/_conflicts/*.json ... and closure profiles / degradation records at specs/_closure/*.json ... Evidence records at evidence/*.json ... are a valid draft target but are never approved'. That error's own enumeration is the finding: it lists every artifact type the pipeline can gate and a concept spec is not among them, while `draft` will happily produce one. Measured consequences in P2: (1) `crates[].specs_search_root` never resolves, so after approving all 14 boundary contracts `validate` is exit 0 but reports 22 non-blocking `[G2+/info] ... applies_to unverifiable -- no spec file under specs_search_root declares concept '<X>'` findings, one per referenced constraint id; (2) `validate-bridge` reports `[G2/info] ... boundary cross-reference was not checked -- no boundary context was supplied to this validator run` for each of the 6 bridges; (3) a witness spec's `approve` fails `[G2/error] ... no concept spec under the search root declares concept 'GroupProbe'`, exit 1, so no witness can ever be approved and G18/G19/G20/generate-feature-ledger/generate-contact-sheet have no reachable input; (4) `select-pilot-cluster` excludes every candidate (exit 2, per epic #1 #80). The only route around it is hand-writing a concept spec into `rust/*/specs/**`, a protected_roots path the installed SKILL.md forbids, so this is not a workaround. Filed as epic #1 #111. chainlink #94 named this as the one remaining gap but no escalation had been filed for it.",
        "repro_cmd": "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && bash analysis/ligature/stage0-3/approve-in-order.sh /tmp/opencode/p2-scratch /tmp/opencode/p2-scratch/proof.txt; grep -A4 'STEP 5' /tmp/opencode/p2-scratch/proof.txt",
        "exit_code": 1,
        "expected": "either a concept spec is promoted by a tool command, or `stage-3-concept-to-code.md` says plainly that a concept spec is consumed by concept-to-code's own tooling only and that G18/G19/G20 and validate-bridge's G2 are therefore unreachable in a port-mode project.",
        "actual": "`draft` produces an artifact that no command in the pipeline can ever consume, and the only warning is a template sentence about routing, not about the four downstream gates that go unreachable.",
        "workaround": "Keep concept specs staged as `.draft`, never hand-write them into `specs/`, and treat the 22 `G2+ applies_to unverifiable` infos plus the 6 `validate-bridge` G2 infos as the expected, non-blocking state. The operator runbook in README.md lists every constraint id by hand so those ids remain auditable while G2+ cannot check them; the 6 bridges cover the real callee preconditions, which is the part of the graph G2+ would otherwise verify.",
        "severity": "blocker",
        "revisit_trigger": "When ligature ships #111, promote the 7 staged concept specs in README.md's order, re-run `validate` (the 22 G2+ infos should become verified applies_to, or become findings if an id is wrong), then re-run `validate-bridge` and approve the 2 witnesses.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": PYZ,
        "tool_version": PYZ_VER,
    },
    {
        "id": "swisstable-ligature-007",
        "pilot": PILOT,
        "stage": "stage-0-3",
        "command": "cd swisstable-verus && python3 tools/ligature/ligature.pyz approve --reviewer <human> rust/swisstable-verus-core/specs/_bridges/BR-GROUPPROBE-WINDOW-001.json",
        "tool": "ligature",
        "chain": "C.3",
        "symptom": "The two installed, hash-pinned Stage 3 reliance templates are jointly unsatisfiable. `stage-3-boundary-drafting.md` says 'A callee precondition the caller must establish does not go here -- it belongs in a bridge specification'; `stage-3-bridge-drafting.md` says `callee_requirement` must be one of the boundary contract's own `callee_guarantees` entries. If preconditions do not belong in callee_guarantees and a bridge's callee_requirement must be one, no bridge can discharge any callee precondition. The binary enforces the second rule: with a boundary listing only the postcondition `GroupProbe.C002`, `approve` on the bridge exits 1 with `[G2/error] ... callee_requirement 'GroupProbe.C001' is not one of boundary_id 'raw_table_find__to__group_probe_match_full''s own callee_guarantees ['GroupProbe.C002'] -- a bridge cannot discharge an obligation the boundary contract never declared`. Filed as epic #1 #112. Compounding it: an EMPTY callee_guarantees list is schema-valid at draft time (the drafting path enforces no minimum length), satisfies G2 for the boundary, and would assert that the caller depends on nothing at all -- a silently vacuous reliance record instead of a visible gap. That is the specific failure mode the operator runbook has to warn about.",
        "repro_cmd": "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && grep -n 'precondition' .ligature/prompts/stage-3-boundary-drafting.md .ligature/prompts/stage-3-bridge-drafting.md && grep -n 'callee_guarantees' .ligature/prompts/stage-3-bridge-drafting.md",
        "exit_code": 1,
        "expected": "the boundary template either permits a callee precondition in callee_guarantees as the obligation a bridge discharges, or bridge G2 accepts a callee_requirement naming a `kind: precondition` constraint directly.",
        "actual": "neither: an author who follows `stage-3-boundary-drafting.md` exactly cannot get any bridge approved, and the only way to satisfy G2 is to break the boundary template's rule.",
        "workaround": "List the callee precondition in `callee_guarantees` alongside the postcondition, for exactly those 6 boundary contracts that have a bridge, and read that entry as 'the obligation a bridge discharges' rather than as a callee postcondition. The README.md runbook says so explicitly per artifact and lists all 14 boundaries' callee_guarantees so the operator can check none of them is empty.",
        "severity": "friction",
        "revisit_trigger": "When ligature ships #112, drop the precondition entries from the 6 `callee_guarantees` lists and re-approve; the boundary template's rule and the binary's G2 will then agree.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": PYZ,
        "tool_version": PYZ_VER,
    },
    {
        "id": "swisstable-ligature-008",
        "pilot": PILOT,
        "stage": "stage-0-3",
        "command": "cd swisstable-verus && python3 tools/ligature/ligature.pyz validate-interaction",
        "tool": "ligature",
        "chain": "C.1",
        "symptom": "An interaction's `evidence_links` are never resolved against the evidence set, at approve time or at validate time. Measured: with NO evidence record promoted at all, all 15 #28 interactions were submitted; the 14 boundary-required ones failed R2 (correctly, no boundary promoted) but the single `inform` interaction `raw_table_find_to_hash_mix_h2`, which declares `evidence_links: [\"E-001\"]`, approved at exit 0 and `validate-interaction` then reported 'OK: all interactions pass G1a/G1b (incl. computed eligibility), G15 protocol coverage, and R2 coverage (15 discovered)' exit 0. A dangling id is also accepted: re-drafting the same interaction with `evidence_links: [\"E-999\", \"E-not-a-record\"]` also approves at exit 0 and passes `validate-interaction`. The contrast is a conflict-resolution record, whose `evidence` list IS resolved (`[G1b/error] ... evidence id 'E-007' does not resolve to any real evidence record -- dangling reference`). Not filed as an escalation: `doctor` declares the underlying gap in its own 'Not yet implemented' section -- 'G4/G5 evidence tracing/grounding: not yet implemented -- required/bug-compat evidence tracing to nothing (G4) and ungrounded obligations (G5) both need cross-referencing interaction evidence_links (#16) to evidence ids (#20), which exist individually but aren't cross-referenced against each other yet' -- so it is a known unimplemented gate, not a defect. Recorded because it means `evidence_links` is documentation, not a checked reference, and the operator must not read a green `validate-interaction` as 'the links resolve'.",
        "repro_cmd": "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && bash analysis/ligature/stage0-3/run-proofs.sh && sed -n '/NO boundaries and NO evidence/,/validate-interaction/p' analysis/ligature/stage0-3/order-constraints.txt",
        "exit_code": 0,
        "expected": "a dangling `evidence_links` id is refused the way a dangling conflict-resolution `evidence` id is.",
        "actual": "`evidence_links` is never resolved; `E-999` and `E-not-a-record` both approve and validate cleanly at exit 0.",
        "workaround": "Verify `evidence_links` by hand. artifacts.py's integrity pass refuses to emit an interaction whose `evidence_links` name an id not in its own EVIDENCE table, so the 15 shipped interactions are checked mechanically even though the binary does not check them.",
        "severity": "friction",
        "revisit_trigger": "When G4/G5 evidence tracing is implemented, re-run analysis/ligature/stage0-3/run-proofs.sh and confirm the interaction evidence links are then resolved rather than merely present.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": PYZ,
        "tool_version": PYZ_VER,
    },
    {
        "id": "swisstable-ligature-009",
        "pilot": PILOT,
        "stage": "stage-0-3",
        "command": "cd swisstable-verus && python3 tools/ligature/ligature.pyz draft 3 boundary-drafting <target>",
        "tool": "ligature",
        "chain": "C.1",
        "symptom": "`ligature.pyz draft` exits 1 on a schema-invalid body but STILL leaves the invalid body staged on disk as `<target>.json.draft`. Measured on an interactive probe: `staged draft: .../probe.json.draft` then `FAIL: generated draft has 3 G1a/G1b finding(s) -- fix before approve()` with exit 1, and the three G1a errors listed. `approve` on that same target then reports `<target>.json.draft fails validation, refusing to promote` and exits 1, so the failure is not silently promoted -- but a staged, known-invalid draft is indistinguishable on disk from a staged, valid draft, and for the four validators that collect drafts (#110) an invalid draft and a valid one produce the identical `'review' is a required property` finding. Also note the documented argument shape is wrong: `approve` is given the TARGET path, not the `.draft`; passing the `.draft` gives `error: target ... is not a .json file -- this pipeline only recognizes .json artifacts ...`. And `draft` does NOT print the prompt it rendered on success, only a `--- paste the model's JSON-only response, then EOF (ctrl-D) ---` banner, so the exact template text an artifact was produced from has to be re-derived from `.ligature/prompts/`.",
        "repro_cmd": "cd /tmp/opencode && rm -rf p2-draft-probe && mkdir p2-draft-probe && rsync -a --exclude 'upstream/' /home/goya/storage/full-ligature-port-workspace/swisstable-verus/ p2-draft-probe/ && cd p2-draft-probe && printf '{\"schema_version\":\"1.0\",\"boundary_id\":\"x\"}' | python3 tools/ligature/ligature.pyz draft 3 boundary-drafting rust/swisstable-verus-core/specs/_boundaries/probe.json --var caller_concept=A --var caller_method=m --var callee_concept=B --var callee_method=n --var caller_spec='{}' --var callee_spec='{}' --var reliance_policy='x' --var prior_artifact='' --var finding='' --var caller_concept_snake=a --var callee_concept_snake=b; echo exit=$?; ls rust/swisstable-verus-core/specs/_boundaries/",
        "exit_code": 1,
        "expected": "a draft that fails its own immediate checks is either not staged or clearly marked, so the tree cannot hold an invalid artifact that looks valid.",
        "actual": "the invalid body is staged at exit 1, and the on-disk draft carries no marker distinguishing it from a valid one.",
        "workaround": "Read the exit code of `draft`, not the file's existence. analysis/ligature/stage0-3/artifacts.py treats a non-zero `draft` exit as a hard failure and reports it as such in drafting.txt; re-running the whole set re-stages every target, so a corrected body always replaces the bad draft.",
        "severity": "friction",
        "revisit_trigger": "When ligature stops staging a body that failed its own G1a/G1b check (or marks it), re-run `bash analysis/ligature/stage0-3/run-proofs.sh` and confirm a deliberately malformed body leaves no file behind.",
        "pyz_sha256": PYZ_SHA,
        "tool_path": PYZ,
        "tool_version": PYZ_VER,
    },
]


# Records already in the file whose text is superseded by this revision, keyed by id.
# Rewritten in place (never duplicated) so the file stays byte-stable on re-run.
REPLACE: dict = {}


def _revise_007(old: dict) -> dict:
    o = dict(old)
    o["symptom"] = (
        "The two installed, hash-pinned Stage 3 reliance templates are jointly unsatisfiable, "
        "and the consequence is a hard G2+/error, not a vacuous record. "
        "stage-3-boundary-drafting.md says 'A callee precondition the caller must establish does "
        "not go here -- it belongs in a bridge specification'; stage-3-bridge-drafting.md says "
        "callee_requirement must be one of the boundary contract's own callee_guarantees. The "
        "binary enforces the second: with a boundary listing only the postcondition "
        "GroupProbe.C002, approve on the bridge exits 1 with `[G2/error] ... callee_requirement "
        "'GroupProbe.C001' is not one of boundary_id 'raw_table_find__to__group_probe_match_full''s "
        "own callee_guarantees ['GroupProbe.C002'] -- a bridge cannot discharge an obligation the "
        "boundary contract never declared`. Obeying the boundary template therefore makes every "
        "bridge unapprovable, and the only way through G2 is to put the precondition in "
        "callee_guarantees anyway. That is NOT silently harmless. G2+ then requires the entry's "
        "`applies_to` to include the boundary's callee method, and a precondition is normally "
        "declared on a NEIGHBOURING member (the loader, or the constructor), so the combination "
        "fails as `[G2+/error] ... 'GroupProbe.C001' applies_to ['load'], which does not include "
        "this boundary's callee method 'match_full'`. Measured in the post-#111 probe "
        "(analysis/ligature/stage0-3/probe-post111.sh) on the first attempt at chainlink #28: "
        "4 of 14 boundary contracts carried a callee_guarantee whose applies_to excluded the "
        "callee, which cascaded into 4 R2/error on validate-interaction ('no boundary contract "
        "for this edge'), 3 G2/error on validate-bridge ('boundary_id does not resolve to any "
        "real boundary contract'), and check --json exit 1 with 4 high findings. The pilot's own "
        "escape -- re-cut each precondition so its applies_to names the callee method it is "
        "established at -- works, is measured in post-111-g2plus.txt, and is now enforced by "
        "artifacts.py's check_applies_to. But it means the author must restate every callee "
        "precondition at the call site, which is exactly the work the boundary template told "
        "them not to do. Filed as epic #1 #112.")
    o["repro_cmd"] = ("cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
                      "bash analysis/ligature/stage0-3/run-proofs.sh && grep -n 'precondition' "
                      ".ligature/prompts/stage-3-boundary-drafting.md "
                      ".ligature/prompts/stage-3-bridge-drafting.md && sed -n '/validators in the "
                      "post-#111 state/,$p' analysis/ligature/stage0-3/post-111-g2plus.txt")
    o["actual"] = (
        "neither: an author who follows stage-3-boundary-drafting.md cannot get any bridge "
        "approved, and an author who breaks its rule to satisfy G2 then fails G2+ unless every "
        "precondition's applies_to is restated to name the callee method. A boundary whose entry "
        "misses that is not counted as covering its edge, so it also breaks R2 for the "
        "interaction and G2 for every bridge on it. An EMPTY callee_guarantees list remains "
        "schema-valid and satisfies G2, which is the other failure mode the templates invite.")
    o["workaround"] = (
        "For each of the 6 bridged boundaries, declare the precondition so its applies_to "
        "includes the callee method it is established at -- GroupProbe.C001 on "
        "load/match_full/match_empty_or_deleted, ProbeSeq.C001 on from_capacity_and_h1/offset, "
        "ControlBytes.C003 on set_dead, ControlBytes.C005 on clear_dead, RawTable.C003 on insert "
        "-- list it in callee_guarantees next to the postcondition, and read it as 'the "
        "obligation a bridge discharges'. artifacts.py's check_applies_to refuses to emit any "
        "artifact where this does not hold, and proof 5 measures the outcome.")
    o["severity"] = "friction"
    o["revisit_trigger"] = ("When ligature ships #112, drop the precondition entries from the 6 "
                            "callee_guarantees lists and re-approve; the boundary template's rule "
                            "and the binary's G2/G2+ will then agree. Proof 5 is the re-check: "
                            "it must still report validate exit 0 with G2+ actually passing.")
    return o


NEW_REPLACE = {}


def _revise_006(old: dict) -> dict:
    """The G2+ count is re-derived, not remembered.

    It changed twice under this pilot's feet: 18 when the set was first drafted,
    20 after the ProbeSeq re-cut and the added ControlBytes.C008 (#28 review), and
    earlier still 22 in a variant that had been probed separately. The value now
    lives in swisstable-verus/README.md and is derived from the staged boundary
    artifacts by analysis/ligature/stage0-3/check-runbook.py, which fails if the
    README and the artifacts disagree.
    """
    o = dict(old)
    o["symptom"] = o["symptom"].replace(
        "reports 22 non-blocking `[G2+/info] ",
        "reports 20 non-blocking `[G2+/info] ")
    o["workaround"] = (
        "Keep concept specs staged as `.draft`, never hand-write them into `specs/`, and treat "
        "the 20 `G2+ applies_to unverifiable` infos as the expected, non-blocking state. Note "
        "that the six `G2 boundary cross-reference was not checked` infos that appear alongside "
        "them are NOT this escalation's fault: proof 5 "
        "(analysis/ligature/stage0-3/post-111-g2plus.txt) shows they survive the concept specs "
        "becoming resolvable, so they come from `check` re-validating a promoted bridge without "
        "boundary context. They are `info` and change no exit code. The operator runbook in "
        "README.md lists every callee_guarantees id by hand so those ids stay auditable while "
        "G2+ cannot check them, and check-runbook.py now derives the 20 from the boundary "
        "artifacts rather than restating it.")
    o["revisit_trigger"] = (
        "When ligature ships #111, promote the 7 staged concept specs in README.md's order, "
        "re-run `validate` (the 20 G2+ infos should become a real G2+ pass -- proof 5 records "
        "what that reads: 'OK: all boundary contracts pass G1a/G1b/G2+ (14 discovered)'), then "
        "re-run `validate-bridge` and approve the 2 witnesses. If instead a `high` G2+/error "
        "appears, an `applies_to` does not cover its boundary's callee method; that is #112's "
        "shape, not this one.")
    return o


def main():
    # analysis/ligature/stage0-3/ -> analysis/ligature/ -> analysis/ -> pilot root
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.normpath(os.path.join(here, "..", "..", "..", "findings", "limitations.jsonl"))
    lines = [l.rstrip("\n") for l in open(dest) if l.strip()]
    existing = [json.loads(l) for l in lines]
    by_id = {e["id"]: e for e in existing}
    for fid, reviser in (("swisstable-ligature-006", _revise_006),
                          ("swisstable-ligature-007", _revise_007)):
        if fid in by_id:
            NEW_REPLACE[fid] = reviser(by_id[fid])
    REPLACE.update(NEW_REPLACE)

    changed = 0
    out = []
    for i, e in enumerate(existing):
        new = REPLACE.get(e["id"])
        if new and new != e:
            out.append(json.dumps(new, ensure_ascii=False))
            changed += 1
        else:
            out.append(lines[i])
    appended = [n for n in NEW if n["id"] not in by_id]
    for n in appended:
        out.append(json.dumps(n, ensure_ascii=False))

    if changed or appended:
        with open(dest, "w") as fh:
            fh.write("\n".join(out) + "\n")
    print("rewrote %d finding(s), appended %d: %s (file now %d records)"
          % (changed, len(appended),
             ", ".join(n["id"] for n in appended) or "-", len(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())