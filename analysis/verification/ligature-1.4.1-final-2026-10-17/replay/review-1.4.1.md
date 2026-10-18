# Ligature 1.4.1 replay review (Chainlink #144)

Reviewed 2026-10-18 against the final attested bundle. This is an evidence overlay; it does not edit the append-only ledger or historical verdict tables.

## Identity and method

- Bundle SHA-256: `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`; source commit `742cb253e0cb9753c7a34a0c32559936130e03ab`; adjudicator `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`.
- All 96 replays ran through the existing harness on reset scratch copies. None was run against a live pilot. Raw command/stdout/stderr/exit captures are under `replay/out/<finding-id>.out`; each row links its capture.
- `CANDIDATE-*`, `probe_hit`, and exit equality were not treated as verdicts. Compound shell commands can return the last grep, echo, or wrapper status. Cases that do not reach their claimed behavior are marked not comparable.
- Historical first-96 ledger SHA-256: `d4ee406c118c8efa4c72f70cb75805f3c7d50eb545b9edcb6980f1dea7879ebd`; full live ledger SHA-256: `2199a067b77fe365bef3d93574456b524871d36572df64901ab8799aa07b0fa7` (102 rows). The ledger was read only; no rows changed.
- These 96 captures are scratch evidence. Live pilot checks are separate in the verification README and issue comments.

## 1.4.1 disposition counts

| Disposition | Count |
|---|---:|
| REPRODUCES | 5 |
| RESOLVED | 47 |
| PARTIAL | 4 |
| CHANGED | 3 |
| ENVIRONMENT-BLOCKED | 1 |
| NOT-COMPARABLE | 26 |
| SUPERSEDED | 3 |
| MATCH | 7 |
| **total** | **96** |

### Prior-table counts

| Bucket | 1.2.0 | 1.3.11 | 1.4.1 reviewed disposition |
|---|---:|---:|---:|
| STILL REPRODUCES / REPRODUCES | 23 | 13 | 5 |
| MATCH | 18 | 15 | 7 |
| RESOLVED | 25 | 36 | 47 |
| PARTLY RESOLVED / PARTIAL | 4 | 5 | 4 |
| SUPERSEDED | 3 | 3 | 3 |
| CHANGED | 3 | 3 | 3 |
| NOT-RUNNABLE | 4 | 5 | 0 |
| NOT-RUNNABLE(ENV) / ENVIRONMENT-BLOCKED | 15 | 16 | 1 |
| NOT-COMPARABLE (conservative category) | 0 | 0 | 26 |
| **total** | **95** | **96** | **96** |

The previous overlay’s 1.3.11 table and the current 1.4.1 replay both cover the first 96 historical finding IDs; 1.2.0 covered 95. The 1.4.1 counts are a reviewed overlay, not harness labels.

## All 96 reviewed dispositions

| Finding | Historical→captured exit | Disposition | Captured observation / review | Raw capture |
|---|---:|---|---|---|
| `date-mcp-001` | 1→1 | REPRODUCES | "error": "Symbol not found: include/date/date.h::days_from_civil#function",<br>[codesight] get-callers | [capture](replay/out/date-mcp-001.out) |
| `date-mcp-002` | 0→0 | REPRODUCES | "result_count": 0,<br>[codesight] get-imports | [capture](replay/out/date-mcp-002.out) |
| `date-ligature-001` | 0→0 | RESOLVED | {"artifacts":[{"artifact_id":"iso_week_weekday__to__weekday_iso_encoding","content_hash":"sha256:2d03a974415641242b305896719d7ae0403e0f042f455524433dcd91c75f328d","kind":"boundary"… | [capture](replay/out/date-ligature-001.out) |
| `date-ligature-002` | 0→0 | RESOLVED | {"artifacts":[{"artifact_id":"iso_week_weekday__to__weekday_iso_encoding","content_hash":null,"kind":"boundary","lifecycle":"absent","path":"rust/date-creusot-core/specs/_boundarie… | [capture](replay/out/date-ligature-002.out) |
| `date-ligature-003` | 2→0 | RESOLVED | {"artifacts":[{"artifact_id":"iso_week_weekday__to__weekday_iso_encoding","content_hash":"sha256:2d03a974415641242b305896719d7ae0403e0f042f455524433dcd91c75f328d","kind":"boundary"…<br>{"change_request_stubs":[],"findings":[{"authority":"mechanized-gate","dedup_key":"bf7c23b42a863afcfc39d561a17acaeb","gate_id":"g14","provenance":"scripts/gate_g14.py:gate_workspac… | [capture](replay/out/date-ligature-003.out) |
| `date-ligature-004` | 0→0 | NOT-COMPARABLE | The replay adds closure_kind to the current descriptor, which is valid. doctor exits 0 and check exits 1 for ordinary blocking findings; it does not recreate the historical invalid-descriptor condition. | [capture](replay/out/date-ligature-004.out) |
| `date-ligature-005` | 0→0 | RESOLVED | {"change_request_stubs":[],"findings":[{"authority":"mechanized-gate","dedup_key":"bf7c23b42a863afcfc39d561a17acaeb","gate_id":"g14","provenance":"scripts/gate_g14.py:gate_workspac… | [capture](replay/out/date-ligature-005.out) |
| `date-ligature-006` | 0→0 | RESOLVED | Installation:<br>installation: conflict | [capture](replay/out/date-ligature-006.out) |
| `date-ligature-007` | 0→0 | RESOLVED | installation_manifest.state = drifted<br>gate_integrity = {'details': '.codex/skills/ligature/SKILL.md: hash drift', 'state': 'drifted'} | [capture](replay/out/date-ligature-007.out) |
| `date-ligature-008` | 1→0 | RESOLVED | Fresh init exposes a pending P0 human_decision for project-descriptor.json in status output; check still exits 1 for unrelated setup findings and shipped example values. | [capture](replay/out/date-ligature-008.out) |
| `date-ligature-009` | 0→0 | PARTIAL | {"change_request_stubs":[],"findings":[{"authority":"mechanized-gate","dedup_key":"588c71a2865c16d36e5ef866a0d09991","gate_id":"P0","provenance":"scripts/project_descriptor.py:desc…<br>check exit=5 | [capture](replay/out/date-ligature-009.out) |
| `date-ligature-010` | 2→0 | RESOLVED | gate integrity: unknown -- project descriptor is present but invalid: $.verifier_policy.default: 'creusot-rust' is not one of ['kani', 'creusot', 'verus']<br>{"change_request_stubs":[],"findings":[{"authority":"mechanized-gate","dedup_key":"276450a52f705068a9c200badce7f4ec","gate_id":"G2+","provenance":"scripts/validate_boundary_contrac… | [capture](replay/out/date-ligature-010.out) |
| `date-ligature-011` | 0→0 | RESOLVED | descriptor {'closure_kind': None, 'mode': None, 'path': 'project-descriptor.json', 'schema_version': None, 'state': 'present-invalid', 'verifier_policy': None} | [capture](replay/out/date-ligature-011.out) |
| `date-ligature-012` | 0→0 | RESOLVED | descriptor {'closure_kind': None, 'mode': None, 'path': 'project-descriptor.json', 'schema_version': None, 'state': 'present-invalid', 'verifier_policy': None}<br>check exit=5 | [capture](replay/out/date-ligature-012.out) |
| `date-ligature-013` | 0→0 | RESOLVED | {'conditions': ['blocking_findings'], 'exit_code': 1} [{'authority': 'mechanized-gate', 'dedup_key': 'bf7c23b42a863afcfc39d561a17acaeb', 'gate_id': 'g14', 'provenance': 'scripts/ga…<br>{'closure_kind': None, 'mode': 'port', 'path': 'project-descriptor.json', 'schema_version': '1.0', 'state': 'present-valid', 'verifier_policy': {'clusters': {}, 'default': 'creusot… | [capture](replay/out/date-ligature-013.out) |
| `date-ligature-014` | 0→0 | RESOLVED | check {'conditions': ['blocking_findings', 'gate_integrity_failed'], 'exit_code': 5} [{'authority': 'mechanized-gate', 'dedup_key': 'bf7c23b42a863afcfc39d561a17acaeb', 'gate_id': '… | [capture](replay/out/date-ligature-014.out) |
| `date-ligature-015` | 0→0 | RESOLVED | Implemented: draft (Stage 0/3), approve (checkpoint), approve-pair (transactional interaction + protocol-debt checkpoint), approve-exemption-pair (transactional interaction + exemp…<br>check {'conditions': ['blocking_findings'], 'exit_code': 1} [{'authority': 'mechanized-gate', 'dedup_key': 'b52b6a94f99f92af658ed1f0f20f0d91', 'gate_id': 'g14', 'provenance': 'scri… | [capture](replay/out/date-ligature-015.out) |
| `date-ligature-016` | 0→0 | RESOLVED | check {'conditions': ['blocking_findings'], 'exit_code': 1} [{'authority': 'mechanized-gate', 'dedup_key': 'c4b0eddc44f4c5074683522c3e6777b4', 'gate_id': 'P0', 'provenance': 'scrip… | [capture](replay/out/date-ligature-016.out) |
| `date-ligature-017` | 2→0 | RESOLVED | manual check exit=1<br>claude check exit=1 | [capture](replay/out/date-ligature-017.out) |
| `date-ligature-018` | 0→0 | RESOLVED | The current Stage 3 prompt names docs/reliance-policy.md; the captured docs listing contains that file and no reliance-policy.template.md. | [capture](replay/out/date-ligature-018.out) |
| `date-ligature-019` | 1→0 | RESOLVED | The scratch draft rejects rust/date-creusot-core/rogue/evil.rs as outside the allowed target scope; the old in-crate escape is not reproduced. | [capture](replay/out/date-ligature-019.out) |
| `date-ligature-020` | 1→0 | NOT-COMPARABLE | The repaired compound command reports draft exit 1 and validate-evidence exit 0, but never invokes promote-evidence; this capture does not test the missing-promotion-path claim. | [capture](replay/out/date-ligature-020.out) |
| `date-ligature-021` | 1→0 | RESOLVED | bridge-drafting exit=1 error: template prompts/stage-3-bridge-drafting.md reference<br>witness-drafting exit=1 error: template prompts/stage-3-witness-drafting.md referenc | [capture](replay/out/date-ligature-021.out) |
| `date-ligature-022` | 0→0 | NOT-COMPARABLE | This capture lists current status and help references but does not run the historical boundary-contract validation that triggered applies_to unverifiable. | [capture](replay/out/date-ligature-022.out) |
| `date-ligature-023` | 0→0 | REPRODUCES | 0<br>2 | [capture](replay/out/date-ligature-023.out) |
| `date-ligature-024` | 0→0 | PARTIAL | Draft reports immediate G1a/G1b success, then the captured G2-policy diagnostic rejects reliance that omits owning-verifier evidence kind. The early draft acceptance still occurs; later validation catches the mismatch. | [capture](replay/out/date-ligature-024.out) |
| `date-ligature-025` | 3→0 | RESOLVED | exit=1<br>run: ligature draft interaction ci/results/c_static/rust_date-creusot-core.json | [capture](replay/out/date-ligature-025.out) |
| `date-ligature-026` | 0→0 | RESOLVED | 1:["rust/*/specs/**"<br>iso_week_weekday__to__weekday_iso_encoding.json | [capture](replay/out/date-ligature-026.out) |
| `date-ligature-027` | 0→0 | NOT-COMPARABLE | check next still says author-interaction, but this replay does not establish a pending human approval checkpoint; the reviewer grep on promoted specs is not a pending-draft probe. | [capture](replay/out/date-ligature-027.out) |
| `date-ligature-028` | 0→0 | PARTIAL | - [G1b/error] rust/date-creusot-core/specs/_boundaries/y<br>- [G1b/error] rust/date-creusot-core/specs/_boundaries/y | [capture](replay/out/date-ligature-028.out) |
| `date-ligature-029` | 0→1 | NOT-COMPARABLE | The compound shell command exits 1 with no captured stdout/stderr for its final grep; it does not establish whether the six historical applies_to IDs are validated. | [capture](replay/out/date-ligature-029.out) |
| `date-ligature-030` | 1→0 | RESOLVED | error: manifest not found: /tmp/nonexistent-wp.json<br>error: receipt not found: /tmp/nonexistent-promo.json | [capture](replay/out/date-ligature-030.out) |
| `date-ligature-031` | 0→1 | NOT-COMPARABLE | Capture only counts reviewer strings and runs a README grep; no accept-promotion command is run. | [capture](replay/out/date-ligature-031.out) |
| `date-ligature-032` | 1→0 | CHANGED | Current help/output lists the plan-driven generate-work-package command. The prior doctor message concerns automatic promoted-I/O generation; the capture does not show that message being corrected. | [capture](replay/out/date-ligature-032.out) |
| `date-ligature-033` | 1→1 | RESOLVED | witness_renderer.py<br>xml_escape.py | [capture](replay/out/date-ligature-033.out) |
| `date-ligature-034` | 1→0 | RESOLVED | "write_set": {<br>"allowed_roots": [ | [capture](replay/out/date-ligature-034.out) |
| `date-creusot-001` | 1→0 | RESOLVED | Scratch Creusot run after the documented civil_from_days source correction prints Proved (93 files); this is port-source resolution, not a Ligature release effect. | [capture](replay/out/date-creusot-001.out) |
| `date-creusot-035` | 1→1 | NOT-COMPARABLE | The command pipes cargo creusot through grep and captures no filtered output; pipeline exit 1 could mean no matching proof messages or an earlier failure, so it is not interpreted as a proof failure. | [capture](replay/out/date-creusot-035.out) |
| `date-creusot-036` | 1→1 | NOT-COMPARABLE | The command pipes cargo creusot through grep and captures no filtered output; pipeline exit 1 could mean no matching proof messages or an earlier failure, so it is not interpreted as a proof failure. | [capture](replay/out/date-creusot-036.out) |
| `date-creusot-037` | 1→1 | NOT-COMPARABLE | The command pipes cargo creusot through grep and captures no filtered output; pipeline exit 1 could mean no matching proof messages or an earlier failure, so it is not interpreted as a proof failure. | [capture](replay/out/date-creusot-037.out) |
| `date-creusot-038` | 1→0 | RESOLVED | The corrected scratch verification ends with Proved (93 files); the original failed VC is no longer observed in this tree. | [capture](replay/out/date-creusot-038.out) |
| `date-creusot-039` | 1→0 | RESOLVED | The corrected scratch verification ends with Proved (93 files); the original failed VC is no longer observed in this tree. | [capture](replay/out/date-creusot-039.out) |
| `date-creusot-040` | 0→0 | CHANGED | The captured help invocation completes successfully and returns Creusot help; one fast run does not falsify the earlier intermittent rebuild slowdown. | [capture](replay/out/date-creusot-040.out) |
| `date-creusot-041` | 0→0 | RESOLVED | Current scratch verifier run completes with Proved (93 files). | [capture](replay/out/date-creusot-041.out) |
| `date-ligature-035` | 0→0 | NOT-COMPARABLE | Only validate-evidence on the existing 15 records is run; this capture does not draft a compile-time evidence record or test its allowed kind. | [capture](replay/out/date-ligature-035.out) |
| `date-ligature-036` | 1→0 | SUPERSEDED | Current scratch R1/G16 output reports accepted reconciliation at 11 discovered / 11 checked; the older staged-interaction blocker is no longer the current gate state. | [capture](replay/out/date-ligature-036.out) |
| `date-creusot-042` | 0→0 | RESOLVED | Refreshed C_static report is 11 discovered / 11 resolved / 0 unresolved and current gate accepts 11/11. | [capture](replay/out/date-creusot-042.out) |
| `date-creusot-043` | 0→0 | REPRODUCES | Gate accepts 11/11 but emits R1 informational findings that two declared interactions have no realized call in this observation; the edge-realization concern remains, without blocking acceptance. | [capture](replay/out/date-creusot-043.out) |
| `date-ligature-037` | 1→2 | NOT-COMPARABLE | Repro contains a literal placeholder path instead of an artifact; current exit 2 is not evidence about a valid approve target. | [capture](replay/out/date-ligature-037.out) |
| `date-ligature-038` | 0→0 | SUPERSEDED | Current scratch R1/G16 output reports accepted reconciliation at 11 discovered / 11 checked; the older staged-interaction blocker is no longer the current gate state. | [capture](replay/out/date-ligature-038.out) |
| `date-creusot-044` | 1→0 | RESOLVED | Captured nextest summary reports 143 tests run, 143 passed, 0 skipped. | [capture](replay/out/date-creusot-044.out) |
| `date-creusot-045` | 2→2 | MATCH | /tmp/neg.jsonl:1: unknown case field: extra | [capture](replay/out/date-creusot-045.out) |
| `date-ligature-039` | 1→0 | RESOLVED | - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on decla…<br>OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record | [capture](replay/out/date-ligature-039.out) |
| `date-ligature-040` | 2→0 | PARTIAL | Local schema JSON paths are absent, while the bundled draft help exposes closure/degradation authoring templates; the sanctioned authoring route exists but direct schema inspection remains unavailable. | [capture](replay/out/date-ligature-040.out) |
| `date-ligature-041` | 2→0 | RESOLVED | deductive OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (1 discovered)<br>bounded OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (1 discovered) | [capture](replay/out/date-ligature-041.out) |
| `date-ligature-042` | 1→1 | RESOLVED | Current capture has the canonical WP-DATE-CREUSOT manifest and G14 derives closure from its artifacts; it does not report the old filename mismatch or declaration-trust defect. | [capture](replay/out/date-ligature-042.out) |
| `date-ligature-043` | 1→1 | RESOLVED | Current capture has the canonical WP-DATE-CREUSOT manifest and G14 derives closure from its artifacts; it does not report the old filename mismatch or declaration-trust defect. | [capture](replay/out/date-ligature-043.out) |
| `date-ligature-044` | 0→2 | NOT-COMPARABLE | Repro calls /tmp/opencode/rerverify_v4.py, which is absent; exit 2 is a missing scratch script, not a Ligature result. | [capture](replay/out/date-ligature-044.out) |
| `date-ligature-045` | 1→0 | RESOLVED | G14 reports the generic-callee condition as VERIFIED from artifact data and closes the 9-obligation scope; no old assurance/report blocking line appears. | [capture](replay/out/date-ligature-045.out) |
| `date-creusot-047` | 1→1 | NOT-COMPARABLE | Each capture filters cargo/Creusot output through grep and stores no matching lines; exit 1 is the pipeline result and does not distinguish a clean run from a verifier error. | [capture](replay/out/date-creusot-047.out) |
| `date-creusot-048` | 0→1 | NOT-COMPARABLE | Each capture filters cargo/Creusot output through grep and stores no matching lines; exit 1 is the pipeline result and does not distinguish a clean run from a verifier error. | [capture](replay/out/date-creusot-048.out) |
| `date-creusot-049` | 1→1 | NOT-COMPARABLE | Each capture filters cargo/Creusot output through grep and stores no matching lines; exit 1 is the pipeline result and does not distinguish a clean run from a verifier error. | [capture](replay/out/date-creusot-049.out) |
| `date-creusot-050` | 1→1 | NOT-COMPARABLE | Each capture filters cargo/Creusot output through grep and stores no matching lines; exit 1 is the pipeline result and does not distinguish a clean run from a verifier error. | [capture](replay/out/date-creusot-050.out) |
| `date-ligature-046` | 0→2 | NOT-COMPARABLE | The repro supplies literal ellipses or obsolete guarantee IDs (Weekday.C1/C2/C3, YearMonthDay.C2, YearMonthDayLast.C1); current exit 2 correctly says these are not provided guarantees and never tests the intended path. | [capture](replay/out/date-ligature-046.out) |
| `date-ligature-047` | 0→2 | NOT-COMPARABLE | The repro supplies literal ellipses or obsolete guarantee IDs (Weekday.C1/C2/C3, YearMonthDay.C2, YearMonthDayLast.C1); current exit 2 correctly says these are not provided guarantees and never tests the intended path. | [capture](replay/out/date-ligature-047.out) |
| `date-ligature-048` | 1→2 | NOT-COMPARABLE | The repro supplies literal ellipses or obsolete guarantee IDs (Weekday.C1/C2/C3, YearMonthDay.C2, YearMonthDayLast.C1); current exit 2 correctly says these are not provided guarantees and never tests the intended path. | [capture](replay/out/date-ligature-048.out) |
| `date-creusot-051` | 0→0 | RESOLVED | Fresh scratch Creusot run reports Proved (93 files). | [capture](replay/out/date-creusot-051.out) |
| `date-ligature-049` | 0→0 | RESOLVED | write-set-check lists four violations including both scratch probes under protected/out-of-set paths; shell echo makes the compound command exit 0, which is not a clean check. | [capture](replay/out/date-ligature-049.out) |
| `date-ligature-050` | 1→0 | RESOLVED | Current R1/G16 capture accepts complete 11/11 reconciliation; the old absent-from-I blocker is absent. | [capture](replay/out/date-ligature-050.out) |
| `date-creusot-052` | 0→0 | MATCH | - [G14/info] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on decla…<br>OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record | [capture](replay/out/date-creusot-052.out) |
| `date-ligature-051` | 1→0 | RESOLVED | Current date package emits assurance at ci/results/WP-DATE-CREUSOT.json while feature-ledger is ci/results/feature_ledger.json; the captured generation preserves separate outputs. | [capture](replay/out/date-ligature-051.out) |
| `date-ligature-052` | 0→0 | NOT-COMPARABLE | The compound probe's final echo exits 0 but does not capture a useful write-set finding for the generated test file; no conclusion is drawn from the wrapper status. | [capture](replay/out/date-ligature-052.out) |
| `date-ligature-053` | 0→0 | MATCH | 102 findings/limitations.jsonl<br>96 | [capture](replay/out/date-ligature-053.out) |
| `date-creusot-053` | 0→0 | MATCH | total 102<br>date-ligature-032 -> work-package.json | [capture](replay/out/date-creusot-053.out) |
| `date-ligature-054` | 1→0 | RESOLVED | Current report invocation succeeds with the distinct canonical report path and feature-ledger projection; the old shared-path collision is absent in this project state. | [capture](replay/out/date-ligature-054.out) |
| `date-ligature-055` | 1→0 | RESOLVED | Current report invocation succeeds with the distinct canonical report path and feature-ledger projection; the old shared-path collision is absent in this project state. | [capture](replay/out/date-ligature-055.out) |
| `date-ligature-056` | 0→0 | NOT-COMPARABLE | The report half succeeds, but the assurance half names obsolete guarantee IDs and exits 2; it does not test report preservation after a valid assurance run. | [capture](replay/out/date-ligature-056.out) |
| `date-ligature-057` | 1→1 | RESOLVED | Version and installation pin both read 1.4.1/current; check exits 1 only for project findings, not a half-migration state. | [capture](replay/out/date-ligature-057.out) |
| `date-creusot-054` | 2→0 | RESOLVED | The repaired harness runs the underlying entry from the project-relative location; its candidate result is tied to a separate obsolete -047 repro, not a cwd-routing failure. | [capture](replay/out/date-creusot-054.out) |
| `date-ligature-094` | 1→1 | NOT-COMPARABLE | The bridge draft is rejected for naming Weekday.C2 outside the boundary contract’s own callee_guarantees; the capture does not exercise the original empty-response/check-bridges crash. | [capture](replay/out/date-ligature-094.out) |
| `date-ligature-095` | 1→0 | RESOLVED | On scratch, concept spec draft passes immediate checks and approve reports the semantic spec promoted. | [capture](replay/out/date-ligature-095.out) |
| `date-ligature-096` | 0→0 | RESOLVED | Current draft help enumerates 11 templates, including the additional Stage 3 templates. | [capture](replay/out/date-ligature-096.out) |
| `date-ligature-097` | 1→1 | NOT-COMPARABLE | Witness approval is refused because the current concept spec lacks a weekday_number query; the prerequisite contract required for the old success-path claim is absent. | [capture](replay/out/date-ligature-097.out) |
| `date-ligature-098` | 0→0 | MATCH | status --json -> exit=0<br>check --json -> exit=1 | [capture](replay/out/date-ligature-098.out) |
| `date-ligature-099` | 0→1 | REPRODUCES | The current capture shows 15 SUPERSEDED markers and retains the 1.1.1 authoring section; this documents stale historical prose still present, not an active tool behavior defect. | [capture](replay/out/date-ligature-099.out) |
| `date-ligature-100` | 1→0 | RESOLVED | Interaction draft passes immediate checks and validate reports all 9 boundary contracts pass G1a/G1b/G2+. | [capture](replay/out/date-ligature-100.out) |
| `date-creusot-055` | 0→0 | NOT-COMPARABLE | The forged-evidence mutation aborts on KeyError obligation_records before completing its intended altered-record gate assertion. | [capture](replay/out/date-creusot-055.out) |
| `date-creusot-056` | 0→1 | CHANGED | The base probe still prints CG3 VERIFIED; the follow-up synthetic Kani artifact leg aborts because /tmp/opencode/p22/pristine is missing, so only that base observation is retained. | [capture](replay/out/date-creusot-056.out) |
| `date-creusot-057` | 0→0 | MATCH | The synthetic Kani/Creusot mismatch is rejected by G14 with verifier, harness, scope, and evidence-kind disagreements; the mutated scratch record is not accepted. | [capture](replay/out/date-creusot-057.out) |
| `date-creusot-058` | 1→0 | SUPERSEDED | The prior depends_on typo was corrected by the later project change; current G14 closes nine declared obligations. | [capture](replay/out/date-creusot-058.out) |
| `date-creusot-059` | 0→0 | RESOLVED | Current proof run reports Proved (93 files), including the previously tracked round_trip proof concern in this source snapshot. | [capture](replay/out/date-creusot-059.out) |
| `date-creusot-060` | 1→1 | ENVIRONMENT-BLOCKED | Nix realization reaches the recorded CoCoALib patch fetch and receives HTTP 404; it is the current environment blocker and does not establish the separate cvc5 URL claim. | [capture](replay/out/date-creusot-060.out) |
| `date-ligature-101` | 1→1 | RESOLVED | Approving absent staged drafts prints “nothing was promoted” and instructs the caller to stage a draft; no traceback is captured. | [capture](replay/out/date-ligature-101.out) |
| `date-ligature-102` | 0→0 | MATCH | The harness cwd pattern checks pass, but the delegated -047 command is itself non-comparable because it uses stale IDs. | [capture](replay/out/date-ligature-102.out) |
| `date-creusot-061` | 0→1 | NOT-COMPARABLE | The repro changes into a missing /tmp/opencode/104/dc directory; it does not evaluate the write-set comparison. | [capture](replay/out/date-creusot-061.out) |
| `date-creusot-062` | 0→0 | NOT-COMPARABLE | The scratch script starts with prose parsed as a shell command (RUN not found), then runs without the intended workspace; narrowed_exit=127/wide_exit=1 are harness errors. | [capture](replay/out/date-creusot-062.out) |

## The 39 changed exits, reviewed individually

These differences are not counted as behavior changes unless the capture supports that conclusion. Pipeline statuses that do not reveal the underlying command result are explicitly inconclusive in the main table.

| Finding | Historical→captured exit | What the capture establishes |
|---|---:|---|
| `date-ligature-003` | 2→0 | Scratch status accepts top-level closure_kind=deductive; command behavior changed to success. |
| `date-ligature-008` | 1→0 | Init now exposes the pending P0 human decision; check still fails for unrelated setup/example findings. |
| `date-ligature-010` | 2→0 | Invalid verifier is rendered as a descriptor validation finding; the pipeline final wrapper is successful. |
| `date-ligature-017` | 2→0 | Malformed values are rejected with diagnostics; compound loop ends with its explicit echo, so exit 0 is not acceptance. |
| `date-ligature-019` | 1→0 | Rogue scratch target is rejected as outside scope; the last loop iteration controls shell exit. |
| `date-ligature-020` | 1→0 | Draft half exits 1 but promotion is never invoked; later validate-evidence passes existing records. |
| `date-ligature-021` | 1→0 | All 11 templates are enumerated; render attempts fail for missing variables, not missing template support. |
| `date-ligature-025` | 3→0 | Missing draft now yields “nothing was promoted”; final check succeeds, masking the earlier command status. |
| `date-ligature-029` | 0→1 | Final grep has no match and exits 1; compound probe does not establish the historical validation claim. |
| `date-ligature-030` | 1→0 | Missing manifest/receipt now produce explicit diagnostics; shell echo leaves overall exit 0. |
| `date-ligature-031` | 0→1 | Only reviewer-count/README grep runs; it does not exercise accept-promotion. |
| `date-ligature-032` | 1→0 | Plan-driven generate-work-package is present; old doctor wording about automatic generation remains a separate change. |
| `date-ligature-034` | 1→0 | No overlaps are printed and work-package validation no longer reports the old overlap. |
| `date-creusot-001` | 1→0 | Corrected scratch project runs Creusot and prints “Proved (93 files)”. |
| `date-creusot-038` | 1→0 | Corrected scratch verification prints “Proved (93 files)”. |
| `date-creusot-039` | 1→0 | Corrected scratch verification prints “Proved (93 files)”. |
| `date-ligature-036` | 1→0 | Current R1/G16 accepts 11/11; old staged-interaction blocker is superseded by reconciled project state. |
| `date-ligature-037` | 1→2 | Literal placeholder target is invalid; exit 2 is not evidence of the old crash. |
| `date-creusot-044` | 1→0 | Current nextest capture reports all 143 tests passed. |
| `date-ligature-039` | 1→0 | G14 closes deductively with 9 provided/evaluated obligations and expected scope 9. |
| `date-ligature-040` | 2→0 | Schema docs remain absent but authoring templates are present; partial result, not command failure. |
| `date-ligature-041` | 2→0 | Current closure validation accepts partial; invalid degraded value remains rejected. |
| `date-ligature-044` | 0→2 | The session-local rerverify script is absent; exit 2 is not a behavior result. |
| `date-ligature-045` | 1→0 | G14 closes nine obligations and reports CG3 verified from artifact data; old blocker line is absent. |
| `date-creusot-048` | 0→1 | Cargo output is piped through grep and no matching text is captured; exit 1 is ambiguous. |
| `date-ligature-046` | 0→2 | Literal ellipsis proof paths are rejected; not comparable to a valid assurance run. |
| `date-ligature-047` | 0→2 | Obsolete Weekday.C1 is not a provided guarantee; no report-path behavior is tested. |
| `date-ligature-048` | 1→2 | The repro supplies literal ellipses or obsolete guarantee IDs (Weekday.C1/C2/C3, YearMonthDay.C2, YearMonthDayLast.C1); current exit 2 correctly says these are not provided guarantees and never tests the intended path. |
| `date-ligature-050` | 1→0 | R1/G16 current state accepts all 11 discovered calls. |
| `date-ligature-051` | 1→0 | Assurance report and feature-ledger are emitted to distinct paths in current project configuration. |
| `date-ligature-054` | 1→0 | Current gate closes with a distinct canonical report output; old refusal is no longer needed. |
| `date-ligature-055` | 1→0 | Feature-ledger generation succeeds alongside the canonical assurance path; no collision is observed. |
| `date-creusot-054` | 2→0 | Harness executes through; delegated repro is non-comparable for stale guarantee IDs. |
| `date-ligature-095` | 1→0 | Concept spec approval succeeds on scratch and prints the promoted target. |
| `date-ligature-099` | 0→1 | 15 superseded markers and stale 1.1.1 authoring prose remain; grep exit 1 reflects missing expected contract text. |
| `date-ligature-100` | 1→0 | Interaction draft and validation succeed; boundary contracts pass. |
| `date-creusot-056` | 0→1 | CG3 base leg still prints VERIFIED; synthetic leg aborts on missing /tmp/opencode/p22/pristine. |
| `date-creusot-058` | 1→0 | Current G14 closes nine obligations after the old dependency typo was corrected. |
| `date-creusot-061` | 0→1 | Missing session directory prevents the write-set comparison; not a Ligature result. |

## Remaining evidence-backed findings and caveats

- CodeSight findings `date-mcp-001` and `date-mcp-002` still reproduce in scratch: the requested C++ header symbol is missing, and reverse importer lookup returns `result_count: 0`.
- `date-ligature-004` is not comparable to the historical invalid-descriptor asymmetry: its current replay descriptor is valid, so doctor exit 0 and check exit 1 reflect different scopes and ordinary findings. `date-ligature-023` does reproduce a documentation gap: no installed per-command exit-code contract is found, while top-level help mentions exit-code behavior generically; tracked under upstream-local Chainlink #147. `date-ligature-027` is not comparable because the replay does not establish a pending approval checkpoint. `date-ligature-024` is partial: incompatible interaction drafts pass immediate checks, then G2-policy validation rejects the missing owning-verifier evidence kind. `date-creusot-043` still reports two declared interactions with no realized call as informational R1 findings.
- Stale documentation remains in the captured pilot README (`date-ligature-099`): 15 superseded markers and an old 1.1.1 authoring section. This is a documentation cleanup item, not evidence of active Ligature behavior.
- Creusot captures `date-creusot-001`, `-038`, `-039`, `-041`, `-051`, and `-059` report `Proved (93 files)` in scratch. This reflects the port-source correction present in the scratch tree, not a Ligature release effect. `-035`–`-037` and `-047`–`-050` use grep pipelines that hide the underlying verifier result; they remain not comparable.
- `date-creusot-060` is environment-blocked: Nix reaches a CoCoALib patch fetch and receives HTTP 404. It does not establish the separately reported cvc5 URL condition.
- Crypto-mixed `status --json` timeout is a separate live command-performance finding documented in `crypto-mixed-status-timeout.md`; it is not one of the 96 date-creusot scratch replays.

## Review limits

This review is limited to the exact 96 historical entries. It does not infer completeness from C_static lower-bound results, universal generic-callee coverage from bounded Kani evidence, or Ligature release causality from port-source edits in scratch. Historical ledger rows, raw replay outputs, and the old overlay are retained unchanged.

## Post-replay Nix evidence — 2026-10-18

The `date-creusot-060` capture is an environment-blocked result from the replay's older shell state: it reaches a CoCoALib patch fetch and receives HTTP 404. Later, local #142 records the approved Creusot 0.14 alignment and successful `cargo check --locked`, `cargo test --locked` (9 known-answer tests), and fresh `cargo creusot` with `Proved (93 files)` plus five proved Alt-Ergo children for the `round_trip` certificate. That successful #142 evidence supersedes the old CoCoALib environment blocker; it does not establish a cvc5 URL failure.

A new scratch rerun on 2026-10-18 attempted the pinned shell from the preserved flake snapshot. With the default Nix cache it exited 1 before entering the shell because `/home/goya/.cache/nix/fetcher-locks/` is read-only. With `XDG_CACHE_HOME=/tmp/date-creusot-nix-cache`, it again exited 1 before entering the shell because access to `/nix/var/nix/daemon-socket/socket` is not permitted. No proof ran in this rerun. Exact commands and raw output are under [`fresh-creusot-rerun-2026-10-18/`](../fresh-creusot-rerun-2026-10-18/). The original `date-creusot-060` disposition remains a faithful classification of its captured command, while the later #142 run is the current successful proof evidence.
