# C.1 re-check: ownership manifest vs work-package manifest (chainlink #55)

Date: 2026-11-17
Owning finding: `date-ligature-001` (`findings/limitations.jsonl`)
Upstream report: epic #1 #71 (closed; fixed under Ligature 1.2.0 and still fixed
under 1.5.1)
Binary: `date-creusot/tools/ligature/ligature.pyz`
Bundle SHA-256: `d704c5a5875d200214310c1fca7854a14a105c1b74cebaa5bc03f6a870bcc030`

## Result

**FIXED / NOT REPRODUCIBLE under Ligature 1.5.1.**

The 1.0.0 defect was that `status --json` reported the tool's own ownership
manifest as a failed work package:

```json
{"artifact_id":"installation","kind":"work-package","lifecycle":"invalid",
 "path":"ci/manifest/installation.json"}
```

Under 1.5.1 that artifact is absent. The same run reports
`installation_manifest.state: "current"`, so `status` now agrees with `doctor`.
The only `work-package` artifacts reported are real `ci/manifest/WP-*.json`
manifests, and each is `validated`.

## Reproduction

The original repro is a fresh `init --mode port`, then `status --json`.
[`repro.sh`](repro.sh) runs it in a throwaway root outside every pilot tree
using this pilot's pinned binary. Current output:

```text
$ bash analysis/ligature/c1-recheck-1.5.1/repro.sh
ligature: 1.5.1
installation_manifest.state: current
ci/manifest/installation.json artifacts: []
work-package artifacts: []
PASS: ci/manifest/installation.json is ownership metadata, not a work-package artifact
exit 0
```

Raw outputs from the same run:

- [`fresh-init/init.stdout.txt`](fresh-init/init.stdout.txt) —
  `ownership manifest: ci/manifest/installation.json`
- [`fresh-init/status.json`](fresh-init/status.json) — `"artifacts":[]`,
  `"installation_manifest":{"state":"current",...}`, product 1.5.1
- [`fresh-init/doctor-installation.txt`](fresh-init/doctor-installation.txt) —
  `installation: current`
- [`fresh-init/check.json`](fresh-init/check.json) — exit 1 only for the
  unrelated fresh-init policy/fixture/crate-prerequisite findings; no
  installation-artifact finding

The fresh root's `check` exit 1 is expected and unrelated: `init` leaves the
reliance-policy placeholder and descriptor example values for a human, and the
declared crate does not exist yet. It does not report the C.1 collision.

## Other baseline roots under the same binary

Each `status --json` was run on an rsync scratch copy outside the pilot tree
(no live pilot was mutated). The ownership manifest is absent from `artifacts`
in all three; only real work-package manifests appear.

| Root | `installation_manifest.state` | `installation.json` artifact | work-package artifacts |
|---|---|---|---|
| `date-creusot` | current | absent | `WP-DATE-CREUSOT.json` (validated) |
| `swisstable-verus` | current | absent | `WP-SWISSTABLE-VERUS.json` (validated) |
| `crypto-mixed` | current | absent | `WP-CRYPTO-MIXED-AEAD-001.json`, `WP-CRYPTO-MIXED-PRIMITIVES-001.json` (validated) |

Machine-readable summary: [`summary.json`](summary.json). Raw status JSON:
[`baselines/`](baselines/).

## Scope

- No Ligature source or `ligature.pyz` contents were inspected; the check is
  black-box.
- The probe roots were created under `/tmp/opencode/`, outside the pilot
  trees. No `specs/_closure` file was written inside a pilot.
- No protected write, grant, approval, promotion, or ruling was made.
- No live pilot file was changed by this re-check; the only pilot changes are
  this evidence directory and the appended `date-creusot-069` finding.
