# Ligature 1.5.1 re-check — date-creusot (issue #195)

Date: 2026-11-17
Pilot: `date-creusot/`
Binary: `tools/ligature/ligature.pyz`
Bundle SHA-256: `d704c5a5875d200214310c1fca7854a14a105c1b74cebaa5bc03f6a870bcc030`
`version --verify`:

```
ligature 1.5.1
  adjudicator: zipapp (attested: true)
  content hash: sha256:def6b87957ff4e26737e18a469a7df447fdadb5df3eac5180db881c42baccfcb
  bundle: 133 file(s)
  bundled schemas: 36
  source: 29acabdb6c70dbab4213ca73626d3fed78afcbcf (clean working tree)
```

Baseline artifacts are in `baseline/`: the pre-change `check --json` and
`migrate --upgrade --json`, the old C_static report, the old manifest hash, and
the version evidence.

## 1. Stray P4-5 closure input (fixed)

`analysis/p4-5-q1/scratch-inputs/specs/_closure/date-creusot-core.json` was an
untracked P4-5 Q1 probe fixture. 1.5.1's G1b reports any closure artifact
outside the canonical `specs/_closure` directory:

```
G1b high analysis/p4-5-q1/scratch-inputs/specs/_closure/date-creusot-core.json
  closure artifact is not directly under the canonical directory
  .../specs/_closure -- found under .../analysis/p4-5-q1/scratch-inputs/specs/_closure
```

Resolution: the fixture directory was archived, its closure member stored
without a `specs/_closure` path component, and the original directory removed.
The probe write-up, command outputs, and result remain in
`analysis/p4-5-q1/README.md`.

- Archive: `analysis/p4-5-q1/scratch-inputs-archive-2026-11-17.tar.gz`
- Archive SHA-256:
  `32343e92f1db05f982a22c61aabee9c047d180231b28e37de53eb6e9ec4c2092`
- Record and member hashes:
  `analysis/p4-5-q1/scratch-inputs-archive.md`

Re-check after the archive: the G1b stray-closure finding is gone from
`check --json`. The archive is inert data; re-extract it outside the pilot tree
when replaying the probe.

## 2. C_static re-extraction (fixed)

The old `ci/results/c_static/rust_date-creusot-core.json` was produced by
extractor `0.2.0`, which 1.5.1 rejects as "a different or unknown extractor
version" (G1b, g14, and r1-g16). It was preserved as
`baseline/c-static-old-extractor.json`, then re-extracted:

```sh
./tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu
# exit 0
# wrote .../ci/results/c_static/rust_date-creusot-core.json:
#   11 discovered, 11 resolved, 0 unresolved (discovered-lower-bound)
```

Report delta:

| Field | Old (0.2.0) | New (0.3.0) |
|---|---|---|
| `coverage_scope.extractor_version` | `0.2.0` | `0.3.0` |
| `source_binding.digest` | `sha256:be74b63e…` | `sha256:5fe482e4…` |
| `source_binding.file_count` | 10 | 10 |
| `callsite_coverage` | 11 discovered / 11 resolved / 0 unresolved | same |

`validate-callsites`:

```
exit 0
OK: all C_static reports pass G1a/G1b (incl. recomputed callsite coverage and
callee shapes) (1 discovered)
```

`gate r1-g16 --json`:

```
exit 0
gate_acceptance: accepted
counts: discovered 11, checked 11, unresolved 0, undeclared_blocking 0,
        undeclared_warnings 0, configuration_mismatches 0
interaction_reconciliation: complete
source_resolution: complete
```

The gate has eight `info` findings only (internal-helper calls, intent without
realization, and one declared-feature/observed-config note). **No new R1/G16
decision is outstanding**, so there is nothing to resolve or escalate here.
Evidence: `gate-r1-g16.json`, `validate-callsites.stdout.txt`,
`c-static-extract.stdout.txt`.

## 3. G13 work-package refresh (blocked on a human grant)

`migrate --upgrade --json` still exits 1, but now only for G13:

```
post_upgrade_validation.state: findings
  [G13/error] ci/manifest/WP-DATE-CREUSOT.json: gate_integrity hash mismatch
  for .codex/skills/ligature/SKILL.md:
    declared sha256:431a8179…, actual sha256:ee39e9e6…
```

`validate-work-package ci/manifest/WP-DATE-CREUSOT.json` exits 1 with the same
single G13 error (plus two pre-existing `10.1/info` findings that are not
blocking). `ci/manifest/**` is a protected root, so the manifest must not be
hand-edited.

Prepared but not run: a fresh exact-path grant and the sanctioned
`generate-work-package --regenerate` call. Current manifest bytes
(`sha256:b8f64aba…`) match the latest recorded generation event's `after_hash`,
so `--regenerate` is the correct mode. The exact commands, expected derived
changes, and post-regeneration acceptance checks are in
[`g13-regeneration-plan.md`](g13-regeneration-plan.md). This needs the
operator's `ESCALATION:` checkpoint.

## 4. Current gate state

`migrate --upgrade --json` (exit 1): only the G13 manifest error above.
`doctor`: exit 0.
`check --json` (exit 1): the two known out-of-set write-set findings
`.gitignore` and `PORT-GAPS.md`, plus `info`-severity G14/R1 findings. No
high-severity C_static, closure, or gate finding remains.
`write-set-check --issue 195 --json` (exit 1): the same two violations, both
the declared project exception.
`gate g14 --json` **exit 0**:

```
cluster date-creusot-core
  closure_kind: deductive
  status: closes
  workspace_findings: []
  CG3 generic_callees_type_universal_or_creusot_owned: VERIFIED (info)
```

`validate-closure` exit 0:
`OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (1 discovered)`.

So the only remaining acceptance blocker is the G13 manifest refresh, which
requires the human-issued grant. After that, `migrate --upgrade` and
`check --json` are expected to reach the acceptance state (the two write-set
findings excepted), with G14 still closing `date-creusot-core` deductively.

## Evidence index

| File | Contents |
|---|---|
| `baseline/` | pre-change check/migrate JSON, old C_static report, old manifest hash, version evidence |
| `c-static-extract.stdout.txt` | re-extraction result |
| `validate-callsites.stdout.txt` | G1a/G1b C_static validation |
| `gate-r1-g16.json` | R1/G16 reconciliation, accepted |
| `gate-g14.json` | release closure, deductive, closes |
| `validate-closure.stdout.txt` | closure profile/record validation |
| `migrate-upgrade.json` | post-upgrade validation, G13 only |
| `validate-work-package.stdout.txt` | G13 error detail |
| `write-set-check-195.json` | two known out-of-set findings |
| `check-after.json` | final consolidated check |
| `doctor.stdout.txt` | doctor, exit 0 |
| `stage-7-plan-WP-DATE-CREUSOT-issue-195.json` | prepared Stage 7 plan (identical to the approved #138 plan except `issue`) |
| `g13-regeneration-plan.md` | exact grant + regeneration + verification commands |
