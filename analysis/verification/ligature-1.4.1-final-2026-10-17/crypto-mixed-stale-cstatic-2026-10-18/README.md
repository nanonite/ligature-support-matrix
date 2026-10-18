# crypto-mixed: G14 and R1/G16 accepted a stale, empty C_static report (2026-10-18)

Found during #134 verification on Ligature 1.4.1 (bundle SHA-256
`973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`). Black box.

## What was observed

- The committed `ci/results/c_static/crates_crypto-mixed-core.json`
  (`c_static-committed-2cbbccd.json`, SHA-256 `20845eb0…d857`) dates from the
  2026-10-13 pilot baseline commit `2cbbccd`, before the Rust port existed
  (`e0bd451`). It reports `discovered: 0`, `local_concepts: []`, and has no
  binding to the crate source (no source hash or commit).
- On a disposable copy with the 2026-10-18 regenerated manifests and that
  committed report, `gate-g14 --json` exits **0**: cluster `crypto-kani`
  `degraded`, with only the accepted CG3 finding (`g14-empty-cstatic.json`).
  `gate-r1-g16 --json` exits **0**, `gate_acceptance: accepted`, 0 checked.
  The three declared interactions are reported only as info, "intent without
  realization, not a coverage failure" (`r1g16-empty.json`).
- The live pilot holds the report that the previous session regenerated at
  02:54 with `extract-c-static --target x86_64-unknown-linux-gnu`
  (`c_static-fresh-1.4.1.json`, SHA-256 `81bbec5a…626e`). It has 16
  discovered, 12 resolved, and 4 unresolved `possible-dispatch` sites
  (`aead.rs:49,52,76`, `poly1305.rs:32`). Against it, live `gate-g14 --json`
  exits **1** (`blocked`): WP-AEAD `all-discovered-resolved` fails for both
  bridges, G17 recomputes `unresolved_indirect_calls_at_or_above_medium` as 4
  where 0 is declared, and the CG3 condition is still `degraded` (accepted).
  `check --issue 134 --json` also reports three R1 "absent from I" calls:
  `encrypt`/`decrypt` → `ChaCha20.with_counter` and `Poly1305.set_key` →
  `Poly1305State.new`. See `../crypto-mixed-134-regeneration-2026-10-18/`.

## Consequence

Earlier results reported as "G14 exits 0, cluster degraded" for crypto-mixed
(2026-10-14 and the morning of 2026-10-18) were computed against an empty call
graph. They did not validate call sites. Stage 8A call-site work (#47:
`validate-callsites`, R1/G16) has never actually been performed on the
implemented port.

## Expected from Ligature

G14 and R1/G16 should detect a call-graph observation that is stale relative
to the crate it describes, and refuse it or flag it high instead of reading
"0 unresolved". Two cheap signals were available: the report has no source
binding, and it lists no local concepts or call sites while the closure's
manifests own 13 functions in that crate. Filed upstream; see local #149.
