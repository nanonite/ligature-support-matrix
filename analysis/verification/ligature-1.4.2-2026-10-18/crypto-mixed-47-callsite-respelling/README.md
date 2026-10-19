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
  | bridge_003 (all usize lengths) | 0/25 failed |
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
