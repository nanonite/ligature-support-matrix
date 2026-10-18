# crypto-mixed: G9 harnesses vs write-set-check (2026-10-18)

Found during #134 verification after the Stage 7 manifests were regenerated.
All probes ran on a disposable `rsync -a` copy of `crypto-mixed/`. The bundle
was used as a black box (1.4.1, SHA-256
`973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`).

| Step | Command | Result | File |
|---|---|---|---|
| 1 | `write-set-check --json` with the existing `ci/harness/*.kani.rs` (untracked) | exit 1, violations: both `ci/harness/BR-CRYPTO-MIXED-00{1,2}.kani.rs` (out-of-set) | `wsc-1-as-copied.json` |
| 2 | remove `ci/harness/*.kani.rs`; `write-set-check --json` | exit 0, clean | `wsc-2-harness-removed.json` |
| 3 | `gate-g9` with no harness files | exit 1: `no generated harness at ci/harness/BR-CRYPTO-MIXED-00N.kani.rs -- run \`pipeline.py check-bridges\`` | `g9.out` |
| 4 | `check-bridges` | exit 0: writes both `ci/harness/*.kani.rs` and `ci/results/bridge_checks/*.json`; output is byte-identical to the live pilot's harness files | `check-bridges.out` |
| 5 | `write-set-check --json` | exit 1, the same two harness violations (the `bridge_checks` JSON is not flagged) | `wsc-4-after-check-bridges.json` |
| 6 | `gate-g9` | exit 0: all bridges pass G9 (2 discovered) | `g9b.out` |
| 7 | commit `ci/harness/` in the scratch git; `write-set-check --json` | exit 1, the same two violations | `wsc-5-harness-committed.json` |
| 8 | the same `write-set-check --json` with released 1.4.0 / 1.3.12 / 1.3.11 bundles | exit 1, the same two violations each | `wsc-old-*.json` |

Conclusion: `gate-g9` needs the files that `check-bridges` writes under
`ci/harness/`, and `write-set-check` reports exactly those files as out-of-set
violations. This happens whether or not they are git-tracked, and has been the
same since at least 1.3.11. A workspace cannot have G9 passing and a clean
write-set at the same time without changing the descriptor's `allowed_roots`,
which is protected policy. Also, the G9 diagnostic names `pipeline.py
check-bridges` rather than `ligature.pyz check-bridges`.

Earlier history: `swisstable-ligature-014` (1.2.x) recorded the opposite
symptom. `check-bridges` wrote `ci/harness/` and `write-set-check` reported
clean.

Live pilot handling: the two generated harness files stay untracked in
`crypto-mixed/ci/harness/`, so G9 keeps passing. `write-set-check` therefore
reports these two violations, and nothing else, until upstream resolves the
contradiction. No descriptor or policy was changed. Filed upstream; see local
issue #134.
