# Worker prompt: continue the Ligature port handoff

Work in `/home/goya/storage/full-ligature-port-workspace`. Continue project-local Chainlink issue **#144**, using the verified Ligature 1.4.1 evidence in:

`date-creusot/analysis/verification/ligature-1.4.1-final-2026-10-17/`

The goal is to finish the downstream review and handoff with evidence-backed dispositions, then work any genuinely remaining port findings. Track active work in Chainlink. Preserve the historical findings ledger and all assurance policy.

## Read first

1. Read `WORKER-CONTRACT.md`, `PROTECTED-WRITES.md`, the relevant section of the master plan named by the contract, and Chainlink #144.
2. Read the verification folder's `README.md`, `verification.json`, replay metadata, and `crypto-mixed-status-timeout.md`.
3. Read current local issues #134 and #135, including their latest comments. Their original descriptions predate the completed P3 work; use the later result comments as evidence, while checking the current pilot state before relying on them.

The contract's release-baseline paragraph is stale. Use this final verification as the current installation record: Ligature **1.4.1**, bundle SHA-256 `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`, source commit `742cb253e0cb9753c7a34a0c32559936130e03ab`, adjudicator hash `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`. Each pilot has its own verified copy. The contract's black-box, pilot-root, write-grant, and protected-policy rules still apply. Do not inspect the Ligature source checkout or unpack `ligature.pyz`.

This prompt is specifically for #144 and the outstanding crypto-mixed follow-ups; do not let an old global `chainlink issue next` result redirect this work to a historical issue. Confirm each issue's current dependencies before acting. Local #144 is the downstream handoff; upstream #143/#161 are different tracker references and do not exist under those numbers locally.

## Work plan

### 1. Reconcile the 96-finding replay

Review all 96 per-command captures under `replay/out/` against the corresponding historical entries in `findings/limitations.jsonl` and the original evidence. Pay particular attention to the **39 exit-code differences**. The existing `CANDIDATE-*` labels are only heuristics, not findings or verdicts.

For each entry, record a concise, evidence-backed disposition such as still reproduces, resolved in 1.4.1, changed behavior, environment-dependent, not comparable because of a documented scratch substitution, or not runnable. Explain the relevant output and whether the command ran live or in scratch. Do not infer resolution from an exit-code match alone, and do not infer a Ligature defect from an unrelated environment failure. Preserve the raw captures and the original 96 ledger rows byte-for-byte. Add review evidence only under an authorized analysis path; observe protected-write grants and allowed roots.

Use the final artifact identity above when identifying these replay results. Do not use or revive the withdrawn candidate audit under `closure-164-165-2026-10-17/` as release evidence.

### 2. Investigate the crypto-mixed status timeout

The final 1.4.1 `crypto-mixed status --json` capture timed out at 180 seconds, while checksum/version verification, migration, managed-resource hashes, and `doctor` passed. Treat this as a command-performance investigation, not an installation failure. Check the recorded command, pilot state, environment, and any comparable baseline evidence. If a safe, targeted reproduction is useful, capture it with a bounded timeout and exact binary identity. Create or update a project-local Chainlink issue if the timeout is a distinct actionable finding; avoid duplicates and preserve the captured evidence.

### 3. Reconcile open crypto-mixed issues #134 and #135

- **#134 / P3:** Verify the actual pilot's bounded Kani assurance records, bridge-only AEAD report, validation, G9, and G14 against the latest #134 result comment. Keep the claims within the exact harness bounds. Do not imply arbitrary-input, RFC-wide, or type-universal coverage. Assess #134 against its acceptance criteria and current dependencies; close it only if those criteria are actually met, otherwise state the precise remaining gap.
- **#135 / P4:** Inventory the generic callees and the exact source hashes relevant to CG3. Determine whether accepted Verus evidence can establish the required type-universal/deductive coverage. If it cannot, document the evidence and present the exact human decision needed. Do not relabel bounded Kani results, change protected manifests/closure policy, remove CG3, or weaken assurance rules without the required human review.

### 4. File and work remaining port findings

After verifying the 1.4.1 installation and replay evidence, review the historical ledger and current Chainlink issues for distinct unresolved port findings. Create project-local issues only for findings that remain actionable and are not already represented; link each to its original finding ID and exact evidence. Do not recreate closed local issues #136–#143 or conflate upstream Ligature issues with project-local ones. Work the new issues only within the contract's pilot-root and write-grant rules. Use the black-box escalation path for a newly reproduced Ligature defect.

## Guardrails

- Do not edit or rewrite historical rows in `findings/limitations.jsonl`; append findings through the approved workflow.
- Do not modify protected manifests, descriptors, closure profiles, proof scopes, verifier policy, root flakes, or user-owned `PORT-GAPS.md` without the exact required human authorization and sanctioned write path.
- Do not treat scratch probes or candidate labels as live results. Label every new scratch reproduction clearly and preserve its inputs and outputs.
- Do not close #144, #134, or #135 merely because work was attempted. Close each only when its own acceptance criteria are satisfied. If an operator decision or external capability blocks completion, keep the issue open and state the precise decision/evidence needed.
- Do not commit at the workspace root; it is not a git repository.

## Completion report

Update Chainlink with exact commands, exit codes, binary hashes, evidence paths, and reviewed dispositions. Summarize: all 96 replay classifications (including each of the 39 changed exits), the status-timeout finding, #134/#135 outcomes, newly created or updated issue IDs, and any operator decisions still needed. Distinguish live pilot checks from scratch probes. Leave the verification artifacts and historical ledger auditable.
