# Chainlink #33 — Stage 8C closure and witness gates

Date: 2026-10-10

## Scope and installed tool

This Stage 8C checkpoint changes only analysis and findings artifacts, including the replay report and its logs; no source, descriptor, manifest, or protected spec was changed. `sha256sum -c tools/ligature/SHA256SUMS` reports `ligature.pyz: OK`. The pinned command reports Ligature 1.3.3, content hash `1b8fd50a65e79138486119c6876a30402ae45ca84dd914ac6edef45e85a3f0d5`; the on-disk bundle SHA-256 is `f0028d88a516be9c1c8c097f024286e1b28af6e5b38db8a49c4d047ffe45c1e1`.

The live descriptor declares `closure_kind: deductive` and `verifier_policy.default: verus`, with an empty `verifier_policy.clusters` map. `status --json` reports zero clusters. There is no `specs/_closure/` directory and no promoted closure profile. The Stage 7 work-package manifest `WP-SWISSTABLE-VERUS` is present and passes its standalone validator; its obligations require Verus evidence, but it does not declare a cluster.

## Stage 8C command results

| Command | Exit | Observed result |
|---|---:|---|
| `validate-closure` | 0 | `OK (nothing to check: no closure artifacts discovered under .)` — empty input, not a closure pass. |
| `gate-g14` | 1 | `error: no closure directory at /home/goya/storage/full-ligature-port-workspace/swisstable-verus/specs/_closure -- a release gate with nothing to close is not a pass; author a closure profile per cluster (docs/closure-profile-schema.json)` |
| `gate-g18` | 0 | `OK (nothing to check: no declared witness_required features discovered under .)` |
| `gate-g19` | 0 | `OK (nothing to check: no witness specs discovered under .)` |
| `gate-g20` | 0 | `OK (nothing to check: no witness specs discovered under .)` |
| `report pilot-cluster` | 1 | `Evaluated 0 candidate cluster(s). No eligible candidate cluster -- every candidate was excluded (see reasons above).` |
| `select-pilot-cluster` | 1 | `Evaluated 0 candidate cluster(s). No eligible candidate cluster -- every candidate was excluded (see reasons above).` |
| `validate-work-package ci/manifest/WP-SWISSTABLE-VERUS.json` | 0 | Manifest passes G1a and §10.1 checks; two informational findings remain (promotion receipt resolution and source-path/allowed-write-set mapping). |
| `check --json` | 1 | 508 findings: 5 high, 462 medium, 41 informational; conditions `blocking_findings` and `human_decision_required`. The active next action is still the R1/G16 interaction for `RawTable.new -> ControlBytes.new`. |

Thus G14 does **not** establish that a `deductive` closure matches the descriptor: it refuses before computing a closure because no cluster/profile exists. The G18–G20 zero-input results likewise establish no witness coverage. This is consistent with the earlier Stage 8A record; it is not a newly observed Ligature defect.

No cluster or closure profile was invented. The closure-drafting instructions require deriving the cluster from workspace manifests and putting a reviewed profile through the draft/approval path; `specs/_closure/` is a protected location. The current manifest has no cluster assignment, and the descriptor's clusters map is empty. The operator's existing scope decision remains in force: this port is Verus-only; no Kani cluster or mixed-verifier claim is introduced. A human must choose/authorize the cluster and profile needed before G14 can make the requested comparison.

## Independent findings replay

The fresh-agent audit attempted every one of the 76 ledger repro records from isolated, per-finding copies. Absolute pilot paths were redirected to the clean extraction; scratch paths and tool homes stayed under isolated `/tmp` directories, and file modes were preserved. The audit did not edit the live pilot or Chainlink database. The complete per-ID outcomes and log index are in [findings-replay.md](findings-replay.md).

The target-level outcomes were 31 exit matches, 13 exit mismatches, and 32 unavailable targets. The unavailable group comprises eight direct executions of `ligature.pyz` (the copied bundle is mode 664), one prose-only repro with no command, 17 Nix flake failures before Verus, and six helper-runner failures that resolved `/tmp` as the flake path before Cargo/Verus. Raw wrapper exits alone yielded 49 code matches, 18 mismatches, and nine not-replayed records; the audit does not treat a shell wrapper's matching exit as evidence that its target ran.

The target-reached mismatches include historical scripts whose wrapper exits mask printed inner gate results, stale recorded exit expectations, and source greps whose result changed or matched a comment. Miri reproduced the fixture-open failure but cargo-nextest returned 100 rather than the ledger's 1; disabling isolation returned 0 with 16/16 passing. The new Stage 8C record `swisstable-ligature-016` replayed with exit 1 as recorded.

## Scope checks

`write-set-check --issue 33 --json` reports `mutated_workspace=false`, `state=clean`, `violations=[]`; it separately lists eight pre-existing protected artifacts as audit-only/unvouched. The workspace-root Nix files are unchanged from the prior recorded issue checkpoint: `flake.nix` SHA-256 `f837c3419f226c97399b6f48c4a2d0c8fd7c4abf159cbc699c510b88ef0694a9`, `flake.lock` SHA-256 `79232a474e4623868368bd9fd0c2c12807cc8d685b9e7dffc8ded5ca00ff8eb6`. No descriptor, work-package manifest, protected spec, verifier policy, source, or Kani configuration was changed.
