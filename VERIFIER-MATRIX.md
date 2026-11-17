# Verifier portfolio matrix — revised 2026-10-26

The operator selected **four distinct new C++ projects**, one for each multi-verifier combination, preserving the three original single-verifier baselines. The canonical execution/coverage plan is [P4-MIXED-PORT-PLAN.md](P4-MIXED-PORT-PLAN.md). This replaces the old nine-cell baseline re-port matrix; its text is [retained as history](planning/p4-mixed-2026-10-26/historical/VERIFIER-MATRIX-before-four-projects.md), not an active implementation queue.

## Seven project workspaces, four new ports

| Configuration | Project / workspace | Status | Meaning |
|---|---|---|---|
| Creusot | P1 Howard Hinnant date / `date-creusot/` | Existing baseline, preserved | Keep accepted evidence, original scope and known limitations |
| Verus | P2 Abseil SwissTable / `swisstable-verus/` | Existing baseline, preserved | Keep proof/scope evidence; remaining baseline closure maintenance is #162 |
| Kani | P3 Botan crypto / `crypto-mixed/` | Existing baseline, preserved | Existing bounded/degraded evidence is not relabelled as deductive |
| Creusot + Verus | M4 Boost.ICL / `icl-creusot-verus/` | Independent Git/Ligature setup root; not ported/proved | Algebra/generic interval contracts plus canonical set/map mutation invariants |
| Creusot + Kani | M5 TinyXML2 / `tinyxml2-creusot-kani/` | Independent Git/Ligature setup root; not ported/proved | Recursive DOM/parser semantics plus bounded scanning/entity/buffer checks |
| Verus + Kani | M6 Snappy / `snappy-verus-kani/` | Independent Git/Ligature setup root; not ported/proved | Scalar codec invariants plus optimized overlap/SIMD copy checks |
| Creusot + Verus + Kani | M7 LevelDB storage slice / `leveldb-three-verifiers/` | Independent Git/Ligature setup root; not ported/proved | Joined batch/log/block pipeline with logical state, representation and codec evidence |

Each mixed row is one independent Git/Ligature root with as many separate Cargo/compiler roots as needed. No extra top-level workspace is created for every verifier/port permutation. The four source pins, source-level edge candidates, selected operations, oracle plans, explicit exclusions and remaining human gates are in the canonical plan and [machine-readable project map](planning/p4-mixed-2026-10-26/projects.json).

## Six directed pairs, grounded in actual source

| Caller → callee | Assigned project | Candidate real source boundary; fit must freeze exact owners |
|---|---|---|
| Creusot → Verus | M4 ICL | High-level interval-set add → segment mutation `_add` |
| Verus → Creusot | M4 ICL | Mutation → interval emptiness/endpoint/subtraction algebra |
| Creusot → Kani | M5 TinyXML2 | Parser/DOM access → StrPair/entity processing |
| Kani → Creusot | M5 TinyXML2 | GetCharacterRef → ConvertUTF32ToUTF8 |
| Verus → Kani | M6 Snappy | Decoder/writer AppendFromSelf → optimized IncrementalCopy |
| Kani → Verus | M6 Snappy | Optimized copy → IncrementalCopySlow fallback |

A plausible ownership map is not verified composition. Intake must trace real calls in the pinned source; do not add artificial runtime backedges to fill a direction. Report an uncovered direction as a gap requiring disposition.

## Measured Ligature rules, reference 1.4.3

Reference bundle SHA-256: `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`. These statements are from the [completed #159 probes](crypto-mixed/analysis/p4-verifier-fit/p4-5-probes/continuation-1.4.3/README.md), not source inspection.

- A Verus-only deductive slice verifies CG3 in 1.4.3 (#175 fixed). Accepted evidence must have the documented verifier declaration; arbitrary function-name harnesses are rejected with actionable diagnostics (#176 fixed).
- Accepted supporting evidence in a package is evaluated and can make `single_verifier_system` false. Merely listing a separate package as supporting does not automatically add it. A supporting label is not a soundness exemption.
- A required cross-verifier guarantee brings supplier evidence into the caller's evaluated closure and triggers CG1. A trusted-assumption representation can narrow that evaluated scope; it does not prove the assumption or remove the global CG3 audit.
- Complete Creusot/Verus assurance can verify CG3. A closure using both still fails CG1. Neither tested mixed owner declaration produced a G17 owner mismatch; neither established a unique sound composite owner.
- Kani evidence anywhere in the current workspace withholds CG3 from unrelated deductive clusters. A `deductive` claim over a closure containing bounded Kani evidence is inappropriate; use the actual selected partial/bounded/degraded scope and human decisions.
- One genuinely approved/ratified scratch degradation covered CG1+CG3 under one `harness-tested` ceiling. This is not production acceptance and not one ceiling per condition.
- #160 demonstrated compiler coexistence with independent Cargo roots/locks/pins/targets. Creusot used an existing matching 0.12 Nix pair; the current 0.14 shell mismatch and external companion-output check remain setup prerequisites.

For every new project, report actual `works / friction / blocker`, per-obligation proof/domain/TCB, native-oracle outcome, actual `deductive / bounded / partial` profile, closed/degraded/blocked status, failed/released conditions and one accepted record ceiling where applicable. Do not promise unqualified mixed deductive closure merely because the components prove or build.

## CG6/G15 and execution scope

Audit the actual M7 storage graph/protocol. If it lacks a real cross-cluster SCC or non-pairwise protocol, retain that absence and use clearly labelled synthetic fixtures under the same M7 project root. Ordinary recursion is not CG6; having three components is not G15. Human checkpoints remain required for positive discharge/debt acceptance. There is no fifth new C++ project or top-level workspace.

#161 is closed with the operator's recorded coverage direction; #177 remains the setup issue and does not itself approve production risk or protected-path grants. The new setup and four project stage chains are in [backlog-map.json](planning/p4-mixed-2026-10-26/backlog-map.json). Old #163–#168 are superseded, not completed. #169–#174 compare and roll up the four new projects; baseline #162 remains deferred maintenance after that roll-up.

## Ligature tested-version and per-root toolchain requirement

The operator directed that every project keep its own Git workspace and
reproducible verifier setup, that Ligature provide the matching Nix Creusot
pair, and that each Ligature version publish the exact verifier versions it
was tested with. The current 1.4.3 bundle does not publish that matrix or a
toolchain pin. The measured local versions, synthetic-vs-production limits,
Nix hashes and remaining 0.14 mismatch are recorded in
[the workspace compatibility record](planning/p4-mixed-2026-10-26/setup/LIGATURE-VERIFIER-COMPATIBILITY.md).
Each new root carries its own verifier subset at
`analysis/setup/VERIFIER-TOOLCHAIN-COMPATIBILITY.md`. These local records do
not imply official Ligature support, a production proof, or a resolution of
epic #2.
