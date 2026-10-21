# P2 Ligature binary issue inventory

This note consolidates Ligature reports and findings from the SwissTable P2 work. Sources are local Chainlink epic #1, the P2 README, `findings/limitations.jsonl`, and the Stage 8C #39 record. The P2 pilot now uses Ligature 1.3.5 (bundle SHA-256 `1a62e34b16af64065b35708575d81249b02e5025174a27fec23c7a467cb71bd7`, attested content hash `sha256:c0fcf84301affba6ead846db0e29477a732c6560b38158afb5ad9888dce9060c`, clean source commit `dda2bcc73cf115e2b6db75f5c0243ab84ab6bbbf`). “Open” in older report rows was the local Chainlink status; upstream Ligature issue IDs are separate. Historical reproductions are version-scoped below.

## P2 upstream reports

| Issue | P2 finding | Status and disposition |
|---|---|---|
| #107 | Before `init`, `extract-c-static` crashes with an uncaught `FileNotFoundError` when `project-descriptor.json` is absent. | Local issue remains open; corresponding Ligature issue #108 is closed. Reported on 1.2.0. |
| #109 | `doctor --descriptor PATH` ignored the supplied descriptor and could report a false clean result. | Closed; verified fixed in 1.2.1. |
| #110 | Four validators treated staged bridge, witness, exemption, and conflict-resolution drafts as final artifacts and failed on their missing review block. | Corresponding Ligature issue #110 is closed; the local tracker was open when this inventory was written. |
| #111 | Concept specs could be drafted but not approved/promoted, leaving downstream checks without concept inputs. | Closed; fixed in 1.2.2. Existing staged artifacts still require review and promotion. |
| #112 | The Stage 3 boundary and bridge templates disagreed about where a callee precondition belongs. | Closed; fixed in 1.2.2. Old drafts may need revalidation or re-cutting. |
| #113 | G9 rejected bridge premise/binding forms that the Stage 3 bridge template suggested. | Closed; fixed in 1.3.2 by documenting the accepted predicate-premise and binding form. Configuring a Verus backend in the protected descriptor was a separate operator decision, not part of this binary fix. |
| #114 | The installed reliance-policy placeholder made `accept-policy` unable to establish the version marker it required. | Closed; `accept-policy --version` fixed the command dead end in 1.2.2. Policy content, reviewer, and chosen version remain human-owned. |
| #116–#119 | P2 needed auditable protected-write grants, crate scaffolding, deterministic Stage 7 work-package generation, and managed gate-integrity hash refresh. | Closed in 1.3.2. The corresponding sanctioned commands are `authorize-write`, `scaffold-crate`, `generate-work-package`, and `migrate --upgrade`. |
| #121–#124 | `configure-crate` needed a typed Cargo profile, then fixes for nested crate roots, Verus version JSON shape, and Nix-packaged `vstd` discovery. | Closed. The successive refusals were resolved in later 1.3.x builds; the P2 #30 closeout records successful `configure-crate` use with Ligature 1.3.3. |
| Local #125 / finding #018 | `record-assurance` rejected the pinned Verus `--output-json` report as “not a why3find proof certificate.” | Upstream Ligature issue #129 is closed. Fixed in 1.3.5: a fresh annotated Verus report records one supported assurance result; mismatched notes and malformed JSON are rejected; stale reports after a Rust source change are rejected; repeated records are byte-deterministic. CLI help now documents the inner proof-note syntax. G14 remains unverified end-to-end because P2 has no reviewed closure profile. The Ligature workspace’s #125 is a separate issue; issue statuses were not changed. |

## Related open report from the other pilot

- #106 is a P1 (`date-creusot`) report for `approve`, `approve-pair`, and `approve-exemption-pair` crashing when the target has no staged `.draft`. Its corresponding Ligature issue #102 is closed; it is not a P2-originated report.

## Other P2 binary findings and upstream disposition

- `swisstable-ligature-004` records silent acceptance of an unknown `verifier_policy` key. It is covered by Ligature issue #104, now closed; the P2 observation was on 1.2.0. No duplicate was filed. P2 remains Verus-only; multi-verifier support is outside its accepted scope.
- `swisstable-ligature-008` records that G4/G5 evidence tracing does not resolve interaction `evidence_links` against evidence records. Filed upstream as #130; the 1.3.4 isolated approval probe rejected a dangling `E-001` reference. Not rerun on 1.3.5.
- `swisstable-ligature-009` records that `draft` leaves an invalid `.draft` file after returning a validation error. Filed upstream as #131; observed on 1.2.1; the 1.3.4 isolated probe confirmed the invalid `.draft` was removed. Not rerun on 1.3.5.
- `swisstable-ligature-014` records that `check-bridges` writes generated harnesses under `ci/harness/` while `write-set-check` still reports clean because that output path is not declared. Filed upstream as #132; observed on 1.2.1; the 1.3.4 isolated write-set probe flagged `ci/harness/` as out-of-set. The global `--workspace` help ordering was clear in 1.3.4. Not rerun on 1.3.5.
- `swisstable-ligature-003` records that broad init-template protected-root globs were not rejected at P0 and caused a later Stage 7 G13 failure. Filed upstream as #133; observed on 1.2.0; the 1.3.4 isolated probe confirmed narrow init globs and rejection of overlapping allowed/protected patterns. Not rerun on 1.3.5.

## Not binary defects

The missing Verus backend declaration and the absence of reviewed closure profiles/clusters were descriptor and human-review decisions. They explain why no G14 profile ran, but they are not additional Ligature bugs. The P2 port remains Verus-only by design; no Kani or mixed-verifier request is included.

## Current follow-up list

1. Upstream #129 is closed and its v1.3.5 assurance-ingestion fix passed positive, mismatch, malformed, stale-source, and deterministic-output probes in an isolated P2 copy. Full G14 acceptance remains unverified because no reviewed closure profile exists.
2. #130–#133 were last behaviorally rechecked against v1.3.4; the v1.3.5 bundle update did not repeat those probes.
3. The corresponding upstream missing-descriptor and staged-draft-validator reports (#108 and #110) are closed; no duplicate reports were filed.

The P2 closeout closed #39 as a completed diagnostic result with an accepted limitation; it did not claim G14 passed. P3 has not been started.
