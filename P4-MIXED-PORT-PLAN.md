# P4: four distinct mixed-verifier C++ ports

**Current plan, 2026-10-26.** The operator chose four distinct new C++ projects for the three verifier pairs and the triple, preserving the three existing single-verifier baselines. This replaces the proposed nine-cell baseline re-port matrix and its repeated-port Axis B implementation plan. There will be **four new port workspaces, seven project workspaces total**, not 21. The source research and planning/backlog changes are authorized; final contracts, trust/risk acceptance, protected writes and toolchain setup remain explicit checkpoints at #161 and the later owning issues.

This file is the local authoritative P4 plan. The historical external master-plan path is missing; no unrelated file has been substituted. Earlier P1–P3 history and accepted decisions remain intact. The pre-revision matrix/backlog are retained under [planning history](planning/p4-mixed-2026-10-26/historical/VERIFIER-MATRIX-before-four-projects.md) and [backlog snapshot](planning/p4-mixed-2026-10-26/backlog-before.json).

## Portfolio and physical isolation

| ID | Distinct upstream project | Verifiers | Planned independent Git/Ligature root | Main new coverage |
|---|---|---|---|---|
| M4 | [Boost.ICL](https://github.com/boostorg/icl) | Creusot + Verus | `icl-creusot-verus/` | Interval/set/map algebra, generic endpoint laws, split/coalesce and representation/iterator invariants |
| M5 | [TinyXML2](https://github.com/leethomason/tinyxml2) | Creusot + Kani | `tinyxml2-creusot-kani/` | Recursive UTF-8 parsing, entity arithmetic, mutable DOM ownership, bounded scanner/memory paths |
| M6 | [Snappy](https://github.com/google/snappy) | Verus + Kani | `snappy-verus-kani/` | Raw compression format, overlapping copies, tag/varint state, actual SIMD/unaligned fast paths and scalar fallbacks |
| M7 | [LevelDB storage-format slice](https://github.com/google/leveldb) | Creusot + Verus + Kani | `leveldb-three-verifiers/` | Ordered state and callbacks, log fragmentation, prefix-compressed blocks, CRC/codec checks and multi-component operation traces |

These directories are **planned only**. No new repo/submodule, descriptor, port crate, source checkout, shell or production proof has been created by this plan update. `date-creusot/`, `swisstable-verus/`, and `crypto-mixed/` stay distinct baseline records with their existing scope and actual completion/limitation status. In particular, SwissTable's remaining Ligature closure maintenance is not silently declared complete.

Each new root must be its own Git repository with a committed initial baseline before Stage 7, its own descriptor/write policy, upstream pin, native oracle, proof/results trees and findings/PORT-GAPS records. Registering submodules/pins in the operator-managed outer repository is a separate operator action. Separate Cargo roots/toolchain files within a mixed project do not create extra top-level port workspaces. There must be no shared mutable manifest, ledger, closure directory or proof output between project roots. If shared source interfaces are needed, declare their ownership, revision and proof/TCB implications explicitly.

## Selection evidence and immutable upstream pins

These are deliberately selected reproducible release snapshots, **not claims to be the latest releases**. Official tag refs were resolved read-only and selected source/test files inspected. The [pin manifest](planning/p4-mixed-2026-10-26/upstream-pins.json) stores exact ref results; the [source-review inventory](planning/p4-mixed-2026-10-26/source-review.json) stores immutable URLs, byte counts and SHA-256 hashes. Suitability/ownership below is an engineering hypothesis, not a demonstrated Rust proof or native build.

| Project | Selected tag | Resolved commit |
|---|---|---|
| Boost.ICL | `boost-1.88.0` | `2741c3a1b7b79f7326360c26c3e1588b385c9e53` |
| TinyXML2 | `11.0.0` | `9148bdf719e997d1f474be6bcc7943881046dba1` |
| Snappy | `1.2.2` | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
| LevelDB | `1.23` | `99b3c03b3284f5886f9ef9a4ef703d57373e61be` |

The four projects expose complementary mechanisms, rather than four similar arithmetic demos. Boost's [official ICL documentation](https://www.boost.org/doc/libs/1_88_0/libs/icl/doc/html/index.html) describes interval sets/maps and aggregation; the pinned [TinyXML2 documentation](https://github.com/leethomason/tinyxml2/blob/9148bdf719e997d1f474be6bcc7943881046dba1/readme.md) describes its DOM, UTF-8, memory ownership and normalization; [Snappy's format/source](https://github.com/google/snappy/blob/6af9287fbdb913f0794d0148c6aa43b58e63c8e3/snappy.cc) exposes overlapping and vectorized copy paths; LevelDB's [log format](https://github.com/google/leveldb/blob/99b3c03b3284f5886f9ef9a4ef703d57373e61be/doc/log_format.md) and [table format](https://github.com/google/leveldb/blob/99b3c03b3284f5886f9ef9a4ef703d57373e61be/doc/table_format.md) provide storage-state interfaces with native tests.

A full generic configuration/TOML parser, full database engine or full Boost distribution port would add breadth without a bounded first proof target. A checksum-only project would add less structural coverage than Snappy plus LevelDB's CRC path. No claim of mathematically optimal coverage is made: this is a coverage-first portfolio with explicit fit gates, and a failed fit must be recorded rather than hidden by a tiny replacement scope.

## M4: Boost.ICL — Creusot + Verus

**Selected vertical slice:** discrete interval algebra and canonical interval sets/maps. Include empty/singleton/open/closed endpoints, union/intersection/difference, insertion/erasure, split/coalesce, membership and segment iteration. Start with `i32` and `i64` endpoint instantiations and an explicit additive integer map codomain. Specify overflow, identity absorption and joining versus splitting semantics. Attempt generic endpoint/combiner law obligations; do not present one scalar instantiation as a port of generic C++ templates.

**Ownership hypothesis:** Creusot owns endpoint/order/interval algebra and high-level set operations; Verus owns canonical segment storage, mutation, split/coalesce and representation/iterator invariants. Real call candidates exist in [interval_base_set.hpp](https://github.com/boostorg/icl/blob/2741c3a1b7b79f7326360c26c3e1588b385c9e53/include/boost/icl/interval_base_set.hpp): `add` calls `_add`, and mutation consults `icl::is_empty` and interval subtraction helpers. `interval_set.hpp` delegates to segment joining helpers. The fit task must assign exact real functions so C→V and V→C are covered; mathematical dependency alone is not a fabricated runtime edge.

**Native oracle:** build the matching Boost dependency distribution and verify the ICL module SHA. The pinned `test/Jamfile.v2` enumerates interval/set/map suites. Compare native operations, pointwise denotation AND canonical segment/iteration results for each selected style; add seeded operation traces, algebraic laws, extreme endpoints and split/join mutants. Pin dependent Boost modules and test/build tools during intake, not merely this module tag.

**Initial exclusions:** all of Boost, continuous/floating endpoint semantics, arbitrary allocator/comparator/codomain policies, pointer/iterator address identity and performance parity. Unsupported generic features remain named transfer gaps. A changed representation must preserve selected observable semantics and must not inherit upstream complexity claims without evidence.

## M5: TinyXML2 — Creusot + Kani

**Selected vertical slice:** in-memory UTF-8 XML parsing plus an explicit DOM mutation/clone/serialization facade: elements, attributes, text, comments, declarations, CDATA, predefined/numeric character references and newline/whitespace modes. Stage the scope if necessary, but enumerate every omitted feature. Preserve the pinned implementation's actual errors and normalization instead of silently substituting a stricter XML interpretation.

**Ownership hypothesis:** Creusot owns parser progress/recursive structure, DOM parent/sibling/ownership invariants, serialization and UTF32→UTF8 conversion. Kani owns bounded string normalization/entity scanning and length/radix/overflow buffer paths. In the [pinned source](https://github.com/leethomason/tinyxml2/blob/9148bdf719e997d1f474be6bcc7943881046dba1/tinyxml2.cpp), DOM value access calls `StrPair::GetStr`/entity processing (C→K), while `XMLUtil::GetCharacterRef` calls `ConvertUTF32ToUTF8` (K→C). These are candidate real boundaries; exact Rust contracts/representation require fit and human review.

**Native oracle:** compile `tinyxml2.cpp`, `tinyxml2.h` and `xmltest.cpp`; translate selected `resources/`/`test/` cases. Compare typed DOM events, ordered attributes, selected valid mutation traces, serialization where defined, error classes and line numbers. Fix whitespace mode and depth/resource limits in every case. Exercise malformed/truncated input, long numeric references, Unicode boundaries, recursion and stale-handle prevention.

**Initial exclusions:** DTD/XSL (outside upstream TinyXML2's stated support), claims of complete XML-standard conformance, raw C++ pointer identity, invalid-pointer traces and all OS file behavior. Rust arena/handle/lifetime decisions must be documented; bounded Kani input/depth assumptions must remain visible.

## M6: Snappy — Verus + Kani

**Selected vertical slice:** raw Snappy block encode/decode, length/varint/tag parsing, literal and all three copy-tag forms, overlapping backreferences and malformed stream rejection. Establish scalar functional semantics, then port and attempt checking of at least one real optimized copy/shuffle path from the pinned source. Model initialized data, slop bytes, offset/length/output bounds and alignment honestly.

**Ownership hypothesis:** Verus owns decoder/state/reconstruction invariants and portable `IncrementalCopySlow`; Kani owns bounded optimized `IncrementalCopy`, vector/shuffle/unaligned and tail paths compared against scalar semantics. In [snappy.cc](https://github.com/google/snappy/blob/6af9287fbdb913f0794d0148c6aa43b58e63c8e3/snappy.cc), decoder/writer `AppendFromSelf` calls optimized copy (V→K), and optimized copy falls back to `IncrementalCopySlow` for tight tails (K→V). This gives a substantive fast-path versus functional-proof boundary.

**Native oracle:** build `snappy_unittests`, selected corrupted-input tests and shipped `testdata/`; use native Compress/Uncompress. Cross-decode native/Rust streams and compare decoded bytes, lengths and rejection behavior. Do not assume all valid compressors produce identical compressed bytes; the format is not a canonical encoding contract. Mutate zero/too-large offsets, copy lengths, truncated tags, one-byte repetition, tight tails and vector boundaries.

**Initial exclusions:** framed/container formats, other codecs, every ISA, throughput parity and unbounded Kani claims. At least one actual optimized implementation must be attempted. Unsupported intrinsics are a finding, not permission to stub the path and call it proved. Rust `MaybeUninit` or unsafe-buffer use needs its own explicit initializedness argument; a shadow model alone is not proof of actual uninitialized-memory safety.

## M7: LevelDB storage slice — Creusot + Verus + Kani

**Selected vertical slice:** a joined in-memory storage-format pipeline: WriteBatch Put/Delete and parsing/handler effects, log writer/reader fragmentation/checksum/truncation/error handling, prefix-compressed block builder/reader and restart seek/iteration, plus replay into a specified logical map. The selected interfaces must compose into one observable pipeline, not three disconnected proof demos.

**Ownership hypothesis:** Creusot owns ordered-map/operation-history semantics and handler/replay state; Verus owns block representation/restart/seek, log framing/reassembly and parser progress; Kani owns bounded fixed/varint codecs, CRC32C/masking and local buffer/fault checks. [WriteBatch::Iterate](https://github.com/google/leveldb/blob/99b3c03b3284f5886f9ef9a4ef703d57373e61be/db/write_batch.cc) dispatches real Handler callbacks; [log writing](https://github.com/google/leveldb/blob/99b3c03b3284f5886f9ef9a4ef703d57373e61be/db/log_writer.cc) and reading use coding/CRC helpers; [block building](https://github.com/google/leveldb/blob/99b3c03b3284f5886f9ef9a4ef703d57373e61be/table/block_builder.cc) uses varint/fixed encoders. Intake must freeze the exact ownership/call map and trace all three kinds of evidence into the selected flow.

**Native oracle:** native `db/log_test.cc`, `table/table_test.cc` and a wrapper over the selected modules. Compare batch/log/read/replay and block-build/seek traces with an in-memory Env/handler. Include short writes, truncated fragments, checksum errors and malformed batches. Preserve partial handler effects on corruption: do not assume WriteBatch parsing rolls back prior callbacks. Disable compression for this initial slice so the project is independent of the separate Snappy Rust port.

**Initial exclusions:** full DB API, compaction scheduling, concurrent writers, filesystem durability, real crash consistency, snapshots and all platform Env implementations. `Flush` is not `Sync`. In-memory bounded fault injection cannot establish OS persistence or linearizability. Compatibility applies to selected formats/options only.

## Coverage obligations and what counts

| Coverage objective | Primary project(s) | Required evidence |
|---|---|---|
| Deductive/deductive composition; generic algebra | M4 | Real C↔V function edges, endpoint/codomain assumptions, multiple concrete instances and generic law attempts |
| Deductive/bounded parser/tree composition | M5 | Real C↔K paths, DOM/tree invariants, bounded malformed-input cases and native normalization/error oracle |
| Deductive/bounded optimized memory composition | M6 | Real V↔K fast/fallback paths, one actual optimized-variant attempt, bounds/init/alignment/overlap model |
| Three verifiers in one actual project | M7 | Joined batch/log/block pipeline, three source-bound assurance kinds, real contracts/call edges and native trace comparison |
| All six directed pairs | M4, M5, M6 | C→V, V→C; C→K, K→C; V→K, K→V. Source references and achieved records, not reciprocal labels |
| C++→Rust differences | All four | Representation/ownership/templates/iterators/callback/ISA/error/overflow gaps in both findings and PORT-GAPS; no silent scope cuts |
| Supporting evidence vs required/assumed dependencies | All four | Reuse #159 semantics; project-specific variations only where they add evidence. Exact evaluated scope, trust policy and global CG3 effects |
| CG6 / G15 | M7 real-graph audit; isolated labelled synthetic controls if needed | Real cross-cluster SCC/protocol evidence where present; otherwise disclose absence and keep synthetic gate fixtures distinct from production source claims |

Three modules do not by themselves constitute a non-pairwise protocol. Ordinary recursion is not automatically a cross-cluster SCC. Audit the real LevelDB callbacks and state history first. If the selected slice lacks a genuine CG6/G15 case, exercise clearly labelled synthetic discharge/debt controls under this same M7 project root (archived or isolated scratch manifests), not a fifth C++ project or an invented claim about LevelDB. Positive discharge/protocol-debt acceptance remains human work. There is no requirement to port an entire database to exercise a gate.

## Assurance and execution rules

- Reference release: verified Ligature 1.4.3, SHA-256 `1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`. Use each root's own approved bundle; later upgrades require explicit verification. Do not inspect the Ligature source checkout or zipapp contents.
- A fitting project is not a proved port. Each intake stage must build the native oracle, audit real call boundaries and propose contracts/domains/TCB and representation before implementation. Scope cuts, skipped optimized paths and unsupported generic laws remain findings requiring explicit disposition.
- Matching Nix toolchains, isolated Cargo/target/proof roots, and required local Why3 solver sockets must be reproducible in setup. Operator decision (2026-11-14): use the demonstrated matching Creusot/creusot-std 0.12.0-dev Nix pair with nightly-2026-04-21 for P4. This does not validate the declared 0.14 shell mismatch, which remains a separate finding on epic #2. The external Creusot companion-output check remains a setup prerequisite.
- Per-owner proofs do not prove cross-verifier composition. Required mixed edges trigger CG1. With Kani present, the current CG3 audit affects the whole project workspace. Pair and triple results must report actual partial/bounded/degraded outcomes and exact scopes; no unqualified mixed deductive claim or borrowed scratch risk approval.
- Operator decision (2026-11-14): partial/bounded/degraded outcomes may be reported and considered only through a later explicit per-record human ruling; no production risk is accepted now, and no #159 scratch ceiling is inherited. #159's scratch record demonstrates one record/one ceiling covering CG1+CG3; it is not production risk acceptance. Do not introduce a trusted assumption merely to turn a gate green.
- Operator decision (2026-11-14): draft narrow project-facing specs for dependency APIs used by selected project source, without verifying dependency implementation source. List every such spec as a trusted TCB assumption and require human review before it supports a proof claim.
- Native oracle agreement and mutation tests falsify discrepancies; they do not replace proofs. Retain source/tool revisions, exact inputs/outputs/exits/bounds and source bindings for every claim. Archive copied `_closure` evidence directories instead of leaving active trees under analysis.
- The current task changes planning and backlog only. No new root initialization, source port, protected file, source checkout in a planned workspace, Nix install, flake edit, grant, approval, promotion, commit or push is authorized or performed merely by updating this plan.

## Remaining #161 choices and setup gate

The operator has approved the four mixed-verifier assignments and project-source coverage boundary, while preserving the three single-verifier baselines. The project slices in this plan are the approved coverage direction; exact source function/call maps and contracts are intake evidence and retain their normal human review. The operator has also approved four independent project roots, verifier-specific Cargo roots/locks/toolchains/targets/proof outputs, the matched Creusot 0.12.0-dev Nix pair for P4, drafting narrow dependency specs as reviewed TCB assumptions, and case-by-case human review of any partial/degraded result without accepting production risk now. The earlier M7 direction also stands: inspect the real graph/protocol and use clearly labelled synthetic controls under M7 only if needed; no fifth project.

Operator decision (2026-11-14): approve the proposed #177 write-set design and the current #169-#174 issue scopes as written. The four named project roots are distinct ownership boundaries. Worker-authored files are limited to project source/tests, oracle, analysis, and findings/PORT-GAPS content. Descriptors/write policies, protected Cargo manifests and locks, nested toolchain files, and outer-repository submodule registration remain operator-managed or use a sanctioned command with an exact issue/path grant. Build targets go under task-specific `/tmp` roots; durable proof and evidence outputs remain separate per tool under each project. This design approval issues no path grants. #177 must enumerate the exact per-root paths and creation routes before protected writes.

The #169-#174 descriptions are specific enough for worker handoff after their stated project evidence prerequisites: supporting-evidence configurations; same-closure composition and per-record ceilings; required versus assumed edges; six directed pair edges; the LevelDB triple assessment; and the four-project roll-up. Their scopes are approved as written. Exact function/call maps and proposed contracts remain intake evidence with the issue-local human review before implementation or proof claims.

No #161 scope, trust-policy, setup-design, or closure-policy choice remains unanswered. This does not issue a protected-path capability, accept a production risk, or waive setup prerequisites. The separate 0.14 shell mismatch remains on epic #2, and the external Creusot companion-output check remains required before production use.

The older pending P1 Kani C002/P2 alternative owner/P3 alternative owner choices belonged to the cancelled baseline re-port expansion and no longer gate this phase. Existing baseline rulings are not reversed. #161 remains open; new setup/implementation tasks remain blocked behind it. Each intake stage also retains its normal contract-review checkpoint.

The actual active backlog and stage IDs are in [backlog-map.json](planning/p4-mixed-2026-10-26/backlog-map.json). Four project epics each have native intake/oracle, owner implementation/assurance, and real-boundary/evidence handoff stages. Run them in the designated serial order, then reconcile supporting/mixed/split/six-direction results, exercise the M7 CG6/G15 controls, and assess the final M7 workspace before the roll-up. Reuse unchanged recent results rather than rerun them to satisfy another issue number.

Original #163–#168 are closed **as superseded unimplemented scope**, not completed ports. Original #162 remains baseline Verus-closure maintenance, deferred after the four-project roll-up; it does not add a fourth verifier configuration to a baseline or block the new ports' source work. Later cross-cutting checks still receive both the portfolio and baseline maintenance evidence.

## Current execution issue map

#161 remains open. #177 is the later operator-controlled setup gate. Each project epic below groups three explicitly ordered leaf stages.

| Project | Epic | Intake / native oracle | Owner implementation / assurance | Real-boundary handoff |
|---|---|---|---|---|
| M4 Boost.ICL | #178 | #179 | #180 | #181 |
| M5 TinyXML2 | #182 | #183 | #184 | #185 |
| M6 Snappy | #186 | #187 | #188 | #189 |
| M7 LevelDB storage slice | #190 | #191 | #192 | #193 |

Then #169 supporting evidence → #170 same-closure results → #171 required/assumed edges → #172 six directions → #194 M7 CG6/G15 controls → #173 final LevelDB triple assessment → #174 portfolio roll-up. Original #162 baseline closure maintenance follows the roll-up and precedes #55 cross-cutting work. #67–#69 deliverables now explicitly include all seven project/configuration records.

## AST report review and execution gates

The callgraph benchmark workspace and `docs/combined-tools/FULL-LIGATURE-HANDOFF.md` were supplied and reviewed as the AST report on 2026-11-14 UTC. The report establishes a measured tool-selection recommendation and a reproducible CodeQL fixture smoke, not a full-Ligature intake result or a P4 project analysis. The AST report-wait is cleared. Review details, exact invocation templates, evidence identities, and limits are recorded in [ast-tool-review.md](planning/p4-mixed-2026-10-26/ast-tool-review.md).

This does not authorize mixed-port workspace setup or implementation, select a production provider, or resolve #161's remaining operator choices. In particular, project-specific C++ build capture, queries, citation review, evidence ingestion, and freshness checks remain prerequisites for any later porting use. #161 remains open and #177 remains blocked by #161.
