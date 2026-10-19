# crypto-mixed #47: BR-CRYPTO-MIXED-003 scope (2026-10-19)

## Problem

After round 1, the regenerated AEAD manifest required BR-CRYPTO-MIXED-003 at
the scope of `kani_chacha20_c003_aead_counter_one_stream_capacity`. That is
the scope of I-CRYPTO-MIXED-007's `ChaCha20.C003` reliance, copied from
I-CRYPTO-MIXED-002. At the time the harness checked only encrypt's length
gate. Decrypt's gate was proved by the dedicated
`bridge_003_limits_aead_ciphertext_to_the_counter_one_stream`, which the
BR-003 adapter used, so the record and the manifest disagreed.

## Round 2 (refused, kept for the record)

The owner approved, ruled on, and re-promoted an I-007 whose C003 reliance
named `bridge_003…` (`draft-responses-i007-round2-refused/`,
`draft-logs/draft-I-CRYPTO-MIXED-007.json.round2-refused.out`).
`generate-work-package` then refused both manifests, writing nothing
(`stage7-plans-v2/generate-*-round2.json`):

> contradictory-source: obligation 'ChaCha20.C003' is declared with
> conflicting required_assurance by I-CRYPTO-MIXED-002, I-CRYPTO-MIXED-007

Every reliance on one obligation must carry one `required_assurance`, so
bridges that conclude the same callee obligation at different call sites
must share one evidence scope.

## Round 3 (fix)

- `kani_chacha20_c003_aead_counter_one_stream_capacity` now proves both AEAD
  length gates: every plaintext length `encryption_output_length` accepts,
  and every message length `decryption_output_length` returns, fits the
  counter-one stream. Kani 0.67: 0/34 failed. Both assertions are reachable;
  the only unreachable check is `bytes_remaining`'s overflow guard, as before
  (`kani-c003-folded.out`).
- The BR-003 adapter mappings (`tests/kani_bridge_backend.py`,
  `tests/record_bridge_only_report.py`) now use that harness, as BR-002's do.
  `check-bridges` exit 0 and `gate-g9` exit 0 over 3 bridges
  (`check-bridges-3.out`, `gate-g9-round3.out`).
- `bridge_003…` stays in `src/kani_proofs.rs` but is unused, like the
  pre-existing `bridge_002…` (the agent's attempt to remove it was blocked).
- I-007 is redrafted back to the round-1 scope. The staged draft is identical
  to the round-1 response (`draft-responses-i007/`).

## Human checkpoint

Approve, rule, and re-mint over the same 29 artifacts (one line, stops at
the first failure):

```sh
! cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed && S=crates/crypto-mixed-core/specs && python3 -I tools/ligature/ligature.pyz approve $S/_interactions/I-CRYPTO-MIXED-007.json --reviewer roger-codex-luna6 && python3 -I tools/ligature/ligature.pyz record-ruling --reviewer roger-codex-luna6 --verdict ratified --artifact $S/_interactions/I-CRYPTO-MIXED-007.json && python3 -I tools/ligature/ligature.pyz accept-promotion crypto-kani --reviewer roger-codex-luna6 --policy-path docs/reliance-policy.md --artifact docs/reliance-policy.md --artifact evidence/E-001.json --artifact evidence/E-002.json --artifact evidence/E-003.json --artifact evidence/E-004.json --artifact evidence/E-005.json --artifact evidence/E-006.json --artifact $S/cha_cha20.json --artifact $S/cha_cha20_poly1305.json --artifact $S/poly1305.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_apply_keystream.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__poly1305_finalize.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__poly1305_set_key.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_encrypt__to__cha_cha20_bytes_remaining.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_with_counter.json --artifact $S/_boundaries/cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream.json --artifact $S/_boundaries/cha_cha20_poly1305_tag__to__poly1305_compute_tag_segments.json --artifact $S/_interactions/I-CRYPTO-MIXED-001.json --artifact $S/_interactions/I-CRYPTO-MIXED-002.json --artifact $S/_interactions/I-CRYPTO-MIXED-003.json --artifact $S/_interactions/I-CRYPTO-MIXED-004.json --artifact $S/_interactions/I-CRYPTO-MIXED-005.json --artifact $S/_interactions/I-CRYPTO-MIXED-006.json --artifact $S/_interactions/I-CRYPTO-MIXED-007.json --artifact $S/_interactions/I-CRYPTO-MIXED-008.json --artifact $S/_bridges/BR-CRYPTO-MIXED-001.json --artifact $S/_bridges/BR-CRYPTO-MIXED-002.json --artifact $S/_bridges/BR-CRYPTO-MIXED-003.json
```

The round-2 grants `GW-ae29e8b2cafa` (PRIMITIVES) and `GW-d85c40268320`
(AEAD) were not spent by the refused runs and are valid until 18:01 UTC. If
they expire first, issue two more.

## After (agent)

Regenerate both manifests from `stage7-plans-v2/` (plans unchanged), then
re-record PRIMITIVES (the C003 harness changed, so all six bindings are
re-run), assemble the AEAD bridge-only report, and run `extract-c-static`,
`gate-r1-g16`, `gate-g9`, and `gate-g14`.
