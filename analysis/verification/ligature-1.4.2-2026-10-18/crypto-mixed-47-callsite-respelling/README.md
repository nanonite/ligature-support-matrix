# crypto-mixed #47: call-site resolution, Poly1305 fold, and Stage 3 re-entry (2026-10-19)

Ligature 1.4.2 (bundle SHA-256
`c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184`), black box.
Owner decisions (2026-10-19, in session): respell the unresolvable calls; fold
`Poly1305State` into `Poly1305`; add real callee obligations; stage drafts
for every undeclared edge now, including the edges hidden by upstream #170.

## 1. Respelling the four possible-dispatch sites

`source.diff`: `aead.rs:49/52/76` and `poly1305.rs:32` rewritten as
associated-path calls (`ChaCha20::bytes_remaining(&chacha)`,
`ChaCha20::apply_keystream(&mut chacha, ..)`, `Poly1305State::update(state,
input)`). Semantics unchanged. No risk tier was moved, and nothing generated
was hand-edited.

| Step | Result | File |
|---|---|---|
| `cargo fmt --check`, `cargo test --locked --offline` | exit 0 / exit 0 (the crate has no ordinary unit tests) | `cargo-fmt.out`, `cargo-test.out` |
| `extract-c-static` | 16 discovered / 16 resolved / 0 unresolved | `extract-c-static.out`, `c_static-before.json`, `c_static-after.json` |
| `validate-callsites` | exit 0 | `validate-callsites.out` |
| `gate-r1-g16 --json` | exit 1: 6 undeclared blocking R1 calls (3 known + 3 exposed by resolution) | `gate-r1-g16.json` |
| `write-set-check` (global and `--issue 47`) | exit 0 (after deleting a `target/` the agent's own `cargo test` had just created) | `write-set-check*.json` |
| `gate-g9` | exit 0 | `gate-g9.out` |
| `gate-g14 --json` | exit 1 only because the Kani records were bound to the old source; **no call-site finding remains** (previously 4 unresolved and G17 0 vs 4) | `gate-g14.json` |
| `record-assurance WP-CRYPTO-MIXED-PRIMITIVES-001 --kani-harness ...` x3 | exit 0; C002 646, C003 30, Poly1305.C002 724 proved goals; 127 s, 5.6 GB | `record-assurance-primitives.*` |
| `gate-g14 --json` again | overlapped the Poly1305 fold edit, so Poly1305.C002 reports a changed snapshot; both ChaCha20 records re-establish | `gate-g14-after-rerecord.*` |

## 2. Extractor defect found on the way (upstream #170, local #150)

`extract-c-static` skips every method whose return type is an array
(`-> [u8; 16]`), both as a caller and as a callee, without counting it. This
hides `ChaCha20Poly1305::tag → Poly1305::compute_tag_segments` (the real
AEAD→Poly1305 edge), the `self.tag(..)` calls, and all of `compute_tag*`.
A scratch copy with only the return types aliased gives the post-fix view:
31 discovered before the fold, and 35 / 35 / 0 after it, with 5 undeclared
edges. See `crypto-ligature-010`.

## 3. Poly1305 fold

`Poly1305State` (a private helper that the extractor treated as its own
concept) is folded into `Poly1305`: the accumulator fields live on
`Poly1305`, and the helpers (`keyed_with`, `load_key`, `absorb`,
`process_block`, `finish`) are private `Poly1305` methods called in
associated-path form. The arithmetic was copied verbatim. A differential
test of the old vs new implementation over 3000 random keys/messages (every
API path, including key-not-set and reuse after finalize) plus the pinned
Botan vector found no difference
(`scratchpad/poly-equiv`, not kept in the pilot). The live extraction is
18 / 18 / 0, with 4 undeclared edges (all ChaCha20); the Poly1305State edges
are gone.

## 4. Stage 3 re-entry (drafts staged for human approval)

See the #47 comment for the full list and the approval order. Summary:

- Concept-spec revisions: ChaCha20 `C004` (capacity after `with_counter`)
  and `C005` (`bytes_remaining` accounting); Poly1305 `C005` (segments tag =
  concatenation tag). Constructors and associated functions can't be listed
  as concept queries (G1a requires `&self`), so these constraints name
  `with_counter` / `compute_tag_segments` in `applies_to` only.
- 5 boundaries, interactions `I-CRYPTO-MIXED-004..008`, and bridge
  `BR-CRYPTO-MIXED-003` (C003 at the decrypt call site).
- New Kani harnesses in `src/kani_proofs.rs`:
  `kani_chacha20_c004_with_counter_stream_capacity`,
  `kani_chacha20_c005_bytes_remaining_tracks_consumption`,
  `kani_poly1305_c005_segments_match_concatenation`, and
  `bridge_003_limits_aead_ciphertext_to_the_counter_one_stream`. Kani 0.67
  (`cargo kani --harness kani_proofs::<name> --exact`, build output outside
  the pilot), results in `kani-*.out`:

  | Harness | Result |
  |---|---|
  | C004 (all u32 counters) | 0/26 failed |
  | C005, first form (symbolic counter and length) | timed out at 1500 s; rewritten |
  | C005 (8 concrete counter/length boundary cases plus a block-crossing pair) | 0/742 failed, 130 s, 2.9 GB |
  | Poly1305.C005 (7 concrete splits of the RFC vector) | 0/753 failed, 35 s |
  | bridge_003 (all usize lengths) | 0/25 failed (later folded into the C003 harness; see section 5) |
  | regression: `poly1305_matches_the_pinned_botan_self_test_vector` | 0/619 failed |
  | regression: `aead_matches_the_pinned_botan_vector` | 0/1489 failed, 170 s, 13.6 GB |

- All 13 drafts were staged in the live pilot with `draft 3 <template>` and
  the manual backend (response on stdin), via `run_47_drafts.py` and the
  responses in `draft-responses/` (generator: `make_47_drafts.py`); logs are in
  `draft-logs/`. Each passed its immediate checks, and `write-set-check
  --issue 47` and the standing validators still exit 0. Approval steps:
  `APPROVAL-RUNBOOK.md`.
- Unchanged and still open: I-CRYPTO-MIXED-001/003 (`encrypt → finalize /
  set_key`) are never realized in the Rust port (Botan structure). Retiring
  them affects BR-CRYPTO-MIXED-001 and both manifests, and is left for the
  owner after this round.

## 5. Approval, Stage 7 regeneration, and gates (2026-10-19)

The owner approved the 13 drafts, ruled on them (plus the closure profile),
and re-minted `PROM-CRYPTO-KANI-001` over 29 artifacts (`APPROVAL-RUNBOOK.md`).
The agent then added BR-CRYPTO-MIXED-003 to the fail-closed Kani bridge
adapter (`check-bridges-1/2.out`, `gate-g9-after.out`) and wrote the v2
Stage 7 plans (`stage7-plans-v2/`, issue 134: six obligations including
C004/C005/Poly1305.C005, plus BR-003).

| Step | Result | File (`stage7-plans-v2/`) |
|---|---|---|
| `generate-work-package --regenerate` PRIMITIVES (grant `GW-dd600ef187c2`) | exit 0, `445326e1…` → `6f28effc…`; diff = 3 new bindings, 2 functions, 6 provided obligations, receipt hash, base commit | `generate-PRIMITIVES.json`, `manifest-PRIMITIVES.diff` |
| same, AEAD (grant `GW-3a6e9f51d098`) | exit 0, `e309f9fb…` → `722d6521…`; diff = 3 new required obligations, BR-003, receipt hash, base commit | `generate-AEAD.json`, `manifest-AEAD.diff` |
| BR-003 scope mismatch | the manifest copied I-007's C003 scope (`kani_chacha20_c003…`, then encrypt-only) while the BR-003 record used `bridge_003…` | `../APPROVAL-RUNBOOK-I007.md` |
| round 2: I-007 re-scoped to `bridge_003…`, approved and promoted | both regenerations **refused** (exit 2, `contradictory-source`: C003 has conflicting required_assurance in I-002 and I-007); nothing written | `generate-*-round2.json`, `crypto-ligature-012` |
| round 3: C003 harness proves both AEAD length gates; BR-003 adapter uses it; I-007 restored to the round-1 content and re-approved | Kani 0/34 failed; `check-bridges` 0; `gate-g9` 0 (3 bridges) | `../kani-c003-folded.out`, `../check-bridges-3.out`, `../gate-g9-round3.out` |
| regenerate both (grants `GW-ae29e8b2cafa`, `GW-d85c40268320`) | exit 0, `unchanged` (the round-3 artifact set is byte-identical to round 1) | `generate-*-round3.json` |
| `validate-work-package` ×2, `validate-promotion`, `validate-closure` | exit 0 | `validate-*.out` |
| `record-assurance` PRIMITIVES, 6 bindings | exit 0, all `supported`: C002 646, C003 33, C004 25, C005 737, Poly1305.C002 844, Poly1305.C005 749 proved goals; 287 s, 4.7 GB | `record-assurance-primitives-round3.*` |
| `tests/record_bridge_only_report.py` (AEAD) | exit 0; 3 bridge records, all `pass` (stale 2-bridge report kept as `WP-CRYPTO-MIXED-AEAD-001.report-before.json`) | `record-bridge-only-report.out` |
| `extract-c-static` | 18 discovered / 18 resolved / 0 unresolved | `extract-c-static.out` |
| `validate-callsites` | exit 0 (exit 1 before re-extraction: stale binding after the harness edit) | `validate-callsites*.out` |
| `gate-r1-g16 --json` | exit 0, **accepted**: 18 checked, 0 undeclared, 0 unresolved, reconciliation complete | `gate-r1-g16.json` |
| `write-set-check --issue 134` / `--issue 47` | exit 0 / exit 0 | `write-set-check-*.json` |
| `gate-g14 --json` | exit 0; `crypto-kani` **bounded**, status `degraded` (CG3 per-instantiation ceiling, the accepted condition); 6 obligations + 3 bridges evaluated, 6 proof artifacts re-checked, 0 cycles; 346 s, 4.7 GB | `gate-g14.json` |

`bridge_003_limits_aead_ciphertext_to_the_counter_one_stream` was later
removed by the owner (section 6).

Still open after #47: I-CRYPTO-MIXED-001/003 are never realized in the Rust
port (section 4); I-CRYPTO-MIXED-008 reports intent without realization
until upstream #170 ships.

### Post-commit `check` and the feature configuration

`check` after the commit exited 0 but named I-CRYPTO-MIXED-004 as the next
action: every interaction declares `features=['default']`, while
`extract-c-static` had been run with no `--feature` (also the case for
I-002 before #47; `info` only). Re-extracted under the declared
configuration:

| Step | Result | File (`stage7-plans-v2/`) |
|---|---|---|
| `extract-c-static --target x86_64-unknown-linux-gnu --feature default` | 18 / 18 / 0 | `extract-c-static-feature-default.out` (previous report: `c_static-features-none.json`) |
| `validate-callsites`, `gate-r1-g16 --json` | exit 0 / exit 0, accepted, 0 configuration findings | `validate-callsites-feature-default.out`, `gate-r1-g16-feature-default.json` |
| `check` | exit 0; R1/G16, G9, G14 executed; G18-G20 not applicable (P3 has no witness specs); 23 findings (was 28), only medium = the accepted CG3 degradation; next action = I-CRYPTO-MIXED-001 intent without realization; 311 s, 4.7 GB | `check.out` |

Use `--feature default` for every future extraction in this pilot.

## 6. Close-out for #134 (2026-10-19/20)

Owner decisions: #152 (I-CRYPTO-MIXED-001/003 never realized) is
disregarded, so those interactions stay as info-level intent without
realization. #134 closes as the parent of #135, which was already resolved on
2026-10-18 by option B (accept the Kani per-instantiation CG3 ceiling).

- The reviewed degradation record named only BR-001/002 in `affected_edges`,
  although G14 applied it cluster-wide (the template notes nothing
  cross-references that list). Redrafted with BR-CRYPTO-MIXED-003 added
  (`degradation-br003/`); approved and ratified by the owner (crypto-mixed
  `b470139`). Ceiling, capability gap, and tracking issue unchanged.
- The owner removed the unused `bridge_003…` harness with
  `remove_bridge003.py` (exact-match, refuses unless the block occurs exactly
  once; `post-bridge003-removal/source.diff`, 11 lines deleted;
  `cargo fmt --check` exit 0). Every Kani and bridge record binds the
  `kani_proofs.rs` hash, so all were re-run:

| Step | Result | File (`post-bridge003-removal/`) |
|---|---|---|
| `extract-c-static --feature default`, `validate-callsites` | 18 / 18 / 0; exit 0 | `extract-c-static.out`, `validate-callsites.out` |
| `gate-r1-g16 --json` | accepted: 18 checked, 0 undeclared, 0 unresolved, 0 configuration mismatches | `gate-r1-g16.json` |
| `record-assurance` PRIMITIVES, 6 bindings | all supported (646 / 33 / 25 / 737 / 844 / 749 proved goals); 267 s, 4.7 GB | `record-assurance-primitives.*` |
| `check-bridges`, `gate-g9` | exit 0 / exit 0, 3 bridges | `check-bridges.out`, `gate-g9.out` |
| `tests/record_bridge_only_report.py` | exit 0, 3 passing bridge records | `record-bridge-only-report.out` |
| `check` | exit 0; 23 findings; only medium = CG3 "accepted as degradation under ceiling 'per-instantiation' (chainlink:135)" over BR-001/002/003 and the six obligations; next action = I-001 intent without realization (disregarded, #152); 304 s, 4.7 GB | `check.out` |
| `write-set-check --issue 134 --json` | exit 0 | `write-set-check-134.json` |
