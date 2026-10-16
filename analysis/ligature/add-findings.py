#!/usr/bin/env python3
"""Append the chainlink #13 findings to date-creusot/findings/limitations.jsonl.

Kept as a script so the eleven entries added by this issue are diffable against
the twenty that chainlink #11 and #12 left, and so a re-run is idempotent
(entries whose id already exists are skipped).
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "findings" / "limitations.jsonl"
PYZ = str(ROOT / "tools" / "ligature" / "ligature.pyz")
SHA = "0ffe6e0eeba3cf329228b9ce3e8f0d576458b6b2a9aec48e43f60a016f9afc4f"
VER = ("ligature 1.0.0; content hash "
       "sha256:74898f6b9feef0d6759d1a81c84692559eab36515a65492ea1697c0187f54adb")

CLEANROOM = ("rm -rf /tmp/dc13 && mkdir -p /tmp/dc13 && tar "
             "--exclude=./upstream --exclude=./analysis/codesight "
             "-C date-creusot -cf - . | tar -C /tmp/dc13 -xf - && cd /tmp/dc13 && ")

NEW = [
    dict(
        id="date-ligature-019",
        pilot="date-creusot",
        stage="stage-0-evidence-intake",
        command="python3 tools/ligature/ligature.pyz draft 0 evidence-intake <target> --var x=1",
        tool="ligature",
        chain="new",
        symptom=(
            "The two writing commands enforce a scope check, but it is crate membership and "
            "nothing else, which is the confirmation chainlink #76 could not obtain because "
            "draft/approve were ahead of it in the graph. A draft target is accepted if and "
            "only if it is under a declared crates[].crate_dir, or is directly "
            "evidence/<file>.json at the workspace root. Inside a crate everything is "
            "accepted: rust/date-creusot-core/rogue/evil.rs, rust/date-creusot-core/src/lib.rs "
            "and rust/date-creusot-core/specs/rogue.md all reach template rendering, and "
            "ci/manifest/installation.json, docs/reliance-policy.md and "
            "project-descriptor.json are correctly refused. write_set.allowed_roots "
            "('rust/*/src/', 'rust/*/tests/') and write_set.protected_roots are read by "
            "neither command."),
        repro_cmd=CLEANROOM + "for c in rust/date-creusot-core/rogue/evil.rs "
                  "rust/date-creusot-core/src/lib.rs rust/rogue/evil.rs docs/evil.md "
                  "project-descriptor.json ci/manifest/installation.json; do "
                  "out=$(python3 tools/ligature/ligature.pyz draft 0 evidence-intake \"$c\" "
                  "--var x=1 2>&1); printf '%-44s %s\\n' \"$c\" \"$(printf '%s' \"$out\" | "
                  "head -1 | cut -c1-70)\"; done",
        exit_code=1,
        expected=(
            "draft/approve refuse a target outside write_set.allowed_roots and inside "
            "write_set.protected_roots, since those are the only boundary the descriptor "
            "declares for the implementation."),
        actual=(
            "The only test is 'does this path start with a declared crate_dir'. "
            "rust/date-creusot-core/rogue/evil.rs passes it and reaches template rendering; "
            "rust/rogue/evil.rs fails it with 'does not belong to any crate declared in the "
            "project descriptor, and is not a recognized workspace-level artifact location "
            "either -- refusing to draft/approve outside a declared scope'."),
        workaround=(
            "Keep the boundary by hand as chainlink #76 already prescribes: upstream/date "
            "read-only at its pinned commit, and no hand-created files under "
            "rust/date-creusot-core/ outside the tool's own canonical artifact directories. "
            "Cross-reference chainlink #76."),
        severity="friction",
        revisit_trigger=(
            "The chainlink #76 re-check, and on any ligature release that makes draft/approve "
            "consult write_set. Also re-measure before chainlink #15 (implement the port), "
            "which is the issue that would actually try to write outside the allowed roots."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-020",
        pilot="date-creusot",
        stage="stage-0-evidence-intake",
        command="python3 tools/ligature/ligature.pyz approve evidence/E-1.json --reviewer chainlink-reviewer --reviewed-at 2026-09-25",
        tool="ligature",
        chain="new",
        symptom=(
            "Stage 0 evidence has a draft path and no promotion path, and the staged draft is "
            "a blocking finding for the commands meant to consume it. draft accepts "
            "evidence/E-1.json, stages evidence/E-1.json.draft and prints 'OK: generated draft "
            "passes G1a/G1b immediate checks' at exit 0. approve then refuses permanently by "
            "design, with its own explanation: 'Evidence records at evidence/*.json "
            "(workspace-level) are a valid draft target but are never approved -- they carry "
            "no review block, so approve() cannot promote them.' The consequence is that "
            "validate-evidence exits 1 on the staged file ('must be a .json file, found suffix "
            "'.draft'' plus 'filename stem E-1.json does not match id E-1') and check --json "
            "reports exit_code 1 with conditions ['blocking_findings']. The only way out is a "
            "hand mv, which no command performs or records. check next never names this: it "
            "reports [refresh-c-static] and nothing about the pending evidence draft."),
        repro_cmd=CLEANROOM + "python3 tools/ligature/ligature.pyz draft 0 evidence-intake "
                  "evidence/E-1.json --var project_descriptor='{\"mode\":\"port\"}' "
                  "--var source_material=x --var prior_artifact='(none)' --var finding='(none)' "
                  "< analysis/ligature/draft-responses/E-1.json >/dev/null 2>&1; echo \"draft "
                  "exit=$?\"; ls evidence/; python3 tools/ligature/ligature.pyz "
                  "validate-evidence; echo \"validate-evidence exit=$?\"; python3 "
                  "tools/ligature/ligature.pyz check --json | tail -1",
        exit_code=1,
        expected=(
            "Either a code path that promotes a staged evidence draft to its target, or a "
            "draft-time refusal of evidence/*.json so a partial artifact is never created. "
            "Boundary contracts and interactions honour exactly that contract -- a staged "
            "draft is promotable by approve -- so the expectation is established by the same "
            "binary."),
        actual=(
            "draft exit 0 with 'staged draft: evidence/E-1.json.draft'; approve exit 1 with the "
            "'never approved' message; validate-evidence exit 1 with two G1b errors on the "
            ".draft suffix; check --json exit_code 1, conditions ['blocking_findings']. No "
            "command moves the file."),
        workaround=(
            "The fifteen evidence records in this root were produced by draft and then moved "
            "from evidence/E-<n>.json.draft to evidence/E-<n>.json with mv -- the exact path "
            "passed to draft, which its own --help calls 'Target artifact path the draft will "
            "eventually promote to'. No record was edited: each promoted file is byte-identical "
            "to the response body kept in analysis/ligature/draft-responses/E-<n>.json, verified "
            "with cmp. The move is scripted in analysis/ligature/stage-0-3.sh and recorded in "
            "analysis/ligature/stage-3-decisions.md section 5 and the pilot README."),
        severity="blocker",
        revisit_trigger=(
            "Immediate, and it gates the rest of the P1 chain: chainlink #14 cannot pass "
            "validate-evidence while any .draft sits in evidence/, and neither can P2 or P3. "
            "Re-check on any ligature release."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-021",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="for t in bridge-drafting witness-drafting concept-to-code exemption-drafting protocol-debt-drafting conflict-resolution-drafting; do python3 tools/ligature/ligature.pyz draft 3 $t <target> --var x=1; done",
        tool="ligature",
        chain="new",
        symptom=(
            "draft can author exactly three artifact kinds -- evidence-intake (stage 0), "
            "boundary-drafting and interaction-drafting (stage 3) -- out of the seven artifact "
            "types the binary's own approve error message calls recognized, plus concept "
            "specs. Enumerated by exhaustion: 31 candidate template names across stages 0 and "
            "3, all others answering 'error: no template at "
            "/tmp/ligature-data-XXXX/prompts/stage-3-<name>.md' at exit 1. draft's stage "
            "argument is a closed {0,3} enum, so there is no other stage to search. Meanwhile "
            "the same binary implements validate-bridge, check-bridges, gate-g9, "
            "validate-witness, render-witness, gate-g18/g19/g20, generate-feature-ledger and "
            "generate-contact-sheet, and ships "
            "vendor/concept-to-code/schemas/spec.schema.json with no verb that drives it. "
            "approve's message enumerates _boundaries, _interactions, _exemptions, "
            "_protocol_debt, _bridges, _witnesses and specs/_conflicts as 'recognized'; draft "
            "produces two of the seven. Compounding effect: because constraint ids can only come "
            "from concept-to-code, and concept-to-code has no verb, stage-3-interaction-drafting "
            "forbids inventing one ('do not emit an interaction with a fabricated id ... output "
            "nothing') while G2++ rejects an empty relies on a boundary-required edge, so no "
            "boundary-required interaction is draftable without hand-declared ids."),
        repro_cmd=CLEANROOM + "for t in bridge-drafting witness-drafting concept-to-code "
                  "concept-drafting exemption-drafting protocol-debt-drafting "
                  "conflict-resolution-drafting bridge witness; do out=$(python3 "
                  "tools/ligature/ligature.pyz draft 3 $t "
                  "rust/date-creusot-core/specs/_boundaries/x.json --var x=1 2>&1); printf "
                  "'%-32s exit=%s %s\\n' $t $? \"$(printf '%s' \"$out\" | head -1 | "
                  "sed 's#/tmp/ligature-data-[^/]*/##' | cut -c1-60)\"; done; echo '--- the "
                  "three that exist ---'; for t in boundary-drafting interaction-drafting; do "
                  "python3 tools/ligature/ligature.pyz draft 3 $t "
                  "rust/date-creusot-core/specs/_boundaries/x.json --var x=1 2>&1 | head -1; "
                  "done",
        exit_code=1,
        expected=(
            "Every artifact type the binary validates, gates and promotes is authorable through "
            "the sanctioned draft -> approve path, or draft says plainly which kinds it cannot "
            "author, so an agent knows before it starts."),
        actual=(
            "'no template at .../stage-3-bridge-drafting.md' and the same for witness, concept, "
            "exemption, protocol-debt and conflict-resolution. The set of draftable kinds is "
            "discoverable only by exhausting names, and the SKILL.md authority region's table "
            "('ligature draft <kind> <target> -- Stage 0/3 one-shot LLM draft') implies a "
            "per-kind registry with more entries than exist."),
        workaround=(
            "Authored only what the binary can author: 15 evidence records, 4 boundary "
            "contracts, 4 interactions. Declared the pilot's constraint ids explicitly, with "
            "statement, source file, line range and evidence ids, in "
            "analysis/ligature/constraint-ids.json, rather than fabricate them inside the "
            "artifacts. Bridges and witnesses were deliberately NOT hand-written into specs/: "
            "that is the same untracked fabrication, and chainlink #14 and #16 are the issues "
            "positioned to decide what a bridge or witness for this subset should be."),
        severity="blocker",
        revisit_trigger=(
            "Immediate, and it is a hard ceiling on Stages 0-3 for all three pilots. Chainlink "
            "#16 (Stage 8A: bridges, witnesses) has no authoring path in v1.0. Re-check on any "
            "ligature release; also re-probe the template name list before P2 and P3."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-022",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="python3 tools/ligature/ligature.pyz status ; python3 tools/ligature/ligature.pyz check",
        tool="ligature",
        chain="new",
        symptom=(
            "G2+'s applies_to traceability for a boundary contract's callee_guarantees can "
            "never be satisfied. After promoting four real boundary contracts, status and check "
            "each report one finding per guarantee, at info severity: \"G2+: 'Weekday.C1': "
            "applies_to unverifiable -- no --specs-search-root given\". No command in the CLI "
            "accepts --specs-search-root (checked --help on validate, validate-bridge, "
            "validate-interaction, check, status, gate), and the descriptor field that should "
            "be the fallback, crates[0].specs_search_root = \"rust\" (filled by chainlink "
            "#12), is not read. So a correct constraint id and a dangling one are "
            "indistinguishable in every reachable command, and check still exits 0. This is the "
            "same class as chainlink #76 and #75: a required, accepted, unread descriptor "
            "field. Here the degradation is visible in the binary's own output rather than "
            "silent, which is better, but it is still permanent."),
        repro_cmd=CLEANROOM + "python3 tools/ligature/ligature.pyz status | sed -n '/open "
                  "findings/,/human decisions/p'; for c in validate validate-bridge "
                  "validate-interaction check status gate; do printf '%-22s ' $c; python3 "
                  "tools/ligature/ligature.pyz $c --help 2>&1 | grep -ci 'specs.search\\|"
                  "specs_search'; done; jq -c '.crates[0].specs_search_root' "
                  "project-descriptor.json",
        exit_code=0,
        expected=(
            "callee_guarantees ids resolve against crates[].specs_search_root, or a command "
            "accepts the --specs-search-root the finding names, so applies_to is verifiable and "
            "a dangling id is an error rather than an unverifiable note."),
        actual=(
            "0 matches for specs_search/specs-search on all six --help outputs; the descriptor "
            "field is present and ignored; every promoted boundary contract carries a "
            "permanent info finding and check exits 0 with conditions []."),
        workaround=(
            "Treat a boundary contract's callee_guarantees as unverified by the tool and audit "
            "the ids by hand. This root declares them in "
            "analysis/ligature/constraint-ids.json with source line ranges so the audit is "
            "mechanical. Cross-reference chainlink #59 (C.5 dangling constraint ID) and #76."),
        severity="blocker",
        revisit_trigger=(
            "Before chainlink #14's accept-promotion: a Stage 4.5 receipt can accept a boundary "
            "contract whose guarantees name constraints that do not exist. Also re-run for the "
            "chainlink #59 C.5 cross-cutting re-check."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-023",
        pilot="date-creusot",
        stage="stage-0-evidence-intake",
        command="find . -name 'exit-code*' ; python3 tools/ligature/ligature.pyz --help | grep -i 'exit code'",
        tool="ligature",
        chain="new",
        symptom=(
            "The plan directs the worker to 'Record every non-zero exit code against "
            "docs/exit-code-contract.md as the binary prints it'. That file does not exist -- "
            "not in this root, not anywhere in the workspace, and not among the files init "
            "installs (nine files, of which the only ones under .ligature/ are two schemas and "
            "three prompts). The binary's own --help has no exit-code table either; the only "
            "occurrence of the phrase is one line of gate-g20 prose in the capability listing. "
            "The machine-readable contract that does exist is check --json's own result object, "
            "and the process exit code agrees with it in every case measured (result.exit_code "
            "0 or 1 against $? 0 or 1). Exit 3 is documented only indirectly, in doctor's "
            "capability list for gate-r1-g16 ('exit 3 means a human risk decision is "
            "outstanding'); this issue observed exit 3 with conditions "
            "['human_decision_required'] from check for a different reason, see "
            "date-ligature-025."),
        repro_cmd=CLEANROOM + "find . -name 'exit-code*' -not -path './upstream/*' | wc -l; "
                  "python3 tools/ligature/ligature.pyz --help 2>&1 | grep -ci 'exit code'; "
                  "find .ligature -type f | sort",
        exit_code=0,
        expected=(
            "docs/exit-code-contract.md is installed by init, or the binary's --help enumerates "
            "exit codes per command, so a worker can record a non-zero exit against something "
            "authoritative."),
        actual=(
            "0 files matching exit-code*; 2 lines in --help containing 'exit code', both inside "
            "gate-g20's prose; init installs only "
            ".ligature/schemas/consolidated-check.schema.json, "
            ".ligature/schemas/project-state.schema.json and the three stage prompts."),
        workaround=(
            "Record non-zero exits against check --json's own result object "
            "(result.exit_code plus result.conditions) and quote the process exit code "
            "alongside it; the exit-code table in "
            "analysis/ligature/stage-3-decisions.md section 8 is built that way and is this "
            "issue's own, not the tool's."),
        severity="friction",
        revisit_trigger=(
            "Every issue whose description says 'record every non-zero exit against the "
            "exit-code contract' -- that is #13, #14, #16 and every P2/P3 stage issue, so the "
            "same gap will be re-encountered five more times."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-024",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="python3 tools/ligature/ligature.pyz draft 3 interaction-drafting <target> --var verifier_policy.default=kani ...",
        tool="ligature",
        chain="new",
        symptom=(
            "The interaction schema accepts creusot-deductive-check as a first-class "
            "assurance kind -- this is the first point in the whole P1 chain where the binary "
            "has accepted Creusot as an evidence producer at all, and it answers part of probe "
            "#19. But verifier_policy.default has no influence on it whatsoever. With the "
            "scratch descriptor's verifier_policy.default flipped from creusot to kani, an "
            "interaction carrying edge_class ['cross-verifier', 'numeric-domain-boundary'] and "
            "accepted_evidence_kinds ['creusot-deductive-check'] still passes G1a/G1b "
            "unchanged at exit 0, and check is silent. So Creusot evidence is representable "
            "per-edge and is never reconciled with the declared default verifier anywhere the "
            "binary can see. The enum is closed and diagnosed properly, which is worth "
            "recording as the positive half: \"'creusot-proof' is not one of ['kani-bounded-"
            "model-check', 'creusot-deductive-check', 'verus-deductive-check']\"."),
        repro_cmd=CLEANROOM + "T=rust/date-creusot-core/specs/_interactions/I-probe.json; sed "
                  "'s/I-year-month-day-to-days-to-weekday-weekday-from-days/I-probe/' "
                  "analysis/ligature/draft-responses/I-1.json > /tmp/b.json; cp "
                  "project-descriptor.json /tmp/pd.json; for v in creusot kani verus; do "
                  "python3 -c \"import json,sys;d=json.load(open('/tmp/pd.json'));"
                  "d['verifier_policy']['default']=sys.argv[1];open('project-descriptor.json',"
                  "'w').write(json.dumps(d,indent=2)+chr(10))\" $v; python3 "
                  "tools/ligature/ligature.pyz draft 3 interaction-drafting $T --var "
                  "interaction_id=I-probe --var caller_concept=YearMonthDay --var "
                  "caller_method=to_days --var callee_concept=Weekday --var "
                  "callee_method=weekday_from_days --var caller_spec=x --var callee_spec=x --var "
                  "target_triple=x86_64-unknown-linux-gnu --var prior_artifact=x --var finding=x "
                  "< /tmp/b.json 2>&1 | tail -1; done; cp /tmp/pd.json project-descriptor.json",
        exit_code=0,
        expected=(
            "An interaction that accepts creusot-deductive-check evidence on a cross-verifier "
            "edge is either rejected, or flagged, when verifier_policy.default names a "
            "different verifier -- otherwise the declared default is decorative."),
        actual=(
            "Identical 'OK: generated draft passes G1a/G1b immediate checks' at exit 0 for "
            "verifier_policy.default in {creusot, kani, verus}. The field is read by no Stage 3 "
            "path; per chainlink #75 no v1.0 command echoes the effective verifier policy back "
            "at all."),
        workaround=(
            "Do not rely on the tool to keep the declared verifier and the recorded evidence "
            "kinds consistent. Chain probe #19 (issue 19) must carry the reconciliation "
            "itself, and Stage 8C's G17 / gate-g14 is the only place the tool is expected to "
            "make the deductive-vs-bounded decision -- which is exactly what probe #23 is for."),
        severity="friction",
        revisit_trigger=(
            "Probe #19 and probe #23 (chainlink issues 19 and 23) both depend on this. Re-run "
            "after any release that threads verifier_policy.default into the interaction or "
            "promotion path."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-025",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="python3 tools/ligature/ligature.pyz approve <interaction>.json --reviewer chainlink-reviewer --reviewed-at 2026-09-25",
        tool="ligature",
        chain="new",
        symptom=(
            "Two unstated ordering facts about the human-approve checkpoint, both found by "
            "hitting them. (1) R2 makes the boundary contract a precondition of the "
            "interaction: approving a boundary-required interaction before any boundary "
            "contract for the same edge exists fails with \"[R2/error] ... eligibility is "
            "boundary-required but no boundary contract for this edge and no reviewed exemption "
            "covers interaction_id '...' (plan.md gate table section 12: R2 -- eligible I edge "
            "with no boundary and no reviewed exemption blocks promotion)\", exit 1. Neither "
            "stage-3-interaction-drafting.md nor check next mentions the ordering; check next "
            "still reported [refresh-c-static] throughout. Boundary contracts must therefore be "
            "promoted first, which is a real constraint on any agent driving the loop. (2) "
            "check exits 3 with conditions ['human_decision_required'] while any interaction "
            "draft is staged, because the interaction schema requires a review property that "
            "stage-3-interaction-drafting.md forbids the draft from carrying: one info-or-"
            "medium finding per staged draft, '[medium/human-decision-pending] G1a: "
            "...json.draft: review is a required property'. That is the tool's own way of "
            "saying a human decision is outstanding, and it is the only place exit 3 was "
            "observed in this issue."),
        repro_cmd=CLEANROOM + "python3 tools/ligature/ligature.pyz approve "
                  "rust/date-creusot-core/specs/_interactions/I-year-month-day-to-days-to-"
                  "weekday-weekday-from-days.json --reviewer chainlink-reviewer --reviewed-at "
                  "2026-09-25; echo \"exit=$?\"; python3 -c \"import json;p='rust/date-creusot-"
                  "core/specs/_interactions/I-year-month-day-to-days-to-year-month-day-from-"
                  "days.json';d=json.load(open(p));d.pop('review');open(p+'.draft','w').write("
                  "json.dumps(d,indent=2)+chr(10))\"; python3 tools/ligature/ligature.pyz check | "
                  "tail -3; echo \"check exit=$?\"",
        exit_code=3,
        expected=(
            "approve's R2 error is discoverable before the agent gets there, and a staged "
            "interaction draft is a visible, non-blocking intermediate state -- or, better, "
            "check next names the pending approval as a kind: human-decision action so the "
            "shipped skill's own step 3 ('stop and ask the human') can fire."),
        actual=(
            "R2 fires only at approve time, with no earlier signal, and check next never "
            "mentions approvals at all. Conversely a staged interaction draft does raise a "
            "human-decision-pending finding, but only as a side effect of the schema requiring "
            "review while the prompt forbids it -- and the finding is severity medium at gate "
            "G1a, not a first-class action_id."),
        workaround=(
            "Always draft and approve the boundary contract for an edge before its interaction, "
            "and never leave an interaction .draft in place: check exits 3 until every one is "
            "promoted. The driver in analysis/ligature/stage-0-3.sh follows that order and ends "
            "with check at exit 0 and 'human decisions pending: 0'."),
        severity="friction",
        revisit_trigger=(
            "P2 and P3 stage issues (#28, #44) drive the same two commands and will hit R2 in "
            "the same order. Re-run at #14, which is the first issue to consume these promoted "
            "artifacts."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-026",
        pilot="date-creusot",
        stage="phase-1-ligature-init",
        command="jq -c '.write_set.protected_roots' project-descriptor.json ; ls rust/date-creusot-core/specs/_boundaries/ rust/date-creusot-core/specs/_interactions/",
        tool="ligature",
        chain="new",
        symptom=(
            "The descriptor's hand-filled write_set.protected_roots contains 'rust/*/specs/**', "
            "which the tool's own layout makes impossible to honour: the sanctioned "
            "draft/approve path writes boundary contracts, interactions and every other "
            "recognized artifact type under <crate_dir>/specs/_boundaries/, "
            "/_interactions/, /_exemptions/, /_protocol_debt/, /_bridges/ and /_witnesses/, "
            "which approve's own error message enumerates. Chainlink #12 filled the descriptor "
            "by hand (there is no descriptor template to copy these patterns from, and init's "
            "template is not a valid state -- see date-ligature-008) and could not have "
            "detected the contradiction, because nothing consumes the write set "
            "(chainlink #76) and draft/approve are ahead of it in the graph. Net effect: the "
            "declared protected list forbids the only writes the pipeline is allowed to make."),
        repro_cmd=CLEANROOM + "jq -c '.write_set.protected_roots' project-descriptor.json | "
                  "tr ',' '\\n' | grep -n specs; ls rust/date-creusot-core/specs/_boundaries/ | "
                  "head -2; python3 tools/ligature/ligature.pyz approve evidence/E-1.json "
                  "--reviewer x --reviewed-at 2026-09-25 2>&1 | tr ' ' '\\n' | grep specs | "
                  "sort -u",
        exit_code=0,
        expected=(
            "protected_roots lists inputs and generated reports, not the directory the "
            "pipeline's own promoted artifacts live in."),
        actual=(
            "'rust/*/specs/**' is in the list, and eight promoted artifacts now sit under "
            "rust/date-creusot-core/specs/ because the tool put them there."),
        workaround=(
            "Treat 'rust/*/specs/**' as covering generated and gate-pinned files only, not the "
            "promoted artifact directories. The descriptor is deliberately NOT edited here: "
            "WORKER-CONTRACT section 3 forbids touching project-descriptor.json in this issue, "
            "and chainlink #76 already records that the field is unread, so the correction is "
            "documentation until someone with descriptor authority acts. Raised on chainlink "
            "#76 for the owner to apply."),
        severity="scope-cut",
        revisit_trigger=(
            "When the descriptor is next edited (chainlink #76's fix, or P2/P3 descriptor work), "
            "drop or narrow the 'rust/*/specs/**' entry to match the tool's canonical layout, "
            "which approve's error message is the authority for."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-027",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="python3 tools/ligature/ligature.pyz approve <target> --reviewer <any non-empty string>",
        tool="ligature",
        chain="new",
        symptom=(
            "The human-approve checkpoint is not enforceable by the tool. approve requires "
            "--reviewer, but the value is any non-empty string (chainlink #17 established this "
            "for the descriptor's review.reviewer; the same holds here) and nothing records or "
            "checks that a human performed a review. The shipped SKILL.md's hash-pinned "
            "authority region says 'Human approval remains human ... Never infer or synthesize "
            "an approval', and its loop step 3 says a kind: human-decision next_action means "
            "'stop and ask the human. Do not cross an approve/promote checkpoint on your own' "
            "-- but check next never emits a human-decision action for a pending approval "
            "(date-ligature-025), so an agent following the skill's loop has no signal telling "
            "it to stop, and nothing in the tool would notice if it did not. The only partial "
            "signal is indirect: a staged interaction draft makes check exit 3 "
            "human_decision_required, and that is a schema artifact, not a checkpoint. "
            "Consequence for this workspace: the eight review blocks in "
            "rust/date-creusot-core/specs/ were written by an unattended agent invocation of "
            "approve, under the reviewer name this workspace declares in "
            "project-descriptor.json (review.reviewer = chainlink-reviewer, the same name "
            "docs/reliance-policy.md uses in its change history), and a human has not yet "
            "ratified them."),
        repro_cmd="cd date-creusot && python3 tools/ligature/ligature.pyz check next; "
                  "python3 tools/ligature/ligature.pyz --help 2>&1 | sed -n '/Human approval "
                  "remains human/,+2p'; grep -c '\"reviewer\": \"chainlink-reviewer\"' "
                  "rust/date-creusot-core/specs/_boundaries/*.json "
                  "rust/date-creusot-core/specs/_interactions/*.json",
        exit_code=0,
        expected=(
            "check next emits an action_id of kind human-decision while any draft awaits "
            "approval, so the shipped skill's step 3 can fire, and approve records something that "
            "distinguishes a human sign-off from a scripted one."),
        actual=(
            "check next reports only [refresh-c-static]; the eight approve calls are "
            "indistinguishable from human ones in the artifacts; the review blocks carry only "
            "a free-text reviewer name and a date."),
        workaround=(
            "Declared rather than hidden: analysis/ligature/stage-3-decisions.md section 10 and "
            "the pilot README record that the review blocks were produced by an agent-run "
            "approve and await human ratification, and the pilot's declared reviewer name "
            "(chainlink-reviewer, from project-descriptor.json's review block and the reliance "
            "policy's change history) is the one used so the pipeline stays internally "
            "consistent. A reviewer who disagrees should re-approve or delete the eight "
            "review blocks; nothing else in the tree depends on them."),
        severity="friction",
        revisit_trigger=(
            "Before chainlink #14's accept-promotion, which will read those review blocks into a "
            "promotion receipt. Also a standing question for the ligature workspace owner "
            "alongside #78, #79 and #80."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-028",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="python3 tools/ligature/ligature.pyz draft 3 boundary-drafting <target> --var caller_concept=Date --var callee_concept=Weekday ...",
        tool="ligature",
        chain="C.5",
        symptom=(
            "Draft-time G1a/G1b checks only the *shape* of a constraint id, never its "
            "attribution. A boundary contract whose callee is Weekday accepts "
            "callee_guarantees ['Date.C1'] -- the wrong concept -- at exit 0, and "
            "reliances[].obligation_id is not cross-checked against the callee concept at all. "
            "The pattern the tool enforces is '^[A-Z][A-Za-z0-9]*\\.[A-Z][0-9]+$' (rejected "
            "value quoted verbatim: \"'A-weekday-from-days-overshoot' does not match "
            "'^[A-Z][A-Za-z0-9]*\\\\.[A-Z][0-9]+$'\"), so any well-formed id passes. Two "
            "related non-enforcements at the same gate, both needed by chainlink #14 to know "
            "what it must still check: the reliance policy states 'G2+ (role safety, plan.md "
            "section 12) enforces the third row mechanically: an adversary-case id inside "
            "callee_guarantees is a hard error', but 'Weekday.A1' passes draft at exit 0 (the "
            "prompt attributes that check to scripts/validate_boundary_contracts.py, i.e. Stage "
            "4, so this is a note for #14 to confirm validate rejects it, not a defect claim); "
            "and interactions[].evidence_links is not checked for existence -- E-999 passes."),
        repro_cmd=CLEANROOM + "B=rust/date-creusot-core/specs/_boundaries/year_month_day_to_days"
                  "__to__weekday_weekday_from_days.json; for g in 'Weekday.C1' 'Date.C1' "
                  "'Weekday.A1' 'A-bad'; do python3 -c \"import json,sys;d={'schema_version':"
                  "'1.0','boundary_id':'year_month_day_to_days__to__weekday_weekday_from_days',"
                  "'caller':{'concept':'YearMonthDay','method':'to_days'},'callee':{'concept':"
                  "'Weekday','method':'weekday_from_days'},'callee_guarantees':[sys.argv[1]]};"
                  "print(json.dumps(d))\" \"$g\" | python3 tools/ligature/ligature.pyz draft 3 "
                  "boundary-drafting $B --var caller_concept=YearMonthDay --var "
                  "caller_method=to_days --var callee_concept=Weekday --var "
                  "callee_method=weekday_from_days --var "
                  "caller_concept_snake=year_month_day --var callee_concept_snake=weekday --var "
                  "caller_spec=x --var callee_spec=x --var reliance_policy=x --var "
                  "prior_artifact=x --var finding=x 2>&1 | tail -1 | cut -c1-60; rm -f $B.draft; "
                  "done; printf 'dangling evidence_links: '; sed "
                  "'s/I-year-month-day-to-days-to-weekday-weekday-from-days/I-probe/' "
                  "analysis/ligature/draft-responses/I-1.json | python3 -c \"import json,sys;"
                  "d=json.load(sys.stdin);d['evidence_links']=['E-999'];print(json.dumps(d))\" | "
                  "python3 tools/ligature/ligature.pyz draft 3 interaction-drafting "
                  "rust/date-creusot-core/specs/_interactions/I-probe.json --var "
                  "interaction_id=I-probe --var caller_concept=YearMonthDay --var "
                  "caller_method=to_days --var callee_concept=Weekday --var "
                  "callee_method=weekday_from_days --var caller_spec=x --var callee_spec=x --var "
                  "target_triple=x86_64-unknown-linux-gnu --var prior_artifact=x --var "
                  "finding=x 2>&1 | tail -1",
        exit_code=0,
        expected=(
            "A callee_guarantees id naming a different concept than the callee, and an "
            "evidence_links id with no evidence record behind it, are both rejected or "
            "flagged."),
        actual=(
            "'Date.C1' and 'Weekday.A1' both pass draft at exit 0; 'E-999' passes at exit 0. "
            "Only 'A-bad' is rejected, on the pattern. The one check that does exist -- the G2+ "
            "applies_to trace -- is permanently unverifiable (date-ligature-022), so nothing in "
            "the reachable command surface can tell a real id from an invented one."),
        workaround=(
            "Audit constraint ids by hand against analysis/ligature/constraint-ids.json, which "
            "gives statement, source file, line range and supporting evidence ids for each of "
            "the five ids this pilot cites. No A*-shaped id and no invented concept prefix is "
            "used in any artifact."),
        severity="friction",
        revisit_trigger=(
            "The chainlink #59 (C.5 dangling constraint ID) cross-cutting re-check, and before "
            "chainlink #14's accept-promotion."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
    dict(
        id="date-ligature-029",
        pilot="date-creusot",
        stage="stage-3-boundary-and-interaction-drafting",
        command="cat analysis/ligature/constraint-ids.json ; jq -r '.callee_guarantees[]' rust/date-creusot-core/specs/_boundaries/*.json",
        tool="ligature",
        chain="new",
        symptom=(
            "This pilot shipped 5 hand-declared constraint ids inside 4 promoted boundary "
            "contracts and 4 promoted interactions, overriding an explicit normative "
            "instruction in the installed stage prompts. stage-3-boundary-drafting.md:55-61 "
            "says 'If the callee spec has no constraint with a stable id field yet ... do not "
            "invent one and do not reference that constraint. Omit it from callee_guarantees "
            "rather than fabricate an id', and stage-3-interaction-drafting.md:126-141 says to "
            "omit the specific reliance and, if that would leave relies empty on a "
            "boundary-required edge, to 'output nothing' rather than 'emit an interaction with a "
            "fabricated id or an empty relies'. The 13 ids are declared in "
            "analysis/ligature/constraint-ids.json with statement, source file, line range and "
            "supporting evidence ids, and each is a line-for-line restatement of a named range "
            "in the pinned checkout, so they are not arbitrary -- but they are not "
            "tool-emitted, and the prompts say in so many words not to produce them. Overriding "
            "a normative prompt instruction is the workspace owner's call, not a worker's. "
            "Logged as an UNRATIFIED DEVIATION, not a decision. Compounded by two earlier "
            "findings: date-ligature-022 (#80) means the tool cannot verify any constraint id in "
            "any reachable command, and date-ligature-028 (C.5) means G1a/G1b check an id's "
            "shape and never its attribution -- so the reliance layer of the promoted specs is "
            "unverifiable by construction and the only verification that exists is a manual "
            "audit against constraint-ids.json. The chainlink reviewer rejected attempt 1 of "
            "issue #13 on exactly this point ('That trade-off is a human's call')."),
        repro_cmd="cd date-creusot && sed -n '55,61p' .ligature/prompts/"
                  "stage-3-boundary-drafting.md && sed -n '126,141p' .ligature/prompts/"
                  "stage-3-interaction-drafting.md && echo '--- ids declared by the pilot ---' "
                  "&& jq -r '.constraints[].id' analysis/ligature/constraint-ids.json | tr '\\n' "
                  "' ' && echo && echo '--- ids shipped inside promoted artifacts ---' && jq -r "
                  "'.callee_guarantees[]' rust/date-creusot-core/specs/_boundaries/*.json | sort "
                  "-u | tr '\\n' ' ' && echo && echo '--- the tool verifies none of them ---' && "
                  "python3 tools/ligature/ligature.pyz check 2>&1 | grep -c 'applies_to "
                  "unverifiable'",
        exit_code=0,
        expected=(
            "Either the stage-3 prompts are inapplicable because concept-to-code constraint "
            "ids do exist in v1.0, or a project supplies its own ids through a sanctioned, "
            "recorded mechanism (a descriptor field, or the reliance policy's change history "
            "with a policy-version bump) rather than by a worker overriding the prompt."),
        actual=(
            "The only producer of constraint ids (concept-to-code) has no verb in the CLI "
            "(chainlink #79), so the prompts' 'do not invent one' branch is the only branch "
            "available, and following it yields a vacuous reliance layer. This pilot took the "
            "other branch without authority. The deviation is now recorded and routed: both "
            "options and their exact commands are in analysis/ligature/stage-3-decisions.md "
            "section 3.1, and no human has ruled."),
        workaround=(
            "None applied unilaterally. The 8 artifacts are left in place, clearly marked "
            "unratified in stage-3-decisions.md sections 3 and 9 and in README.md, so the "
            "human can choose option A (accept as a recorded deviation: one change-history "
            "row plus a policy-version bump in docs/reliance-policy.md, artifacts stand) or "
            "option B (re-draft empty per the prompts: callee_guarantees [], delete the "
            "interactions outright since G2++ forbids an empty relies on a boundary-required "
            "edge, which reduces Stage 3 to 4 boundaries with no guarantees). Nothing else "
            "depends on the ids in the meantime."),
        severity="blocker",
        revisit_trigger=(
            "A human ruling on section 3.1, which gates chainlink #14: accept-promotion would "
            "otherwise launder an unratified reliance layer into a Stage 4.5 receipt. Also "
            "moot if chainlink #79 is fixed, since a concept-to-code verb would give the ids a "
            "producer and remove the need for the deviation entirely."),
        pyz_sha256=SHA,
        tool_path=PYZ,
        tool_version=VER,
    ),
]


def main() -> int:
    text = LEDGER.read_text() if LEDGER.exists() else ""
    existing = {json.loads(l)["id"] for l in text.splitlines() if l.strip()}
    added = [e for e in NEW if e["id"] not in existing]
    with LEDGER.open("a") as fh:
        for e in added:
            fh.write(json.dumps(e, sort_keys=False) + "\n")
    print(f"ledger: {len(existing)} existing, {len(added)} added, "
          f"{len(existing) + len(added)} total")
    for e in added:
        print("  +", e["id"], e["severity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
