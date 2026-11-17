# G13 work-package regeneration plan — Ligature 1.5.1, chainlink #196

Status: **waiting on human-issued protected-write grants**. The worker did not
edit any protected file. `ci/manifest/**` is a declared protected root; the
only sanctioned writer is `generate-work-package`.

## Why regeneration is needed

`migrate --upgrade --json` exits 1 with `post_upgrade_validation.state:
findings`, and its only findings are the two G13 errors below
(`migrate-upgrade.json`; `files_written: []`, `conflicts: []`):

```
[G13/error] ci/manifest/WP-CRYPTO-MIXED-AEAD-001.json:
  gate_integrity hash mismatch for .codex/skills/ligature/SKILL.md:
    declared sha256:431a8179e9364591db288c707b6b5c8a3f28bd6799db5932482e14ca83bf588a,
    actual   sha256:ee39e9e64d510dbb918eb1cab6185aae8df5f4054f84a5f09766a2033df39735
[G13/error] ci/manifest/WP-CRYPTO-MIXED-PRIMITIVES-001.json:
  gate_integrity hash mismatch for .codex/skills/ligature/SKILL.md:
    declared sha256:431a8179…, actual sha256:ee39e9e6…
```

Only the `.codex/skills/ligature/SKILL.md` pin is stale. The other four
`gate_integrity` entries (`.ligature/schemas/consolidated-check.schema.json`,
`.ligature/schemas/project-state.schema.json`, `scripts/witness_renderer.py`,
`scripts/xml_escape.py`) still match. `validate-work-package` on each manifest
exits 1 with the same single G13 error plus the two pre-existing non-blocking
`10.1/info` findings (`validate-work-package.stdout.txt`).

## Preconditions verified (read-only)

- **Current bytes match the latest grant-backed write event**, which is the
  `--regenerate` precondition. The later `unchanged` no-op events do not
  establish provenance, so the latest *writing* event is the one compared:

  | Manifest | Current sha256 | Latest write event | Grant |
  |---|---|---|---|
  | `WP-CRYPTO-MIXED-PRIMITIVES-001.json` | `sha256:6f28effc…` | `regenerated`, 2026-10-19T16:38:53Z | `GW-dd600ef187c2` |
  | `WP-CRYPTO-MIXED-AEAD-001.json` | `sha256:722d6521…` | `regenerated`, 2026-10-19T16:39:51Z | `GW-3a6e9f51d098` |

  Both hashes are the events' `after_hash` in
  `ci/results/protected-writes.jsonl` (`baseline/manifest-hashes.json`).
- **Plan files.** Each plan is a byte-identical copy of the Stage 7 plan that
  produced the current manifests
  (`date-creusot/analysis/verification/ligature-1.4.2-2026-10-18/crypto-mixed-47-callsite-respelling/stage7-plans-v2/stage-7-plan-WP-CRYPTO-MIXED-*-issue-134.json`)
  with only the `issue` field changed to `chainlink:196` so it matches the
  issue-scoped grant:
  - `stage-7-plan-WP-CRYPTO-MIXED-PRIMITIVES-001-issue-196.json`
  - `stage-7-plan-WP-CRYPTO-MIXED-AEAD-001-issue-196.json`
- **Plan accepted up to the grant check.** Both plans parse, resolve the
  closure profile, manifests, bridges and assurance inputs, and are refused
  only for the missing capability (`generate-*-refusal.json`, exit 2):

  ```
  {"error":{"code":"missing-or-invalid-grant",
            "message":"no active exact-path write grant for issue 196 covers
                       ci/manifest/WP-CRYPTO-MIXED-…-001.json; nearby records:
                       … (other-issue)",
            "required_inputs":["authorize-write --issue 196 --path
                       ci/manifest/WP-CRYPTO-MIXED-…-001.json --op write
                       --issuer <name>"]},
   "state":"refused"}
  ```

  The refusal wrote nothing: `ci/results/protected-writes.jsonl` and both
  manifests are unchanged (`sha256:f640cef7…` ledger hash before and after).

## Human checkpoint (operator) — run both grants

`authorize-write` is a Tier 2 human checkpoint. The worker must not run it.
Each grant is exact-path and issue-scoped to **196**; a grant for the old
issue 134 would not be consumed by `write-set-check --issue 196`.

```sh
cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed
./tools/ligature/ligature.pyz authorize-write \
  --issue 196 \
  --path ci/manifest/WP-CRYPTO-MIXED-PRIMITIVES-001.json \
  --op write --issuer <human-identity> --issuer-kind human \
  --ttl 900 --one-shot --json

./tools/ligature/ligature.pyz authorize-write \
  --issue 196 \
  --path ci/manifest/WP-CRYPTO-MIXED-AEAD-001.json \
  --op write --issuer <human-identity> --issuer-kind human \
  --ttl 900 --one-shot --json
```

Record each returned `grant_id` (`GW-…`). Issue the second grant within the
first grant's TTL, or regenerate immediately after each grant.

## Sanctioned regeneration — run in this order

```sh
cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed
./tools/ligature/ligature.pyz generate-work-package \
  --plan analysis/p4-verifier-fit/ligature-1.5.1/stage-7-plan-WP-CRYPTO-MIXED-PRIMITIVES-001-issue-196.json \
  --issue 196 \
  --toolchain 1.95.0-x86_64-unknown-linux-gnu \
  --target x86_64-unknown-linux-gnu \
  --feature default \
  --regenerate \
  --grant-id <GW-primitives> \
  --json

./tools/ligature/ligature.pyz generate-work-package \
  --plan analysis/p4-verifier-fit/ligature-1.5.1/stage-7-plan-WP-CRYPTO-MIXED-AEAD-001-issue-196.json \
  --issue 196 \
  --toolchain 1.95.0-x86_64-unknown-linux-gnu \
  --target x86_64-unknown-linux-gnu \
  --feature default \
  --regenerate \
  --grant-id <GW-aead> \
  --json
```

The command derives the candidate, runs the same G1a/§10.1 validation as
`validate-work-package`, and replaces the manifest atomically only on success;
the old bytes survive any refusal. `--adopt-existing` is **not** the right
mode: both manifests already have grant-backed generation provenance.

Expected derived changes (all command-produced, no hand edits):

- `gate_integrity` entry for `.codex/skills/ligature/SKILL.md` becomes
  `sha256:ee39e9e64d510dbb918eb1cab6185aae8df5f4054f84a5f09766a2033df39735`.
- `issue` becomes `chainlink:196` (the plan and grant must both name 196).
  This is an attribution change from `chainlink:134`; it follows from
  scoping the write to this issue. If the operator wants the manifest to keep
  `chainlink:134`, the grant and plan must both name 134, which then cannot be
  consumed by `write-set-check --issue 196`. Preferred: 196.
- `provenance.base_commit` and `provenance.artifact_set_hash` may refresh to
  the current workspace state; the generator owns those values.
- No obligation, bridge, function, gate, write-policy or definition-of-done
  content should change. If any does, stop and treat it as a plan-scope
  mismatch, not a G13 refresh.

## Post-regeneration verification

```sh
cd /home/goya/storage/full-ligature-port-workspace/crypto-mixed
./tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-CRYPTO-MIXED-PRIMITIVES-001.json
./tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-CRYPTO-MIXED-AEAD-001.json
./tools/ligature/ligature.pyz write-set-check --issue 196 --json
./tools/ligature/ligature.pyz migrate --upgrade --json
./tools/ligature/ligature.pyz doctor
CARGO_TARGET_DIR=/tmp/opencode/kani-target-196 ./tools/ligature/ligature.pyz check --json
CARGO_TARGET_DIR=/tmp/opencode/kani-target-196 ./tools/ligature/ligature.pyz gate-g14 --json
```

Acceptance for #196:

- both `validate-work-package` runs exit 0, with only their two pre-existing
  `10.1/info` findings;
- `migrate --upgrade --json` exits 0 (no G13 findings);
- `doctor` exits 0;
- `check --json` exits 0 with only the accepted `medium`
  `generic_callees_type_universal_or_creusot_owned` G14 finding for
  `crypto-kani` plus `info` findings (the state captured in `check-after.json`
  before regeneration);
- `gate-g14 --json` exits 0 with `crypto-kani` `status: degraded`,
  `closure_kind: bounded`, and the same `per-instantiation` degradation;
- `write-set-check --issue 196` stays clean apart from the two grants being
  reported as consumed.

Run Kani one harness at a time and keep `CARGO_TARGET_DIR` outside the pilot
(as above); `check` and `gate g14` rerun every recorded harness.
