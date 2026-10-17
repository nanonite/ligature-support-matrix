# Ligature 1.4.0 verification and nine-obligation closure — 2026-10-17

This record documents the sanctioned completion of the date-creusot nine-obligation
workflow on the installed Ligature 1.4.0, at project revision
`729f0432c90dd7916bdbeecb750b9d5abbbbf5cd`. It resolves upstream findings
`date-creusot-063`, `date-creusot-064`, and `date-ligature-103`.

## Installed release

- Product: ligature 1.4.0
- Source commit: `38e23b4188728abf19ec29e67ff6341c9daf8d8a`
- Bundle artifact SHA-256: `sha256:1f04052e4fea0441bc807c4caf2c80ecad4d70b7f9f101665185eae7aa46dc9e`
- Content hash (adjudicator identity): `sha256:6e9072ba2b7c8f92497efc0778de214dcff9c7a5d1fc88ef17876441c0657d13`
- `version --verify`: attested true; `sha256sum -c SHA256SUMS`: OK.
- Installed into `tools/ligature/` and re-pinned with `migrate --upgrade`; the
  installation manifest now records `installed_product_version` 1.4.0 and
  `@adjudicator` `sha256:6e9072ba...`. `doctor`/`status --json` report
  `pinned` and `current`.

The same release was installed and re-pinned in the `crypto-mixed` and
`swisstable-verus` pilots (each has its own `tools/ligature` bundle).

## Stage 7: nine-obligation manifest

`generate-work-package --regenerate` (Ligature #164) replaced
`ci/manifest/WP-DATE-CREUSOT.json` in place under an exact, issue-scoped
`write` grant for issue 138, after the full candidate validated. The derived
manifest:

- `obligations`: `Month.C001`, `Weekday.C001`, `Weekday.C002`, `Weekday.C003`,
  `Year.C001`, `Year.C002`, `YearMonthDay.C002`, `YearMonthDay.C007`,
  `YearMonthDayLast.C001`.
- `report.emit`: `ci/results/WP-DATE-CREUSOT.json` (canonical
  `ci/results/<work-package>.json`), separating the assurance report from the
  feature-ledger projection.
- `provenance`: `base_commit` `729f0432...`, `artifact_set_hash`
  `sha256:69548f171e1a4210f0d95233b9592f22fa15acccda8f03e5cf1c7b43d197ce71`
  (recomputed from the current promotion receipt, superseding the stale
  `sha256:891099b3...`).
- `YearMonthDay.C007` carries a reviewed standalone assurance requirement
  derived from the approved `YearMonthDay` concept spec plus the owning
  Creusot verifier policy (Ligature #162); no interaction was invented.

The regeneration audit event (`result: regenerated`) and both before/after
hashes are in `ci/results/protected-writes.jsonl`.

## Stage 8: assurance recording

`record-assurance WP-DATE-CREUSOT` recorded all nine fresh Creusot
certificates to `ci/results/WP-DATE-CREUSOT.json`. The eight
interaction-backed obligations retain their reviewed `minimum_scope`; a
complete Creusot certificate records the verifier-derived universal input
domain as strictly stronger than that scope (Ligature #163), without copying
the requirement's domain into the achievement. `YearMonthDay.C007` records
its round-trip certificate with 10 proved goals.

## Gates

- `gate g14 --json`: exit 0; cluster `date-creusot-core`, `closure_kind`
  `deductive`; scope counts `provided_obligations` 9, `evaluated_obligations`
  9, `unique_obligations` 9; expected scope `state: matched` for exactly the
  nine IDs including `YearMonthDay.C007`; no findings.
- `gate-r1-g16 --json`: exit 0; 11 discovered / 11 checked, 0 unresolved,
  0 configuration mismatches, source resolution and interaction
  reconciliation complete.
- `validate-work-package`: OK (G1a and §10.1).
- `validate` / `validate-interaction`: OK; no unresolved concept references.
- `validate-promotion`: OK.
- `check --json`: exit 1 with only two pre-existing `write-set` high findings
  for `.gitignore` and `PORT-GAPS.md` (workspace contract files outside the
  descriptor write set), unrelated to this workflow; the G14 and R1/G16 runs
  are `executed` with no blocking gate finding.

Reports saved: `analysis/verification/g14-ligature-1.4.0-2026-10-17.json`,
`r1-g16-ligature-1.4.0-2026-10-17.json`, `check-ligature-1.4.0-2026-10-17.json`.

## Superseded artifact

The pre-1.4.0 assurance report that occupied the feature-ledger path (the old
manifest's `report.emit`) is preserved at
`analysis/verification/superseded/feature_ledger.json.1.3.12-legacy-assurance-report`
before `report feature-ledger` regenerated `ci/results/feature_ledger.json`.
Both current outputs now coexist.
