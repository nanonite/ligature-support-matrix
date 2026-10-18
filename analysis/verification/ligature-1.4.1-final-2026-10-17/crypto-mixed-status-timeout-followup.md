# Crypto-mixed status timeout follow-up

Date: 2026-10-18. Pilot root: `/home/goya/storage/full-ligature-port-workspace/crypto-mixed`.

## Identity and committed state

- Pilot Git HEAD: `13e602135232fb6f188125b17aa01cc1e2ffb3dd`.
- The 1.4.1 installation files are modified in the working tree as expected; source tree remains at that committed revision. The C_static report and generated bridge harnesses were refreshed through Ligature commands.
- Bundle SHA-256: `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`; `version --verify` attests source commit `742cb253e0cb9753c7a34a0c32559936130e03ab` and adjudicator `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`.

## Bounded reproductions

From the crypto-mixed pilot root, both commands were rerun with a 20-second bound:

```sh
timeout --kill-after=3s 20s python3 -I tools/ligature/ligature.pyz status --json
timeout --kill-after=3s 20s python3 -I tools/ligature/ligature.pyz --workspace /home/goya/storage/full-ligature-port-workspace/crypto-mixed status --json
```

Both returned timeout status **124** after 20 seconds and emitted no stdout/stderr. The earlier final-release record documents the explicit `--workspace` form timing out after 180 seconds. The issue is command performance; these results do not indicate an installation or pin failure.

Control evidence: `doctor` exits 0 in under one second; bundle checksum, `version --verify`, migration, and 18 managed-resource hashes pass. The same 1.4.1 `date-creusot status --json` completes successfully under 30 seconds.

No source inspection, bundle unpacking, pilot descriptor change, or assurance-policy change was made to investigate this timeout.
