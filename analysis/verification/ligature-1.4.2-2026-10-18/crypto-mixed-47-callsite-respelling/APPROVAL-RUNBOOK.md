# crypto-mixed #47: human approval runbook (staged 2026-10-19)

Thirteen drafts are staged as `<target>.draft` in `crypto-mixed/`. Every
command below is a human checkpoint: run it yourself, from
`/home/goya/storage/full-ligature-port-workspace/crypto-mixed`, with your own
reviewer name. Order matters: `approve` checks each artifact against what is
already promoted (G2+/G2++/R2), so specs come first, then boundaries, then
interactions, then the bridge.

## 0. Read what you are approving

```sh
for f in crates/crypto-mixed-core/specs/cha_cha20.json crates/crypto-mixed-core/specs/poly1305.json; do
  diff <(python3 -m json.tool "$f") <(python3 -m json.tool "$f.draft"); done
for f in crates/crypto-mixed-core/specs/_boundaries/*.draft crates/crypto-mixed-core/specs/_interactions/*.draft crates/crypto-mixed-core/specs/_bridges/*.draft; do
  echo "=== $f"; cat "$f"; done
```

What to check:

| Draft | What it says | Backed by (Kani, all verified 2026-10-19) |
|---|---|---|
| ChaCha20 `C004` (applies_to `with_counter`) | a stream started at counter c has (2^32 − c)·64 bytes | `kani_chacha20_c004_with_counter_stream_capacity`: all u32 counters, 0/26 failed |
| ChaCha20 `C005` (applies_to `bytes_remaining`) | capacity drops by exactly the consumed length; unchanged on rejection | `kani_chacha20_c005_bytes_remaining_tracks_consumption`: 8 boundary cases + block-crossing pair, 0/742 failed |
| Poly1305 `C005` (applies_to `compute_tag_segments`) | segment tag = tag of concatenation | `kani_poly1305_c005_segments_match_concatenation`: 7 splits of the RFC vector, 0/753 failed |
| 5 boundaries | `encrypt`/`decrypt` → `with_counter` [C004]; `encrypt` → `bytes_remaining` [C005]; `decrypt` → `apply_keystream` [C002, C003]; `tag` → `compute_tag_segments` [Poly1305.C005] | |
| `I-CRYPTO-MIXED-004..008` | the same five edges, `boundary-required`, Kani-only reliances | |
| `BR-CRYPTO-MIXED-003` | decrypt's C002 length bound + fresh counter-one stream ⇒ ChaCha20.C003 at `apply_keystream` | `bridge_003_limits_aead_ciphertext_to_the_counter_one_stream`: 0/25 failed |

Judgment calls to look at: `with_counter` and `compute_tag_segments` can't be
concept queries (G1a admits only `&self` methods), so C004 and Poly1305.C005
name them only in `applies_to`. If `approve` rejects that as untraceable,
stop and tell the agent. Edge classes are `numeric-domain-boundary` (plus
`stateful` for the `with_counter` edges), following the template's "prefer
boundary-required when unsure". `I-CRYPTO-MIXED-008` declares the real
AEAD→Poly1305 edge, which R1 can't see until upstream #170 ships; until
then it reports as intent without realization (info).

## 1. Concept specs

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && for t in cha_cha20 poly1305; do python3 -I tools/ligature/ligature.pyz approve crates/crypto-mixed-core/specs/$t.json --reviewer roger-codex-luna6 || break; done
```

## 2. Boundaries

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && for b in cha_cha20_poly1305_encrypt__to__cha_cha20_with_counter cha_cha20_poly1305_encrypt__to__cha_cha20_bytes_remaining cha_cha20_poly1305_decrypt__to__cha_cha20_with_counter cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream cha_cha20_poly1305_tag__to__poly1305_compute_tag_segments; do python3 -I tools/ligature/ligature.pyz approve crates/crypto-mixed-core/specs/_boundaries/$b.json --reviewer roger-codex-luna6 || break; done
```

## 3. Interactions

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && for i in 004 005 006 007 008; do python3 -I tools/ligature/ligature.pyz approve crates/crypto-mixed-core/specs/_interactions/I-CRYPTO-MIXED-$i.json --reviewer roger-codex-luna6 || break; done
```

## 4. Bridge

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && python3 -I tools/ligature/ligature.pyz approve crates/crypto-mixed-core/specs/_bridges/BR-CRYPTO-MIXED-003.json --reviewer roger-codex-luna6
```

## 5. Ruling over the 13 changed or new artifacts

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && S=crates/crypto-mixed-core/specs && python3 -I tools/ligature/ligature.pyz record-ruling --reviewer roger-codex-luna6 --verdict ratified --artifact $S/cha_cha20.json --artifact $S/poly1305.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_bytes_remaining.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream.json --artifact $S/_boundaries/cha_cha20_poly1305_tag__to__poly1305_compute_tag_segments.json --artifact $S/_interactions/I-CRYPTO-MIXED-004.json --artifact $S/_interactions/I-CRYPTO-MIXED-005.json --artifact $S/_interactions/I-CRYPTO-MIXED-006.json --artifact $S/_interactions/I-CRYPTO-MIXED-007.json --artifact $S/_interactions/I-CRYPTO-MIXED-008.json --artifact $S/_bridges/BR-CRYPTO-MIXED-003.json
```

## 6. Re-mint the crypto-kani promotion receipt (all 29 artifacts)

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && S=crates/crypto-mixed-core/specs && python3 -I tools/ligature/ligature.pyz accept-promotion crypto-kani --reviewer roger-codex-luna6 --policy-path docs/reliance-policy.md --artifact docs/reliance-policy.md --artifact evidence/E-001.json --artifact evidence/E-002.json --artifact evidence/E-003.json --artifact evidence/E-004.json --artifact evidence/E-005.json --artifact evidence/E-006.json --artifact $S/cha_cha20.json --artifact $S/cha_cha20_poly1305.json --artifact $S/poly1305.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_apply_keystream.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__poly1305_finalize.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__poly1305_set_key.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_bytes_remaining.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream.json --artifact $S/_boundaries/cha_cha20_poly1305_tag__to__poly1305_compute_tag_segments.json --artifact $S/_interactions/I-CRYPTO-MIXED-001.json --artifact $S/_interactions/I-CRYPTO-MIXED-002.json --artifact $S/_interactions/I-CRYPTO-MIXED-003.json --artifact $S/_interactions/I-CRYPTO-MIXED-004.json --artifact $S/_interactions/I-CRYPTO-MIXED-005.json --artifact $S/_interactions/I-CRYPTO-MIXED-006.json --artifact $S/_interactions/I-CRYPTO-MIXED-007.json --artifact $S/_interactions/I-CRYPTO-MIXED-008.json --artifact $S/_bridges/BR-CRYPTO-MIXED-001.json --artifact $S/_bridges/BR-CRYPTO-MIXED-002.json --artifact $S/_bridges/BR-CRYPTO-MIXED-003.json
```

## After step 6 (agent, then two grants from you)

1. `check-bridges` generates the BR-CRYPTO-MIXED-003 harness; the agent adds its
   exact body to the fail-closed adapter `tests/kani_bridge_backend.py`, then
   checks `gate-g9`.
2. The agent updates both rebuilt Stage 7 plans (new obligations C004/C005/
   Poly1305.C005 and their harnesses, plus BR-CRYPTO-MIXED-003). You issue two
   exact one-shot grants for the two manifests; the agent regenerates them,
   since the receipt hash and promotion set change.
3. `record-assurance` for PRIMITIVES (six harness bindings) and the AEAD bridge
   report; then `extract-c-static`, `gate-r1-g16`, `gate-g9`, `gate-g14`.
