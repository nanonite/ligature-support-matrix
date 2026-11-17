# G13 work-package regeneration plan — Ligature 1.5.1, issue #195

Status: **waiting on a human-issued protected-write grant**. No protected file
was edited by the worker.

## Why regeneration is needed

`migrate --upgrade` exits 1 only because the post-upgrade G13 validation of
`ci/manifest/WP-DATE-CREUSOT.json` still declares the pre-1.5.1 managed-skill
hash:

```
- [G13/error] ci/manifest/WP-DATE-CREUSOT.json: gate_integrity hash mismatch for
  .codex/skills/ligature/SKILL.md:
    declared sha256:431a8179e9364591db288c707b6b5c8a3f28bd6799db5932482e14ca83bf588a,
    actual   sha256:ee39e9e64d510dbb918eb1cab6185aae8df5f4054f84a5f09766a2033df39735
```

The other three `gate_integrity` entries still match. The manifest is in a
declared protected root (`ci/manifest/**`); it must not be hand-edited.
`generate-work-package` is the sanctioned Stage 7 verb.

## Preconditions verified

- Current manifest bytes match the latest grant-backed generation event:
  `sha256:b8f64abac3310c40f2fa243b54c660790017cd157260921f3121449c6dcc3e3d`
  equals the `after_hash` of the `work-package-generation` event recorded at
  `2026-10-19T04:22:17Z` in `ci/results/protected-writes.jsonl`
  (grant `GW-669bbca24293`, result `regenerated`). This is the
  `--regenerate` precondition.
- The plan is the approved nine-obligation Stage 7 plan with only its `issue`
  field changed to match this issue:
  `analysis/verification/ligature-1.5.1/stage-7-plan-WP-DATE-CREUSOT-issue-195.json`.
  It is byte-identical to
  `analysis/verification/stage-7-plan-WP-DATE-CREUSOT-issue-138.json` apart
  from `issue`.
- `generate-work-package` refused the plan without a grant, as expected:

  ```
  EXIT 2
  {"command_result":2,"error":{"code":"missing-or-invalid-grant",
   "message":"no active exact-path write grant for issue 195 covers
   ci/manifest/WP-DATE-CREUSOT.json; nearby records: ... (other-issue)",
   "required_inputs":["authorize-write --issue 195 --path
   ci/manifest/WP-DATE-CREUSOT.json --op write --issuer <name>"]},
   "event":"work-package-generation","schema_version":"1.0","state":"refused"}
  ```

## Human checkpoint (operator)

Issue the exact-path grant. This is a Tier 2 human action; the worker must not
run it.

```sh
cd /home/goya/storage/full-ligature-port-workspace/date-creusot
./tools/ligature/ligature.pyz authorize-write \
  --issue 195 \
  --path ci/manifest/WP-DATE-CREUSOT.json \
  --op write \
  --issuer <human-identity> \
  --issuer-kind human \
  --ttl 900 \
  --one-shot \
  --json
```

Record the returned `grant_id` (`GW-…`).

## Sanctioned regeneration

```sh
cd /home/goya/storage/full-ligature-port-workspace/date-creusot
./tools/ligature/ligature.pyz generate-work-package \
  --plan analysis/verification/ligature-1.5.1/stage-7-plan-WP-DATE-CREUSOT-issue-195.json \
  --issue 195 \
  --toolchain rustc-1.90.0/cargo-creusot-0.14.0-dev/why3-1.8.2 \
  --target x86_64-unknown-linux-gnu \
  --regenerate \
  --grant-id <GW-…> \
  --json
```

The command validates the full derived candidate before replacing the manifest
and preserves the old bytes on any refusal. Expected derived changes, all
command-produced, no hand edits:

- `gate_integrity` entry for `.codex/skills/ligature/SKILL.md` becomes
  `sha256:ee39e9e64d510dbb918eb1cab6185aae8df5f4054f84a5f09766a2033df39735`.
- `issue` becomes `chainlink:195` because the command requires the plan's
  `issue` to equal `--issue`, and the grant is scoped to this issue. If the
  operator wants to keep `chainlink:138` attribution instead, the grant and
  plan must both use 138; `write-set-check --issue 195` would then not consume
  it. Preferred: 195.
- `provenance.base_commit` / `provenance.artifact_set_hash` may refresh to the
  current workspace state, as derived by the generator.

## Post-regeneration verification

```sh
cd /home/goya/storage/full-ligature-port-workspace/date-creusot
./tools/ligature/ligature.pyz validate-work-package ci/manifest/WP-DATE-CREUSOT.json
./tools/ligature/ligature.pyz write-set-check --issue 195 --json
./tools/ligature/ligature.pyz migrate --upgrade --json
./tools/ligature/ligature.pyz doctor
./tools/ligature/ligature.pyz check --json
./tools/ligature/ligature.pyz gate g14 --json
```

Acceptance:

- `validate-work-package` exits 0 (its two `10.1/info` findings are
  pre-existing and non-blocking).
- `migrate --upgrade --json` exits 0.
- `check --json` exits 0 except for the two known out-of-set write-set
  findings `.gitignore` and `PORT-GAPS.md` (declared project exception).
- `gate g14 --json` exits 0 with `date-creusot-core` still
  `closure_kind: deductive`, `status: closes`.
