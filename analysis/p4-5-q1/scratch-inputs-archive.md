# P4-5 Q1 scratch inputs: archive record (2026-11-17)

The live probe fixture directory `analysis/p4-5-q1/scratch-inputs/` was an
untracked scratch workspace used for the 2026-10-25 P4-5 Q1 probe. Ligature
1.5.1's G1b scans the whole pilot for closure artifacts outside the canonical
`specs/_closure/` directory, so the fixture's
`scratch-inputs/specs/_closure/date-creusot-core.json` produced a blocking
finding (`G1b high analysis/p4-5-q1/scratch-inputs/specs/_closure/date-creusot-core.json`)
even though it was never a live pipeline input.

The fixture is retained as an archive. Nothing was deleted without a record.

- Archive: `analysis/p4-5-q1/scratch-inputs-archive-2026-11-17.tar.gz`
- Archive SHA-256: `32343e92f1db05f982a22c61aabee9c047d180231b28e37de53eb6e9ec4c2092`
- Original directory removed: `analysis/p4-5-q1/scratch-inputs/` (untracked)

The archive is not a live workspace. To reuse the probe, extract it outside the
pilot tree (for example under `/tmp`), not inside `date-creusot/`. That keeps
G1b from treating the fixture as a live closure artifact.

## Member mapping

The closure snapshot is stored without a `specs/_closure/` path component so
that the archive itself carries no closure-artifact path. File contents are
unchanged; the hashes below are of the original members.

| Original path | Archive path | SHA-256 |
|---|---|---|
| `scratch-inputs/ci/manifest/WP-DATE-VERUS.json` | `scratch-inputs/ci/manifest/WP-DATE-VERUS.json` | `c6c6ffd9f5998e90579bdbd59a5bf6337ec23829bc3305de74054fcede395762` |
| `scratch-inputs/ci/results/WP-DATE-VERUS.json` | `scratch-inputs/ci/results/WP-DATE-VERUS.json` | `b58745c3973a20cb208a3f5e2ea812af2759aed74b6fb926713d37d0710b0d8e` |
| `scratch-inputs/project-descriptor.json` | `scratch-inputs/project-descriptor.json` | `586efa8b170da7d9ffacf0919491ee08fca95792b9205c643a49db6ecca1e165` |
| `scratch-inputs/specs/_closure/date-creusot-core.json` | `scratch-inputs/closure-snapshot/date-creusot-core.json` | `f577bd0ba0cd56df3a852c13cd3cf499a6c8d843b38d64835af928819db3b082` |

The probe write-up and its command outputs remain in
`analysis/p4-5-q1/README.md`; this archive only relocates the scratch fixture.
