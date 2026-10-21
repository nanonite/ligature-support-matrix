# C++ → Rust/Verus port gaps — SwissTable (superseded draft)

This planning copy is superseded by the reviewed final document at `PORT-GAPS.md`. It is retained as drafting history only; do not use its entries or status statements as current evidence. Upstream references are pinned to Abseil commit `2065f4ded0558c6f89fee67c8e5228feb4eb960e` (tag `20260817.0`; `upstream/upstream-pin.json`). The final document and `findings/limitations.jsonl` are the current records.

### Automatic growth and sized reservation are removed from insertion (`swisstable-verus-009`)
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:155-165` describes insert finding a key and growing when overcrowded; `raw_hash_set.h:3677-3713` calls `PrepareInsertLarge`; `raw_hash_set.cc:2369-2393` selects the slow growth/deleted-slot path using `GrowthInfoAccessor`; `raw_hash_set.cc:2344-2366` sizes `ReserveTableToFitNewSize` from the requested size.
- **What the Rust port does instead:** `src/swiss_table.rs:218-223` requires `has_free_slot()` before `insert`; `:414-455` exposes separate `reserve(additional)` but ignores `additional` and increments `capacity_bits` by one. `src/raw_table.rs:790-800` expressly does not resize on insertion.
- **Why:** The port isolates `resize` as an explicit verified boundary and does not implement Abseil's growth policy/metadata. The operator's 2026-10-02 ruling, recorded in the source comments, accepts the insertion-path cut; the ledger's earlier `blocker` describes the pre-ruling request.
- **Impact:** A caller must explicitly reserve before insertion; full/overcrowded insertion and reserve-for-N behavior are not parity-compatible. Rehash is reachable through `reserve`, not through `insert`. A successful explicit resize is not proof of insertion-driven rehash.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-009`.
- **Generalizable lesson:** Porting `insert` without its load-factor transition makes capacity management a new caller obligation, even when a standalone resize exists. Test operation sequences, not merely individually available methods.

### A spec-valued ghost field cannot be initialized by this executable constructor (`swisstable-verus-011`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272` defines a policy-parameterized container whose real slot state is initialized and updated by constructors/operations; `raw_hash_set.h:3691-3710` obtains a slot through the policy-backed insert path.
- **What the Rust port does instead:** `src/raw_table.rs:189-198` stores executable `ControlBytes` and `Vec<u64>` hashes; `:530-552` derives `stored_hashes()` by `Set::new` over full slots rather than maintaining a `ghost live: Set<u64>` field. `src/swiss_table.rs:20-23` similarly derives its model.
- **Why:** On the pinned Verus 0.2026.05.24, initializing an executable struct with `Set::empty()` or `Ghost::new(Set::empty())` failed mode checking, as documented by `swisstable-verus-011`. This is a limitation of this attempted construction, **not** a proof that every possible ghost encoding is impossible.
- **Impact:** No persistent abstract set is kept in lockstep with writes; the derived model's membership is provable but set-level frame/equality obligations become difficult (next entry). The executable slot abstraction remains a subset of Abseil's policies.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-011`, `swisstable-verus-017`, `swisstable-verus-023`.
- **Generalizable lesson:** Before designing a refinement proof around an updatable ghost collection, type-check its constructor in the target verifier's execution mode. A derived model avoids ghost initialization but moves cost into quantifiers and framing.

### Derived-set extensionality exceeds the chosen proof budget (`swisstable-verus-023`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:155-165` promises insert without losing other elements; `raw_hash_set.cc:2104-2144` transfers slots during resize. The set-level preservation property is a *port specification* of those operations, not a C++ `Set::new` construct.
- **What the Rust port does instead:** `src/raw_table.rs:20-42,530-552,790-825,998-1011` uses per-slot/frame and count contracts, and bidirectional **per-slot survival** for resize, rather than `stored_hashes() =~= old(stored_hashes()).insert(k)` or resize set equality. `src/swiss_table.rs:32-40` applies the same ruling at the container boundary.
- **Why:** Four measured variants failed to close or regressed: `assert_sets_equal!` plus `group_set_axioms`, an existential trigger, inline proof via `lemma_stored_in`, and pointwise `stored_in` postconditions (55→57 primary error locations in the former verification state). Membership via `lemma_stored_in` verifies; two-directional equality over the existential `Set::new` does not follow automatically. A mid-mutation `model()` invariant is actually false in write windows. The operator ruled set-level extensionality out of scope on 2026-10-02, rather than authorizing a fifth retry.
- **Impact:** The narrowed contracts capture named-slot updates and counts, not the original abstract-set equality; an independent equivalence proof is still absent. The current crate run verifies the re-scoped contracts, while the stronger derived-set equality remains a separate limitation and is the subject of the post-#30 tracked-Map probe.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-011`, `swisstable-verus-017`, `swisstable-verus-023`, `swisstable-verus-013` (older pre-ruling count).
- **Generalizable lesson:** A verifier may prove membership in a derived collection without proving extensional equality across mutation. Record which abstract property was dropped, preserve a useful pointwise contract, and never present weaker verified clauses as proof of the former contract.

### Erase's `kEmpty`/`kDeleted` choice was initially misdiagnosed; corrected at the pinned revision (`swisstable-verus-021`)
- **Category:** Semantic divergence (historical, fixed).
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:708-723`, `WasNeverFull`, uses `is_single_group` or two `Group(...).MaskEmpty()` windows and a `TrailingZeros()+LeadingZeros()<Group::kWidth` test; `:868-883`, `EraseMetaOnlyLarge`, writes `kEmpty` if true and `kDeleted` otherwise. `growth_info().OverwriteFullAsEmpty/Deleted()` at `:877/:881` **updates accounting after** the choice; it is not read by `WasNeverFull`. Calls originate at `raw_hash_set.h:3482-3497`.
- **What the Rust port does instead:** Earlier it always wrote `kDeleted` and the ledger claimed the test needed a missing growth-history field. Current `src/control_bytes.rs:272-315,563-680` implements the control-byte test; `src/raw_table.rs:882-968` calls it and chooses `set_empty`/`set_dead`. The source documents the corrected interpretation explicitly. The separate growth-left accounting still has no equivalent (see next entry).
- **Why:** The original reading conflated branch-condition inputs with side effects in the two branch arms. The source also documents a subsequent erroneous transcription of the mask-count condition (`src/control_bytes.rs:293-302`), replaced by the `fwd+bwd<width` formula.
- **Impact:** Tombstone-always changed control-byte state, empty count and growth pressure; the present code restores the *erase byte decision*. This does not yet constitute a C++/Rust differential test or a clean proof of every table operation.
- **Status:** fixed.
- **Finding ids:** `swisstable-verus-021` (historical ledger entry); the corrected mask transcription is called `swisstable-verus-030` in the current source, but was not present in the inspected limitations ledger, so that ID must be reconciled before transfer.
- **Generalizable lesson:** Read the exact predicate and its caller at the pinned revision before declaring an upstream optimization unportable. A nearby metadata write is not evidence that the predicate reads that metadata; retain corrected gap history rather than silently deleting the false claim.

### Growth-left, deletion bookkeeping and insertion policy remain absent
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:2369-2393` branches on `growth_info.GetGrowthInfoLowerBound().HasNoDeletedAndGrowthLeft()`, decrements growth accounting and may use `PrepareInsertLargeSlow`; `:2344-2366` computes remaining growth on reserve; `:875-882` updates growth info after erase.
- **What the Rust port does instead:** `src/raw_table.rs:189-198` tracks control bytes, hashes and length, but no Abseil growth-left or deleted-slot budget; `src/swiss_table.rs:414-455` grows on explicit reserve without Abseil's threshold or sizing policy.
- **Why:** Proof-focused subset chooses capacity/slot invariants instead of allocator and load-factor metadata. This is distinct from the **fixed** `WasNeverFull` byte choice: its predicate does not require growth metadata, but upstream's subsequent scheduling/accounting does.
- **Impact:** Different growth timing, capacity and probe costs; an oracle comparing only membership can miss it, while a capacity/control-byte or allocation trace will expose it.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-009`, `swisstable-verus-021` (the corrected distinction).
- **Generalizable lesson:** Separate the correctness decision for a slot transition from the auxiliary accounting that determines when later operations rehash. Restoring the first does not restore the second.

### SIMD groups are replaced by scalar sixteen-byte loops (`swisstable-verus-002`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/hashtable_control_bytes.h:277-345` (`GroupSse2Impl`, unaligned 128-bit load, compare/movemask, saturated subtraction); `:361-438` (`GroupAArch64Impl`, **8-byte** NEON group, not `GroupArmNeonImpl`); `:441-460` portable **8-byte** group; `:504-521` selects implementations by architecture. These names and widths are from the pinned checkout, not a previous SwissTable API.
- **What the Rust port does instead:** `src/group_probe.rs:1-23,146-207,210-235` builds `u16` masks one bit at a time over `GROUP_WIDTH=16` (`src/control_bytes.rs:33-38`), without intrinsics, target features or `unsafe`.
- **Why:** The Verus-facing implementation models byte and bit-mask semantics rather than architecture-specific vector loads; the separate SIMD scope/Kani decision remains outside this port.
- **Impact:** No SIMD instruction/performance parity, and the portable/NEON 8-lane scheduling is not represented. For a fixed valid 16-byte window, masks are intended to encode the same byte predicates as the SSE2 path; this is **not** a measured runtime equivalence claim for every architecture, sentinel, or look-up trace.
- **Status:** open.
- **Finding ids:** `swisstable-verus-002`, `swisstable-verus-003`.
- **Generalizable lesson:** Proving a scalar mask abstraction does not port vector loads, platform dispatch or throughput. Record lane width, mask layout and architecture conditions before claiming a SIMD substitute is equivalent.

### Raw uninitialized slots and sanitizer lifetimes become initialized vectors (`swisstable-verus-001`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272` parameterizes `slot_type` and allocator via policy; `:3478-3497` separates metadata-only erase from destruction; `raw_hash_set.cc:505-516` poisons/unpoisons slot memory on control-byte transitions, and `:2104-2135` transfers and deallocates an allocated backing array. `raw_hash_set.h:2390-2409` dereferences and advances raw slot/control pointers.
- **What the Rust port does instead:** `src/raw_table.rs:11-18,189-198` has `ControlBytes` with `Vec<u8>` bytes, parallel initialized `Vec<u64>` hashes and no raw-pointer/`MaybeUninit` slot layer; `src/swiss_table.rs` separately stores `Vec<u64>` values. Erase zeroes the logical slot; resize builds a fresh table rather than transferring C++ object lifetimes in raw storage.
- **Why:** Safe, initialized Vec indexing yields Verus-friendly ownership and bounds obligations; a faithful unsafe representation would require separate memory-initialization, aliasing, destruction and sanitizer/lifetime arguments, not supplied here. The source's shorthand “`Vec<u64>` control bytes” is inaccurate: the actual control vector holds `u8`.
- **Impact:** Object lifetime, destructor effects, allocator behavior, poison/unpoison diagnostics, layout, peak allocation and pointer identity are not ported or proved. It is only a logical-slot model; zero is reserved as `NO_HASH` in this representation.
- **Status:** open.
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-003`.
- **Generalizable lesson:** A safe logical container may preserve membership while dropping physical lifetime and address semantics. Treat the storage refactor as a separate transfer gap, not as evidence that unsafe source code was verified.

### Probe-coverage proof is replaced by bounded probing and a full scan (`swisstable-verus-004`, `-006`)
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1751-1771` states triangular-probe group coverage (`(i²+i)/2` bijective modulo a power of two); `:1773-1789` advances the masked sequence; `:3393-3422` and `:3677-3713` use group masks for lookup/insertion.
- **What the Rust port does instead:** `src/raw_table.rs:640-710` bounds the group loop; its find path falls back to a linear scan, and `:790-834` checks for an existing key before `claim_first_free`; `src/swiss_table.rs:332-355` scans all slots for erase. The reference's `& capacity_mask` wrap is retained in `src/probe_seq.rs`, but group-coverage completeness is not proved.
- **Why:** A proof that the particular quadratic sequence visits all groups was outside the verified proof work; a bounded scan establishes absence/uniqueness without that number-theoretic induction.
- **Impact:** Lookup, duplicate detection and erase can cost O(capacity), rather than relying on expected group-probe behavior; logical results may match without algorithmic or timing parity. Not proof that the fast probe loop alone is complete.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-004`, `swisstable-verus-006`.
- **Generalizable lesson:** A mathematically correct probe progression is not the same as a machine-checked coverage theorem. If a linear fallback supplies correctness, disclose the new asymptotic path and retain the missing coverage obligation.

### Generic hash/equality, payload and collision policy specialize to `u64` identity (`swisstable-verus-008`)
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2200-2236` supplies policy, hasher, equality and allocator parameters; `:3691-3695` filters a tag match through `equal_to(key, slot)`; `:3730-3761` requires only **equal keys imply equal hashes**, not collision-freedom. `raw_hash_map.h:351-359` constructs or assigns a generic value.
- **What the Rust port does instead:** `src/swiss_table.rs:8-18,218-255` takes `u64` keys and values and identity hashes, while `src/raw_table.rs:80-83,790-795` refuses hash zero as `NO_HASH`.
- **Why:** Generic payload/lifetime/policy behavior and a `Map<K,V>` refinement would enlarge both executable and proof scope; the zero sentinel makes a simple `Vec<u64>` slot model possible.
- **Impact:** Key zero, generic types, nontrivial hash collisions/equality, heterogeneous lookup, value destruction and allocator hooks have no parity coverage. Do **not** repeat the source/ledger's implication that Abseil requires distinct keys to have distinct hashes; only equal-key hash consistency is required by the pinned C++.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-008`, `swisstable-verus-001`.
- **Generalizable lesson:** An injective identity hash can make proofs easier by eliminating collisions, but it changes the input domain and removes the very collision path a hash table must normally handle. State the restricted domain and the upstream contract separately.

### Pointer-based iterator validity becomes an index cursor (`swisstable-verus-001`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2390-2425` dereferences `(ctrl_,slot_)` pointers, checks generation/container validity and advances both; `:2431-2455` stores generation pointer and skips deleted controls; `:2753-2765` returns lifetime-bound begin/end iterators; `:3803-3817` can produce a non-iterable insertion iterator.
- **What the Rust port does instead:** `src/table_iterator.rs:1-25,39-81` keeps `offset_` and `capacity`, scans control bytes and ends at the sentinel. It does not hold a C++ slot pointer or generation guard.
- **Why:** Safe cursor/index verification avoids aliasing and pointer-lifetime/invalidation proof obligations that belong to the omitted raw-slot/generation layer.
- **Impact:** Iteration over full slots is modeled, but iterator dereference semantics, invalidation on rehash/erase, pointer stability and cross-container comparison diagnostics are not preserved or verified.
- **Status:** open.
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-008` (specialized value representation); iterator-specific ledger id not found in inspected `limitations.jsonl` and should be added before claiming the §6.5 both-ledgers requirement is met.
- **Generalizable lesson:** An index cursor can preserve visitation order/termination without being equivalent to a pointer iterator. Audit validity, generation and reference-lifetime guarantees separately from enumeration correctness.

### Rehash transfer algorithm and object relocation are simplified
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:593-653` documents and begins the in-place `DropDeletesWithoutResizeAndPrepareInsert` swap/tombstone chain; `:1610-1629` encodes probed elements when growing; `:2104-2144` also has a fresh-backing-array `ResizeAllocatedTableWithSeedChange` path that transfers slots, reseeds and resets growth accounting.
- **What the Rust port does instead:** `src/raw_table.rs:985-1015,1105-1120` maps old full slots into a fresh `RawTable` using logical hashes and ghost source/destination placement records. It does not implement same-capacity in-place swap chains, policy-driven relocation, allocator effects, reseeding or growth-info recalculation.
- **Why:** Initialized Vec-backed storage and proof-friendly per-slot records replace C++ raw move/swap and pointer arithmetic. The current direct-Verus `resize` slice verifies, but its internal placement and resource behavior remain different from the upstream algorithm.
- **Impact:** Preservation is specified per slot in both directions and the current resize slice verifies. Internal placement, memory use, object move/destruction effects and resize-performance parity still differ; Cargo integration and behavioral parity remain untested.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-013`, `swisstable-verus-019`; a dedicated transfer-algorithm finding should be logged.
- **Generalizable lesson:** “Rehash preserves elements” is only one property of a transfer path. Distinguish fresh allocation from in-place tombstone reclamation and prove relocation, ownership and resource behavior separately.

### Machine-word capacity and bitwise proof obligations need additional bounds and lemmas
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1773-1789` uses unchecked `size_t` masked arithmetic and an uncapped `index_ += Width`; `hashtable_control_bytes.h:291-343` computes masks with bitwise/vector operators.
- **What the Rust port does instead:** `src/probe_seq.rs` caps capacity bits, states explicit overflow guards and retains `& capacity_mask`; `src/group_probe.rs:163-207` builds a `u16` mask using `|`/`<<`. `verif/lemmas.rs` supplies bit-vector bridge lemmas. `src/control_bytes.rs` carries a conservative `0x7FFF_FFFF` capacity bound.
- **Why:** Verus integer-mode proofs need explicit `#[verifier::bit_vector]` facts for bounds; the pinned build's probes cannot directly establish `usize::MAX`/unbounded narrowing, though later bounded-cast lemmas in the current port recover some exact round trips. Initial reports that Verus had **no** bitwise model, or that `usize` had been proved 32-bit, were retracted.
- **Impact:** Smaller admitted capacity range and proof boilerplate; original masked operators and `u16` masks are retained, not replaced with modulo or boolean vectors. `GroupProbe::load` still mentions `usize::MAX` in an invariant; its proof status should be checked in the latest transcript, not inferred from an old probe.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-012`, `swisstable-verus-014`, `swisstable-verus-015`, `swisstable-verus-016`, `swisstable-verus-018`, `swisstable-spec-003`.
- **Generalizable lesson:** Distinguish “an operator is unsupported” from “this solver mode needs a lemma,” and test a non-tautological probe in the target binary before weakening a port. Bound casts explicitly rather than inferring machine width from a successful self-equality.

### Upstream slot/sentinel invariants were mis-stated by draft constraints
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1751-1768` describes mirrored bytes and slot-index wrapping; `:1530-1538` specifies `kDeleted→kEmpty`, `kEmpty→kEmpty`, full→`kDeleted`; `raw_hash_set.cc:434-443` implements that rewrite and restores sentinel/clones.
- **What the Rust port does instead:** `src/control_bytes.rs` implements the actual deletion rewrite; `src/group_probe.rs` bounds windows by `ctrl.bytes.len()` rather than by slot `capacity`, admitting sentinel/padding loads. Draft `ControlBytes.C006` incorrectly forbids deleted→empty; draft `GroupProbe.C001/C004` incorrectly require `base+16<=capacity` and forbid sentinel inclusion.
- **Why:** Concept-drafting confused logical slot count with allocated control-byte length and stated an inverse to the upstream tombstone reclamation. These are mistakes in generated/staged transfer specifications, not required differences in Rust.
- **Impact:** Approving the drafts as-is would forbid an actual upstream behavior and make the trailing group unrepresentable. The port follows source behavior, so a spec gate may reject the correct implementation.
- **Status:** open.
- **Finding ids:** `swisstable-spec-001`, `swisstable-spec-002`.
- **Generalizable lesson:** Review generated invariants against sentinel, padding and state-transition truth tables before proof work. A formally precise draft can still be precisely false about its source.

### Erase call ownership was misplaced in a staged boundary draft
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:3482-3497` dispatches `erase_meta_only`; `raw_hash_set.cc:856-883` has the erase helpers own metadata/control updates, not the outer container pre-writing the tombstone.
- **What the Rust port does instead:** `src/swiss_table.rs:300-310` delegates to `RawTable::erase`; `src/raw_table.rs:915-968` writes the chosen control byte. The staged `specs/_boundaries/swiss_table_erase__to__control_bytes_set_dead.json.draft` demands a nonexistent container→control-byte call and remains protected; the Stage-7 manifest does not declare this edge.
- **Why:** A draft boundary inferred a call at the wrong abstraction level. An earlier port followed it and invalidated `RawTable::erase`'s `model()` precondition before the callee ran.
- **Impact:** Following the draft makes the erase proof inconsistent; following C++ leaves a staged boundary unrealized until re-drafted. The implementation-level misstep was fixed, not the upstream/spec mismatch.
- **Status:** open.
- **Finding ids:** `swisstable-spec-008`, `swisstable-verus-020`.
- **Generalizable lesson:** A call-graph edge is an ownership claim. Cross-check each staged boundary against the pinned C++ callee before structuring a verifier precondition around it.

### C++ header indexing and Rust call extraction cannot certify transfer edges
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272,3677-3713` defines template-scoped calls; `hashtable_control_bytes.h:277-345,361-438` holds SIMD group methods; `raw_hash_set.cc:593-653,708-723` holds rehash/erase control flow.
- **What the Rust port does instead:** The source was inspected directly; no claim of call-edge completeness is based on `codesight-mcp`'s index or `ligature extract-c-static`'s Rust-only extraction. `swisstable-verus/README.md:110-149` and `analysis/codesight/README.md` record the analysis limits.
- **Why:** codesight treated indexed `.h` as C, lost class scopes, silently omitted 202 headers/24 `.inc` files and emitted false cross-header edges; the ligature extractor scanned Rust impl-method calls and did not parse upstream C++. Some initial missing-name probes also used names absent at this 2026 pin, so not every `Symbol not found` is an index defect.
- **Impact:** A tool's successful index or a negative symbol search cannot prove that a C++→Rust edge is absent, nor can two non-overlapping analyses establish parity. In the recorded 63-edge hand-verified sample, only 28 edges were recovered by the C++ analysis artifacts.
- **Status:** open.
- **Finding ids:** `swisstable-mcp-001`, `swisstable-mcp-002`, `swisstable-mcp-003`, `swisstable-mcp-004`, `swisstable-mcp-013`, `swisstable-mcp-015`, `swisstable-mcp-016`, `swisstable-mcp-018`.
- **Generalizable lesson:** Validate a cross-language index's language detection, file census and symbol-version names before relying on its call graph. An exit-zero index is not evidence of complete C++ header coverage.

### Differential oracle parity is not established by an upstream passing baseline
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:155-174,3393-3422,3677-3713` covers observable insert/find/erase behavior; `raw_hash_set.cc:708-723,868-883` controls post-erase states. The pinned upstream baseline is 242/242 passing CTest suites (`upstream/upstream-pin.json:32-40`), not a Rust comparison.
- **What the Rust port does instead:** The inspected `oracle/oracle-PROTOCOL.md` defines a pinned C++ golden-driver/case map, but the inspected README describes #32 as future differential work; no comparison result is asserted here. The port specializes keys, capacity, growth and unsafe slots as above.
- **Why:** Upstream's tests and a verifier transcript answer different questions from a shared-input C++/Rust oracle. Host hash values and pointer/allocator observations need an explicit common representation or an exclusion, and zero/collision/growth cases may not be admissible in the Rust API.
- **Impact:** No measured behavioral parity follows from 242 passing C++ suites or from partially verified Verus obligations. Cases outside the Rust domain must be marked explicitly unmapped/excluded, not counted as matches.
- **Status:** open.
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-002`, `swisstable-verus-004`, `swisstable-verus-008`, `swisstable-verus-009`, `swisstable-verus-021`; a dedicated oracle-parity finding should be logged once #32 establishes its actual coverage.
- **Generalizable lesson:** A green source-suite baseline pins the reference, not the translation. Parity requires a shared operation schema, comparable domains and recorded exclusions for physical effects that cannot be normalized.

### Protected Cargo metadata forces a direct verifier invocation (`swisstable-verus-010`)
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272` is the template component under translation; its upstream build/test baseline was established with CMake at the pinned commit (`upstream/upstream-pin.json:15-40`). There is no corresponding C++ `Cargo.toml` construct; this is a *translation-workspace* gap, not a source-language semantic mismatch.
- **What the Rust port does instead:** `analysis/verus/run-verus.sh` invokes `verus --crate-type=lib` directly on `src/lib.rs` because the declared crate directory lacks `Cargo.toml` and the descriptor protects `rust/*/Cargo.toml`; `README.md:1255-1263` records the choice.
- **Why:** The protected write set forbids creating the manifest normally required by `cargo verus verify`, even though Rust modules are available to direct Verus.
- **Impact:** Direct proof runs can cover the crate modules but do not establish Cargo build/test/nextest integration or generated oracle parity. A green direct Verus run is not evidence of a Cargo package.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-010`, `swisstable-mcp-019` (earlier extractor lifecycle ordering).
- **Generalizable lesson:** Confirm that the target build metadata can actually be created within the allowed write set before promising Cargo-based verification. A direct verifier invocation can unblock proofs without silently crossing protected roots.

### A plausible rehash invariant was false inside the control-byte rewrite window (`swisstable-verus-019`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1530-1538` declares deleted→empty and full→deleted; `raw_hash_set.cc:434-443,604-645` rewrites metadata *before* moving the still-live slot payloads in `DropDeletesWithoutResizeAndPrepareInsert`.
- **What the Rust port does instead:** `src/raw_table.rs:360-405` defines `reclaiming_model(before,before_hashes)` for the transient state, rather than asserting the normal `model()` through `clear_dead`; `:985-1015` uses a fresh-table transfer. The current source additionally corrects an `is_full`↔pre-reclaim-full claim to `is_dead`↔pre-reclaim-full (`:370-400`).
- **Why:** Once a full control byte becomes `kDeleted`, its stored hash has not yet moved or been zeroed: `!is_full(i) ==> slot_hash(i)==NO_HASH` is *false*, not merely too hard for SMT. The later `is_full` predicate on the reclaimed array was likewise the wrong state classifier.
- **Impact:** An impossible loop invariant blocked resize proof and made attempted lemmas misleading; the revised predicate states the transition window honestly. The final per-slot preservation obligations now verify in the 150/0 crate run.
- **Status:** fixed for the scoped resize proof (false invariant corrected and witness bridges discharged).
- **Finding ids:** `swisstable-verus-019`; the source labels the later correction `swisstable-verus-031`, which was not yet present in the inspected ledger and needs reconciliation.
- **Generalizable lesson:** Model intermediate representation states explicitly when a port separates metadata updates from payload moves. Before adding solver hints to an invariant, check whether it is true immediately after each write.
