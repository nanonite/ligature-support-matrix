# Verifier-policy probe on Ligature 1.4.1

Date: 2026-10-18. This is a black-box probe for local Chainlink #75, run on
reset scratch copies of the date-creusot pilot. No live pilot files were changed.

## Identity and evidence

- Bundle: `date-creusot/tools/ligature/ligature.pyz`, SHA-256
  `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`.
- `sha256sum -c SHA256SUMS`: exit 0, `ligature.pyz: OK`.
- `python3 -I ligature.pyz version --verify`: exit 0; version 1.4.1,
  source `742cb253e0cb9753c7a34a0c32559936130e03ab`, attested content hash
  `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`.
- Generated descriptor schema at
  `.ligature/schemas/project-descriptor.schema.json`, SHA-256
  `a6166c6d70ee97b60e3656133908315c297b3f7470202659fd20731c087c534b`.
  Its `verifier_policy` description says it is closed to exactly `default`,
  `clusters`, and `supporting`, and the generated schema names the verifier
  domain `creusot`, `verus`, and `kani`.
- The tested descriptor inputs and unfiltered CLI captures are preserved under
  [`verifier-policy-probe/`](verifier-policy-probe/). Each scratch descriptor
  is also linked to its captured `status --json` and `check --json` output.

## Probes

Both scratch roots were made from the current date-creusot tree with
`upstream/` excluded. The only input mutation was `verifier_policy`:

1. `{"default":"creusot","supporting":["kani"]}`
2. `{"default":"creusot","fallback":"kani"}`

In each scratch root, the exact CLI commands were:

```sh
python3 -I tools/ligature/ligature.pyz status --json
python3 -I tools/ligature/ligature.pyz check --json
```

Results:

| Input | `status --json` | `check --json` | Interpretation |
|---|---|---|---|
| `supporting:["kani"]` | exit 0; descriptor `present-valid`; normalized policy echoes `{"clusters":{},"default":"creusot","supporting":["kani"]}`; gate integrity `pinned` | exit 1 due to unrelated existing project findings | A second verifier is expressible under the documented `supporting` key. |
| `fallback:"kani"` | exit 0; descriptor `present-invalid`; gate-integrity detail says `unexpected property 'fallback'; permitted: clusters, default, supporting` | exit 5, conditions include `gate_integrity_failed` and `invalid_input`; P0 and gate-integrity findings repeat the rejected property | The old silently accepted alias is now rejected and surfaced as invalid input. |

Historical replay `date-ligature-011` also tests `defualt` and records
`present-invalid` on this same 1.4.1 artifact. The current schema exposes the
three-value verifier domain, and `status` echoes the effective normalized
policy. Thus the three defects in #75 (open object/typo trap, undisclosed value
domain, and inability to express a second verifier) were rechecked against
1.4.1 and are resolved. The valid-policy `check` exit 1 is not evidence of a
policy failure; it is the existing project check result. All probes here ran
on scratch copies, not the live pilot.
