# crypto-mixed Stage 8C (chainlink #49, 2026-10-20)

Stage 8C validates the implemented closure against the approved `crypto-kani`
closure profile (#44), runs the remaining gates and reports, and has a fresh
agent replay every finding in `findings/limitations.jsonl`. Ligature 1.4.2
(bundle `c4d989f3…`, `sha256sum -c` OK, attested). The pilot was at `6a55894`
for the gates and the replay.

## Gates and reports (`gates/`)

| Command | Exit | Result |
|---|---|---|
| `validate-closure` | 0 | All closure artifacts pass G1a/G1b and G17 profile/record consistency (2 discovered) |
| `gate-g14` / `--json` | 0 | `crypto-kani`, declared `closure_kind='bounded'`, does not fully close: it is released under the accepted `per-instantiation` degradation (chainlink #135) for `generic_callees_type_universal_or_creusot_owned`. 6/6 obligations and 3/3 bridge records evaluated; Ligature re-ran every named Kani harness. "OK: 0 cluster(s) close under their declared profile, 1 released under an accepted degradation record" |
| `gate-g18`, `gate-g19`, `gate-g20` | 0 | Nothing to check: no witness specs or `witness_required` features. An empty-input pass establishes nothing |
| `report pilot-cluster`, `select-pilot-cluster` | 1 | `crypto-kani` excluded: "sole verifier 'kani' is not a deductive verifier" |
| `report feature-ledger` | 0 | 0 declared features. Refreshed `assurance_results_hash`, stale since the 2026-10-13 baseline |
| `report contact-sheet` | 0 | Wrote `docs/witnesses/_contact_sheet.svg` (0 features) |
| `report gold-set-measurement` | 1 | No `specs/_gold_sets`; not part of this pilot |
| `check --json` (`gates/check-final.json`) | 0 | 23 findings: 22 info, plus the 1 medium accepted CG3 degradation. Unchanged from before #49 |
| `doctor`, `write-set-check --issue 49` | 0 | Clean |

G14's closure kind matches the declared `bounded`. Kani establishes generic
callees per monomorphization only, and that coverage ceiling was accepted in
#135, so P3's result is accepted bounded evidence with a recorded
degradation, not full closure.

An earlier `check` run exited 1 with 17 write-set findings on the files in
this directory. It started before the operator added `analysis/stage8c/**` to
`allowed_roots` (16:16:51) and scanned the new files later (16:17:08).
`write-set-check` and the settled `check` above are clean. This was a
sequencing mistake in the run, not a Ligature or write-set problem.

## Findings replay (`replay/`)

A fresh subagent, with none of this session's context, replayed all 31
findings. Each got its own `rsync` copy of the frozen baseline, and
historical states were rebuilt from git history and older bundles. No
human-checkpoint verb was run.

| Verdict | Count | Findings |
|---|---|---|
| REPRODUCED | 23 | |
| REPRODUCED-RESOLVED | 4 | crypto-mcp-001, crypto-ligature-008, crypto-ligature-011, crypto-oracle-002 |
| PARTIAL | 3 | crypto-rdb-001, crypto-rdb-002, crypto-oracle-003 |
| NOT-RUNNABLE(HUMAN) | 1 | crypto-ligature-012 (needs approve, record-ruling, accept-promotion and a grant; the workaround's shared harness scope and 0/34 failures were confirmed) |
| NOT-REPRODUCED, NOT-RUNNABLE(ENV/PROSE) | 0 | |

- The 1.3.x-1.4.1 Ligature defects crypto-ligature-002 to -007 reproduce in
  their historical states and are gone on 1.4.2.
- crypto-ligature-009 (no intake for evidence outside the verifier enum) and
  crypto-ligature-010 (array-return methods skipped by `extract-c-static`)
  are still present.
- `replay/findings-replay.md` has the per-finding commands, decisive output,
  and 32 ledger defects (mostly missing commit or bundle context, prose
  timeouts, and exit codes that belong to `command`, not `repro_cmd`).

### Corrections made from the replay

The three PARTIAL entries were recorded in #48 and are corrected in place:

- **crypto-rdb-001 and -002:** the original rdb script hard-codes
  `break 0x2111f0`, which is valid only for the original build path (clean
  rebuilds gave 0x211240, 0x211250 and 0x2111e0).
  `oracle/divergences/boundary-aead-output-length-encrypt-0003/replay.sh` now
  resolves the address with `nm` and checks the transcript, because rdb exits
  0 even when its commands fail. It printed `replay ok: breakpoint 0x2111e0`.
  The "stack randomized per run" claim is now environment-qualified.
- **crypto-oracle-003:** the prose repro is replaced by
  `repro/jsonvalue_incomplete_type.cpp`. clang++ `-std=c++20` gives 4 errors
  and exit 1; `-std=c++17` and g++ 14 `-std=c++20` both compile. The rejection
  is specific to clang with libstdc++. The 7 errors and exit 2 recorded before
  were the full driver's `cmake --build`.
- **crypto-rdb-001's `exit_code` 100:** this is nextest's exit code, kept
  because `rdb-divergence-workflow.md` section 5 asks the record to preserve
  the failing nextest command's code.

The other ledger defects are left as recorded and listed in the replay
report, following the P1/P2 practice of not rewriting older entries.

## New findings

- **crypto-ligature-014 (by design; the docs overstate it):**
  - What happens: `write-set-check` enforces `protected_roots` only in
    pipeline-owned locations (`ci/manifest/**`, crate `specs/**`). Writes to
    other declared protected roots such as `README.md`, `scripts/**`,
    `analysis/codesight/**`, or `oracle/**` before 69645d2 leave it "clean",
    listed only as audit-only `protected_unvouched`.
  - Operator view (2026-10-20): this is intended. Ligature is open-ended and
    enforces or suggests the pipeline's phases, not every root a project
    declares. Protecting other roots is project policy, enforced by review.
    No epic #1 escalation.
  - Follow-up for the workspace docs: `WORKER-CONTRACT.md` section 0 and
    `PROTECTED-WRITES.md` describe every ungranted protected write as
    blocking, which is more than the tool does. #90 was closed on a probe of
    pipeline-owned paths only.
- **crypto-ligature-015 (scope-cut):** a bounded, witness-free pilot gets no
  Stage 8C report beyond G14:
  - `pilot-cluster` is deductive-only;
  - G18-G20 pass on empty input;
  - the stale feature-ledger hash was never flagged by `check`.
