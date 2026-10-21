# Chainlink #39 — Verus evidence and deductive closure probe

Date: 2026-10-10

## Verus result

The production crate was re-run with the pinned Verus 0.2026.05.24.ecee80a binary and pinned Z3 4.15.4 from `tools/versions.lock`:

```text
$ PATH=/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/7igjywfjlfa7v2sknkd9dbvpv2s5qf6g-z3-4.15.4/bin:/home/goya/.cargo/bin:$PATH verus --crate-type=lib --multiple-errors 200 rust/swisstable-verus-core/src/lib.rs
verification results:: 149 verified, 0 errors
exit=0
```

The complete verifier output is captured in `analysis/verus/verus-transcript.txt`. The separate diagnostic `verif/reachability_probe.rs` reports 12 verified and 4 errors; it is not one of the work-package obligations and is not counted as production crate evidence.

The Nix wrapper in `analysis/verus/run-verus.sh` could not launch Verus in this environment: its first run could not open `/home/goya/.cache/nix/fetcher-locks` (read-only filesystem); setting `XDG_CACHE_HOME=/tmp/issue39-xdg-cache` then exposed that the workspace root is not a Git repository. The direct invocation above uses the pinned store binaries and succeeds. The failed wrapper transcripts were replaced with the direct, successful runs so the canonical transcript reflects the actual Verus result.

## Ligature result

```text
$ python3 tools/ligature/ligature.pyz validate-evidence
OK: all evidence records pass G1a/G1b (11 discovered)

$ python3 tools/ligature/ligature.pyz gate-g14
error: no closure directory at /home/goya/storage/full-ligature-port-workspace/swisstable-verus/specs/_closure -- a release gate with nothing to close is not a pass; author a closure profile per cluster (docs/closure-profile-schema.json)
exit=1
```

`status --json` reports `closure_kind=deductive`, `verifier_policy.default=verus`, zero clusters, and artifact kinds `callsites`, `evidence`, and `work-package`; it reports no assurance artifacts. `specs/_closure/` is absent. The 11 validated E records are source-artifact, comment, and requirement records (including deferred E-010/E-011), not per-obligation Verus assurance records. `ci/results/` has no assurance record. `record-assurance --help` requires explicit `--proof OBLIGATION=PATH` mappings.

Therefore this probe confirms the crate's Verus result and confirms that the existing evidence records pass G1a/G1b, but it cannot test whether G14 accepts Verus evidence end to end: G14 stops before closure recomputation because no cluster/profile exists. No `record-assurance` mapping was minted from the whole-crate transcript; the manifest's 30 non-precondition obligations do not have an approved one-to-one certificate mapping in the workspace.

## Verus assurance-record probe

To make the full-crate result machine-readable, the pinned Verus binary was rerun with `--output-json`; outputs are in `analysis/verus/verus-results.json` and `analysis/verus/verus-results.stderr.txt`. The JSON reports `success=true`, `verified=149`, `errors=0`, and `is-verifying-entire-crate=true`. The seven concept drafts' constraints refer to 32 distinct methods; all 32 method names appear in the JSON `func-details` index. The JSON does not emit Ligature obligation IDs or individual per-obligation status labels.

`record-assurance --help` accepts one `--proof OBLIGATION=PATH` per provided guarantee. The first probe incorrectly included all 36 manifest obligations and exited 2 because the six call-site preconditions are not provided guarantees; the manifest assigns them to bridge evidence. Retrying with only the 30 `provided_guarantees`, each mapped to the successful Verus JSON report, also exited 2:

```text
error: analysis/verus/verus-results.json is not a why3find proof certificate (expected a directory holding proof.json, or the proof.json file itself)
```

No assurance artifact was written. This confirms that Ligature 1.3.3's `record-assurance` path rejects the actual Verus output format before G14 can evaluate it. The result is recorded as `swisstable-ligature-018` and escalated under Chainlink epic #1. Do not manufacture a Why3 certificate or claim that Verus assurance was recorded; #39 remains blocked pending a supported Verus assurance path.

## Cluster layout decision and remaining blocker

The operator selected six Verus-only clusters matching the concept groups already declared by the seven concept drafts:

| Cluster | Concepts |
| --- | --- |
| `hashing` | `HashMix` |
| `control-bytes` | `ControlBytes` |
| `probing` | `GroupProbe`, `ProbeSeq` |
| `table` | `RawTable` |
| `api` | `SwissTable` |
| `iteration` | `TableIterator` |

This keeps the port Verus-only; Kani and mixed-verifier scope remain excluded. `ci/manifest/WP-SWISSTABLE-VERUS.json` is a single work-package manifest whose definition of done covers all seven concepts (30 provided guarantees and 6 precondition requirements). The Stage 3 closure-profile format names whole work-package manifests in `work_packages`; it has no field for selecting a subset of a manifest's concepts or obligations. Reusing that aggregate manifest in all six profiles would therefore make each profile cover the same whole-package closure; splitting it would change the protected proof-scope manifest and its dependency/assurance model. The least-scope mapping is to retain the aggregate WPM and reference it from each of the six profiles. That gives six concept-group labels with identical, overlapping whole-package closures, not six isolated proof slices. This matches the manifest's stated one-package design and avoids splitting the tightly coupled package; the human profile review must accept that overlap.

The selected concept grouping and recommended aggregate-WPM mapping are recorded. The profile paths are protected at `specs/_closure/<cluster>.json`; `write-set-check --issue 39 --json` reports no active grant for #39. No profile, descriptor, manifest, or verifier policy was changed, and no Kani or mixed-verifier scope was introduced. The sanctioned draft/review path still needs an exact issue-scoped grant and human reviewer before it can write the six profiles.

The G14/profile blocker remains recorded as `swisstable-ligature-017`; the Verus certificate-format rejection is `swisstable-ligature-018` in `findings/limitations.jsonl` and upstream issue #125. After Ligature supports the pinned Verus output format and the human-reviewed aggregate-WPM profiles are authorized, record assurance and rerun `validate-closure` and G14.
