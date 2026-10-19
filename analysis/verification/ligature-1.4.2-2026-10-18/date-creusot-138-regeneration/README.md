# date-creusot: manifest G13 refresh and source-bound C_static for Ligature 1.4.2 (2026-10-19)

Ligature 1.4.2 (bundle SHA-256
`c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184`), black box.

## Manifest regeneration (G13)

After the 1.4.2 upgrade, `ci/manifest/WP-DATE-CREUSOT.json` failed G13: its
`gate_integrity` pinned the 1.4.1 managed `SKILL.md` (`6b3c3ae7…`) and
project-state schema (`f38a526b…`). The user issued an exact one-shot human
grant, `GW-669bbca24293` (issue 138, issuer `roger-codex-luna6`, TTL 3600 s).
Issue 138 is used because the generator requires `--issue` to match the plan;
the plan `analysis/verification/stage-7-plan-WP-DATE-CREUSOT-issue-138.json`
(SHA-256 `89ec5534…`) is the one that produced the manifest being replaced,
and the manifest matched that generation event (`2adfab4a…`) before the run.

```sh
python3 -I tools/ligature/ligature.pyz generate-work-package \
  --plan analysis/verification/stage-7-plan-WP-DATE-CREUSOT-issue-138.json --issue 138 \
  --toolchain 'rustc-1.90.0/cargo-creusot-0.14.0-dev/why3-1.8.2' --target x86_64-unknown-linux-gnu \
  --grant-id GW-669bbca24293 --regenerate --json
```

The run exited 0 with `result=regenerated`, `2adfab4a…` → `b8f64aba…`. The
diff is exactly the two `gate_integrity` hashes (`431a8179…`, `f5f974e4…`)
plus `provenance.base_commit` (`729f043` → `af74636`). No `--feature` was
passed, matching the existing `features: []`.

| Check | Exit | Note | File |
|---|---|---|---|
| `validate-work-package` | 0 | passes G1a and §10.1 | `validate-wp.out` |
| `write-set-check --issue 138 --json` | 1 | only the two existing violations, `.gitignore` and `PORT-GAPS.md` (unchanged since before 1.4.2) | `write-set-check-138.json` |
| `doctor` | 0 | | `doctor.out` |

## C_static re-extraction (#169 follow-up)

The 1.4.2 rollout did not refresh this pilot's report. The committed
`ci/results/c_static/rust_date-creusot-core.json` was a legacy report with no
source binding, which 1.4.2 refuses (`validate-callsites` exit 1, G1b:
"legacy C_static report has no source binding … run `ligature
extract-c-static`"). Re-extracted with the sanctioned command:

| Check | Exit | Result | File |
|---|---|---|---|
| `extract-c-static --target x86_64-unknown-linux-gnu` | 0 | 11 discovered / 11 resolved / 0 unresolved, now source-bound | `extract-c-static.out`, `c_static-legacy-before.json`, `c_static-1.4.2.json` |
| `validate-callsites` | 0 | | `validate-callsites.out` |
| `gate-r1-g16 --json` | 0 | `accepted`: 11 checked, 0 undeclared, 0 unresolved | `gate-r1-g16.json` |
| `gate-g14 --json` | 0 | `date-creusot-core` **closes deductive**; CG3 verified from artifact data (1.1 s) | `gate-g14.json` |

The array-return-type extractor defect found on crypto-mixed (upstream #170)
does not apply here: no method in `rust/*/src` returns an array type.
