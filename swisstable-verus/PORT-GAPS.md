# C++ → Rust/Verus port gaps — SwissTable

Pinned upstream references below are relative to `upstream/abseil-cpp/` at commit `2065f4ded0558c6f89fee67c8e5228feb4eb960e` (tag `20260817.0`; see `upstream/upstream-pin.json`). Port references are relative to `rust/swisstable-verus-core/`. This document records the accepted scope cuts, implementation divergences, proof limitations, and transfer-tool gaps for the port; each entry links to `findings/limitations.jsonl`.

The scoped direct-Verus crate run reports **149 verified, 0 errors** (`analysis/verus/verus-transcript.txt`, captured by `analysis/verus/run-verus.sh`; the same counts come back through `cargo verus verify` in `analysis/verus/cargo-transcript.txt`, captured by `analysis/verus/run-cargo.sh`). That proves only the current per-slot/counting contract set. The crate is a real Cargo package: `cargo build` and `cargo test` both exit 0, and the manifest's `vstd` pin plus `[package.metadata.verus] verify = true` are what make that so (see the Cargo entry below). At the #30 closeout, cargo test discovered 0 runtime tests and no differential oracle parity was claimed; #32 has since added a bounded nextest oracle. The former `swisstable-verus-021` claim that `WasNeverFull` reads `growth_info()` was corrected: the pinned C++ updates growth accounting after choosing the erase byte.

### Automatic growth and sized reservation are removed from insertion (`swisstable-verus-009`)
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:155-165` describes insert finding a key and growing when overcrowded; `raw_hash_set.h:3677-3713` calls `PrepareInsertLarge`; `raw_hash_set.cc:2369-2393` selects the slow growth/deleted-slot path using `GrowthInfoAccessor`; `raw_hash_set.cc:2344-2366` sizes `ReserveTableToFitNewSize` from the requested size.
- **What the Rust port does instead:** `src/swiss_table.rs:218-223` requires `has_free_slot()` before `insert`; `:414-455` exposes separate `reserve(additional)` but ignores `additional` and increments `capacity_bits` by one. `src/raw_table.rs:790-800` expressly does not resize on insertion.
- **Why:** The port isolates `resize` as an explicit verified boundary and does not implement Abseil's growth policy/metadata. The operator's 2026-10-02 ruling, recorded in the source comments, accepts the insertion-path cut; the ledger's earlier `blocker` describes the pre-ruling request.
- **Impact:** A caller must explicitly reserve before insertion; full/overcrowded insertion and reserve-for-N behavior are not parity-compatible. Rehash is reachable through `reserve`, not through `insert`. A successful explicit resize is not proof of insertion-driven rehash.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-009`.
- **Generalizable lesson:** Porting `insert` without its load-factor transition makes capacity management a new caller obligation, even when a standalone resize exists. Test operation sequences, not merely individually available methods.

### Executable ghost state needs a tracked wrapper, not a spec-valued field (`swisstable-verus-011`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272` initializes and updates live slot state through constructors and operations; `:3691-3710` obtains a slot through policy-backed insertion.
- **What the Rust port does instead:** The production port keeps executable `ControlBytes` and `Vec<u64>` hashes and derives `stored_hashes()` from slots. The separate #120 analysis clone verifies a different representation: `RawTable` owns `Tracked<LiveIndex>`, whose tracked struct owns `Map<u64, usize>` mapping each live hash to its current physical slot.
- **Why:** A direct executable `ghost Set` field initialized with `Set::empty()` or `Ghost::new(Set::empty())` still fails mode checking on Verus 0.2026.05.24. A tracked wrapper around a tracked `Map` works, but `Map::tracked_empty/insert/remove` and the broadcast map/set axiom groups enlarge the trusted computing base; see `analysis/tracked-map-probe/tcb.md`.
- **Impact:** The probe verifies map/slot maintenance through insert, both erase outcomes, clear, resize, and value remapping, without a `Set` extensionality proof. It establishes viability for this bounded slice only; the tracked representation is not in production and no contract was changed.
- **Status:** worked-around for the bounded #120 probe; production remains on the derived model per the operator's 2026-10-08 decision to keep the existing ruling.
- **Finding ids:** `swisstable-verus-011`, `swisstable-verus-017`, `swisstable-verus-023`, `swisstable-verus-032`.
- **Generalizable lesson:** A failed spec-valued field initializer does not rule out all ghost state. Test a linear tracked wrapper with a map, then price its library axioms into the TCB before adopting it.

### Derived-set extensionality remains a scope cut; a tracked index is viable (`swisstable-verus-023`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:155-165` preserves entries across insertion; `raw_hash_set.cc:2104-2144` transfers slots during resize. Set equality over the port's derived `Set::new` is a port specification of those operations.
- **What the Rust port does instead:** Production contracts remain per-slot/frame and counting, with bidirectional per-slot survival for resize. The #120 scratch clone maintains `Map<u64, usize>` incrementally and proves the two-way map-domain/slot relation without `ext_equal` over `stored_hashes()`.
- **Why:** Four measured `Set::new` extensionality variants failed to close or regressed. The distinct tracked-map representation verifies through erase and bounded resize, but its vstd axiom functions add TCB trust and the experiment does not establish the original `Set` equality contracts.
- **Impact:** The 2026-10-02 ruling still governs production: no set-level contract change was made. Findings distinguish the failed derived-Set proof from the viable, higher-trust tracked-map slice. Evidence is in `analysis/tracked-map-probe/`.
- **Status:** ruled-scope-cut for production contracts; tracked representation viability demonstrated in a separate probe; operator kept the 2026-10-02 ruling on 2026-10-08.
- **Finding ids:** `swisstable-verus-011`, `swisstable-verus-017`, `swisstable-verus-023`, `swisstable-verus-013` (older pre-ruling count), `swisstable-verus-032`.
- **Generalizable lesson:** A tracked index can make updates easy to state while leaving the former abstract-set contract unproved. Keep representation viability, TCB cost, and permission to strengthen contracts as separate decisions.

### Erase's `WasNeverFull` decision matches upstream after a counter fix (`swisstable-verus-021`, `-030`)
- **Category:** Semantic divergence.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:708-723` counts the leading non-empty bytes in the after/before `MaskEmpty` windows; `:868-883` chooses `kEmpty` when their sum is below 16 and `kDeleted` otherwise.
- **What the Rust port does instead:** `ControlBytes::was_never_full` now freezes each counter at the first empty byte, matching the `TrailingZeros`/`LeadingZeros` prefix run. `RawTable::erase` chooses the corresponding control byte.
- **Why:** The previous executable loops assigned `fwd = n` / `bwd = m` for every empty byte; the recursive specifications also replaced the count at every empty. Both therefore measured the last empty in a window rather than the first non-empty run. Because implementation and spec shared the same error, the prior 149/0 proof did not expose it. The correction tracks whether the run has already ended, updates the recursion/step lemmas, and tests an isolated full slot and a 16-slot run around the erased index.
- **Impact:** The concrete `kEmpty` and `kDeleted` cases now verify, and erase's branch-specific postconditions include the tracked live-map/slot invariant in the scratch integration. A fresh production crate run after the fix reports 149 verified, 0 errors. Growth-left and deletion-budget accounting remain a separate scope cut.
- **Status:** fixed and verified.
- **Finding ids:** `swisstable-verus-021`, `swisstable-verus-030`.
- **Generalizable lesson:** A verified implementation and specification can still agree on the same transcription error. Use concrete boundary states that exercise actual counter order, not only a lemma restating the chosen formula.

### Exact slot-index change is not established by the bounded value-remap proof (`swisstable-verus-033`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:2104-2144` allocates a larger table and transfers each live key/value slot to its new probe-selected position.
- **What the Rust port does instead:** The bounded `SwissTable::reserve` proof keeps each live key associated with its value and the tracked map points to the final slot. The probe verifies `values[tracked_map[32]] == 320` after reserve.
- **Why:** An extra assertion that this key's post-resize physical slot differs numerically from its old slot was not discharged by the pinned Verus run (153 verified, 1 error, including a resource-limit error). The gate's bidirectional key/value preservation and final map lookup do verify; they do not assert an exact destination index.
- **Impact:** The probe establishes value continuity through resize and map remapping, but does not claim a particular key changed numeric slot. The failed assertion and transcript are retained in `analysis/tracked-map-probe/`.
- **Status:** worked-around for the bounded value-preservation gate; exact index delta remains open.
- **Finding ids:** `swisstable-verus-033`.
- **Generalizable lesson:** A value-preservation contract can be proved without identifying the exact destination index. State whether an experiment proves association preservation or an actual index change; they are different guarantees.

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
- **Why:** The current P2 boundary is scalar-only. Issue #36 records SIMD as a scope cut for this implementation; no SIMD code exists to assign to Verus or a Kani sub-cluster. This is not a claim about general intrinsic reach.
- **Impact:** No SIMD instruction/performance parity, and the portable/NEON 8-lane scheduling is not represented. For a fixed valid 16-byte window, masks are intended to encode the same byte predicates as the SSE2 path; this is **not** a measured runtime equivalence claim for every architecture, sentinel, or look-up trace.
- **Status:** ruled-scope-cut.
- **Finding ids:** `swisstable-verus-002`, `swisstable-verus-003`.
- **Generalizable lesson:** Proving a scalar mask abstraction does not port vector loads, platform dispatch or throughput. Record lane width, mask layout and architecture conditions before claiming a SIMD substitute is equivalent.

### Raw uninitialized slots and sanitizer lifetimes become initialized vectors (`swisstable-verus-001`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:2231-2272` parameterizes `slot_type` and allocator via policy; `:3478-3497` separates metadata-only erase from destruction; `raw_hash_set.cc:505-516` poisons/unpoisons slot memory on control-byte transitions, and `:2104-2135` transfers and deallocates an allocated backing array. `raw_hash_set.h:2390-2409` dereferences and advances raw slot/control pointers.
- **What the Rust port does instead:** `src/raw_table.rs:11-18,189-198` has `ControlBytes` with `Vec<u8>` bytes, parallel initialized `Vec<u64>` hashes and no raw-pointer/`MaybeUninit` slot layer; `src/swiss_table.rs` separately stores `Vec<u64>` values. Erase zeroes the logical slot; resize builds a fresh table rather than transferring C++ object lifetimes in raw storage.
- **Why:** Safe, initialized Vec indexing yields Verus-friendly ownership and bounds obligations; a faithful unsafe representation would require separate memory-initialization, aliasing, destruction and sanitizer/lifetime arguments, not supplied here. The source's shorthand “`Vec<u64>` control bytes” is inaccurate: the actual control vector holds `u8`.
- **Impact:** Object lifetime, destructor effects, allocator behavior, poison/unpoison diagnostics, layout, peak allocation and pointer identity are not ported or proved. It is only a logical-slot model; zero is reserved as `NO_HASH` in this representation. Issue #35 confirmed there is no unsafe implementation to route to Kani; this physical transfer gap remains open.
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
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-008` (specialized value representation); The iterator limitation is linked to the existing storage and specialized-value scope findings; no pointer-iterator parity is claimed.
- **Generalizable lesson:** An index cursor can preserve visitation order/termination without being equivalent to a pointer iterator. Audit validity, generation and reference-lifetime guarantees separately from enumeration correctness.

### The rehash transfer algorithm and object relocation are simplified
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:593-653` documents and begins the in-place `DropDeletesWithoutResizeAndPrepareInsert` swap/tombstone chain; `:1610-1629` encodes probed elements when growing; `:2104-2144` also has a fresh-backing-array `ResizeAllocatedTableWithSeedChange` path that transfers slots, reseeds and resets growth accounting.
- **What the Rust port does instead:** `src/raw_table.rs::resize` runs `clear_dead` (the reference's own step 1, unchanged) and then walks the tombstoned slots once, re-inserting each key through the ordinary verified `insert`. It does not implement same-capacity in-place swap chains, policy-driven relocation, allocator effects, reseeding or growth-info recalculation.
- **Why:** Initialized `Vec`-backed storage replaces C++ raw move/swap and pointer arithmetic (see the raw-slot entry), and the reference's own alternative resize path (`FindNewPositionsAndTransferSlots`) is also a transfer into a fresh table, so the observable result — the keys live again, at positions the probe sequence chooses — is the same. The port additionally needs a *record* of where each key went, because the control bytes and the payload are two separate `Vec`s where C++ has one allocation and a pointer move; see `swisstable-verus-031` for why that record is a ghost `Seq` pair.
- **Impact:** Preservation is specified per slot in both directions and the resize slice verifies (149 verified / 0 errors). Internal placement, memory use, object move/destruction effects and resize-performance parity still differ, and no C++/Rust behavioral comparison has been run.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-001`, `swisstable-verus-013`, `swisstable-verus-019`, `swisstable-verus-031`.
- **Generalizable lesson:** "Rehash preserves elements" is only one property of a transfer path. Distinguish fresh allocation from in-place tombstone reclamation, and note that splitting one allocation into two can create a *bookkeeping* obligation the original never had.

### Machine-word capacity and bitwise proof obligations need additional bounds and lemmas
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1773-1789` uses unchecked `size_t` masked arithmetic and an uncapped `index_ += Width`; `hashtable_control_bytes.h:291-343` computes masks with bitwise/vector operators.
- **What the Rust port does instead:** `src/probe_seq.rs` caps capacity bits, states explicit overflow guards and retains `& capacity_mask`; `src/group_probe.rs:163-207` builds a `u16` mask using `|`/`<<`. `verif/lemmas.rs` supplies bit-vector bridge lemmas. `src/control_bytes.rs` carries a conservative `0x7FFF_FFFF` capacity bound.
- **Why:** Verus integer-mode proofs need explicit `#[verifier::bit_vector]` facts for bounds; the pinned build's probes cannot establish `usize::MAX` or the *unbounded* `u64 -> usize` narrowing, though a bounded round-trip lemma recovers the exact casts the port actually needs. Initial reports that Verus had **no** bitwise model, or that `usize` had been proved 32-bit, were both retracted — the first by a non-tautological probe, the second by a probe whose postcondition was its own body.
- **Impact:** Smaller admitted capacity range and proof boilerplate; the original masked operators and `u16` masks are retained, not replaced with modulo or boolean vectors. One site still needs a bound Verus will not give it: `GroupProbe::load`'s loop invariant, where proving `base + i` cannot wrap before it is a `Vec` index requires the type maximum. That site is implemented with the literal bound and its proof status is read from the current transcript, not from an older probe.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-012`, `swisstable-verus-014`, `swisstable-verus-015`, `swisstable-verus-016`, `swisstable-verus-018`, `swisstable-verus-025`, `swisstable-verus-028`, `swisstable-spec-003`.
- **Generalizable lesson:** Distinguish "an operator is unsupported" from "this solver mode needs a lemma", and test a non-tautological probe in the target binary before weakening a port. A probe whose postcondition is its own body verifies for any width and proves nothing — the same defect as a vacuous lemma.

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

### Differential parity is limited to the mapped observable operation subset
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** The 11 SwissTable-relevant source files listed in README.md declare 409 GoogleTest test forms across flat_hash_map, flat_hash_set, raw_hash_set, control-byte, resize, node-storage, allocator, hashtable-sampling, and inlined-vector tests. The complete source-declaration inventory is oracle/test-map.csv; the pin is Abseil 20260817.0, commit 2065f4ded0558c6f89fee67c8e5228feb4eb960e.
- **What the Rust port does instead:** oracle/driver.cpp and the generated nextest cases compare a specialized u64-to-u64 map's insert/replace, contains, erase, reserve, clear, and selected erase-if results. They normalize contents by key and inject IdentityHash-v1 on the C++ side while the Rust table receives that same raw key. Fourteen cases compare behavior (two translated upstream tests, four comparable boundaries, and eight seeded random sequences); two cases check explicit exclusion placeholders for key zero and C.10 iteration/pointer observability.
- **Why:** The approved Verus port has no generic value/key/equality or allocator API, node storage, raw-pointer slot lifetime, sanitizer behavior, iterator order contract, architecture-specific SIMD path, or full Abseil growth policy. Other source tests may exercise outcomes expressible as contents, but their constructor, iteration, allocator, storage, or internal behavior is not translated as the same operation in this case schema. The two directly translated upstream tests are FlatHashMap.EraseIf and the content portion of FlatHashMap.Reserve; the latter's reference-stability assertion is outside the comparison. The test map records 407 of 409 source declarations as unmapped; typed-test declarations are listed once and their runtime type instantiations are not separately enumerated.
- **Impact:** The observed 16/16 nextest pass establishes parity only for those mapped operations and cases. It does not imply that the 242-test CTest baseline, all 409 source declarations, test-template instantiations, performance, allocation, pointer stability, traversal order, SIMD, or internal probe behavior match.
- **Status:** open.
- **Finding ids:** swisstable-verus-001, swisstable-verus-002, swisstable-verus-004, swisstable-verus-008, swisstable-verus-009, swisstable-verus-021, swisstable-verus-035.
- **Generalizable lesson:** A differential runner can establish a narrow contract without claiming suite-wide parity. Keep the test inventory complete, mark unsupported cases unmapped, compare normalized observable results, and report mapped coverage alongside the pass count.

### Iteration order and pointer stability stay outside the oracle contract
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:597-599` documents a per-table seed mixed into H1 to randomize iteration order; `absl/container/flat_hash_map.h:69-70,108-114,482-483` documents pointer/reference invalidation on rehash and move for flat storage. The pin is Abseil 20260817.0, commit 2065f4ded0558c6f89fee67c8e5228feb4eb960e.
- **What the Rust port does instead:** The oracle sorts the logical key/value contents before comparison. The new reversed-insertion boundary confirms that insertion and reserve results are compared in key order; the C.10 case is explicitly excluded with a null placeholder. The port does not promise an equivalent C++ pointer/reference identity or stability contract.
- **Why:** Abseil deliberately varies iteration order by per-table seed and relocates flat elements during rehash. The Rust port has a Vec-backed scalar model and no matching C++ borrowed-reference contract. A shared `IdentityHash-v1` input does not make native hash mixing, seeds, slots, or iteration order equal.
- **Impact:** The 16 passing nextest cases compare logical contents and operation results. They establish neither iterator-order parity nor pointer/reference stability parity, and the explicit exclusion prevents those properties from being mistaken for verified behavior.
- **Status:** ruled-scope-cut.
- **Finding ids:** swisstable-verus-036.
- **Generalizable lesson:** Normalize map contents when iteration order is not contractual, and represent reference-stability exclusions explicitly. Supplying the same hash input is not evidence that two hash-table implementations share their layout or invalidation behavior.

### A deterministic package scaffold does not configure Cargo-Verus (`swisstable-verus-010`)
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** There is no corresponding C++ `Cargo.toml`; this is a Rust/verifier build-workflow gap, not a source-language semantic mismatch.
- **What the Rust port does instead:** `rust/swisstable-verus-core/Cargo.toml` carries three lines beyond the generic scaffold: `[dependencies] vstd = "=0.0.0-2026-05-24-0157"`, `[package.metadata.verus] verify = true`, and the `verus!`-generated crate root that proof-only imports `#[cfg(verus_only)]`-guard. `analysis/verus/run-verus.sh` drives `verus` directly on `src/lib.rs`; `analysis/verus/run-cargo.sh` captures `cargo build`, `cargo test` and `cargo verus verify`.
- **Why:** The generic `scaffold-crate` template intentionally emits no dependencies and no tool-specific package settings, so the scaffolded manifest is a valid Cargo package but not a *verifier* package. Two separate symptoms, one cause: without `verify = true`, `cargo verus verify` prints `WARNING: You asked for verification, but cargo did not find any crates that opted into verification` and degrades to `cargo check`; without a `vstd` dependency, neither `cargo check` nor the driver can resolve `vstd` or the `verus!` macro. The `vstd` pseudo-version is driver-matched, so a Verus release bump must change it in the same commit.
- **Impact:** None outstanding for this issue. All three Cargo entry points exit 0 and `cargo verus verify` reports 149 verified / 0 errors, matching the direct run. The earlier zero-test condition is resolved by #32's generated integration suite and #37's two additional oracle cases: `cargo nextest` now runs 16 oracle tests. A *second* `cargo verus verify` is still a cached no-op that prints no `verification results` line at all, so a transcript captured that way would record a green run that verified nothing — `run-cargo.sh` touches `src/lib.rs` first to force the verification to re-run.
- **Status:** fixed (the operator's 2026-10-03 authorization covered exactly this one protected-root file).
- **Finding ids:** `swisstable-verus-010`.
- **Generalizable lesson:** A deterministic package scaffold is not necessarily a verifier-ready project, and "no output" from a cached verify is not success. Test the manifest *and* the source's verifier-only imports against the pinned toolchain template, and make the runner force a real verification rather than reporting the cache.

### A plausible rehash invariant was false inside the control-byte rewrite window (`swisstable-verus-019`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1530-1538` declares deleted→empty and full→deleted; `raw_hash_set.cc:434-443,604-645` rewrites metadata *before* moving the still-live slot payloads in `DropDeletesWithoutResizeAndPrepareInsert`.
- **What the Rust port does instead:** `src/raw_table.rs:360-405` defines `reclaiming_model(before,before_hashes)` for the transient state, rather than asserting the normal `model()` through `clear_dead`; `:985-1015` uses a fresh-table transfer. The current source additionally corrects an `is_full`↔pre-reclaim-full claim to `is_dead`↔pre-reclaim-full (`:370-400`).
- **Why:** Once a full control byte becomes `kDeleted`, its stored hash has not yet moved or been zeroed: `!is_full(i) ==> slot_hash(i)==NO_HASH` is *false*, not merely too hard for SMT. The later `is_full` predicate on the reclaimed array was likewise the wrong state classifier.
- **Impact:** An impossible loop invariant blocked resize proof and made attempted lemmas misleading; the revised predicate states the transition window honestly. The final per-slot preservation obligations now verify in the 150/0 crate run.
- **Status:** fixed for the scoped resize proof (false invariant corrected and witness bridges discharged).
- **Finding ids:** `swisstable-verus-019`; the corrected transient invariant is recorded under `swisstable-verus-019`.
- **Generalizable lesson:** Model intermediate representation states explicitly when a port separates metadata updates from payload moves. Before adding solver hints to an invariant, check whether it is true immediately after each write.

### A third plausible rehash invariant was false in the same window (`swisstable-verus-031`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:434-447` `ConvertDeletedToEmptyAndFullToDeleted` is `absl::bit_internal::Subtract`: one saturating subtract over the control bytes that maps every byte with the MSB set to `kEmpty` and every other byte to `kDeleted`. **After that call no slot in the table is full** — that is the point of it.
- **What the Rust port does instead:** `src/raw_table.rs` `reclaiming_model` states the window as `is_dead_spec(i) <==> before[i] <= 0x7F`. It previously read `is_full_spec(i) <==> before[i] <= 0x7F`, justified in a comment by "`clear_dead` never promotes a free byte" — which is true and irrelevant: the clause is about what happens to the *full* bytes, and they all become dead.
- **Why:** This is the third instance of the same failure mode, after `swisstable-verus-019` (a false `model()` invariant over the same window) and `swisstable-verus-020` (a false `erase` comment). In each case the stated predicate was a plausible reading of the reference, was false, and had to be corrected against the source rather than proved. The symptom in the transcript is `invariant not satisfied before loop`, which is indistinguishable from a solver gap until you check the predicate against the reference by hand.
- **Impact:** No residual impact: the corrected predicate and the resize contract verify (149 verified / 0 errors). The cost was the wrong *diagnosis* of a failing invariant as a tool limit, which is what pushed the rehash proof into a solver-budget fight instead of a source check.
- **Status:** fixed.
- **Finding ids:** `swisstable-verus-031`, `swisstable-verus-019`, `swisstable-verus-020`.
- **Generalizable lesson:** When an invariant "should not verify", check whether it is *true* before escalating to a tool limitation. A loop invariant phrased as `is_full ⟺ was_live` in a window where the reference just made everything not-full is a source-reading error, and no amount of solver budget fixes it.

### The rehash transfer needs an existential witness, and `exists`-inside-`forall` exceeds the solver budget (`swisstable-verus-031`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:2104-2144` `ResizeAllocatedTableWithSeedChange` moves each surviving slot into the new backing array and remembers nothing about where it went; the swap chain at `:593-653` needs no bookkeeping either, because the control byte and the payload are co-located and a single pointer move relocates both.
- **What the Rust port does instead:** `src/raw_table.rs::resize` records the placement in two ghost `Seq`s — `dest` indexed by the **source** slot, `owner` indexed by the **destination** slot — so each of the two survival directions is a pointwise fact about a single index (`dest[i] >= 0 ⟹ t.is_full(dest[i]) ∧ t.slot_hash(dest[i]) == before_hashes[i]`, and symmetrically for `owner`). The transfer itself reuses the already-verified `insert`, so find-or-open is not re-proved. The earlier revision stated both directions as `exists`-inside-`forall` loop invariants — five of that shape, plus a distinctness clause and an H2-tag clause.
- **Why:** Verus reported `note: while loop: Resource limit (rlimit) exceeded` on that loop and left 15 primary error locations unclosed. The distinguishing factor is not the number of invariants but the shape: a `forall` whose body contains an `exists` over a mutable array forces the solver to reason about a two-level quantifier over an unbounded index range, while a pointwise `forall` over one index with a recorded witness is a first-order fact. A ghost `Seq` is enough to carry the witness; no new abstraction is needed.
- **Impact:** The port verifies at 150/0, but any future contract that genuinely needs an existential per-slot statement will hit the same wall. This is the practical successor to `swisstable-verus-023` for the *pointwise* contracts: set-level extensionality was ruled out of scope, and the replacement that worked was a ghost index, not a better encoding of the same quantifier.
- **Status:** fixed.
- **Finding ids:** `swisstable-verus-031`, `swisstable-verus-023`.
- **Generalizable lesson:** When a quantified loop invariant will not close, check the quantifier *shape* before the budget. `forall i. P(i) => exists a. Q(i, a)` and `forall i. P(i) => Q(i, w[i])` are the same statement when the witness is unique, and only the second is a first-order obligation — a ghost sequence holding `w` converts one into the other without weakening the contract.

### `usize::MAX` is nameable only as a disjunction, so every bound becomes a literal (`swisstable-verus-025`)
- **Category:** No faithful Rust or verifier equivalent.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1755-1771` sizes the control array from `NumSlots` and `kWidth` in `size_t` without ever writing a maximum; the C++ side never needs a numeric type maximum because `size_t` overflow is a non-issue in the sized constructors it uses.
- **What the Rust port does instead:** Every capacity bound in the port is the literal `0x7FFF_FFFF`, carried as an invariant of `ControlBytes::well_formed` so it is available wherever the capacity is used. `verif/lemmas.rs::lemma_usize_max_is_one_of_two` records what Verus *can* say: `usize::MAX as u64` satisfies `r == 0xFFFF_FFFF || r == 0xFFFF_FFFF_FFFF_FFFF`.
- **Why:** Verus 0.2026.05.24 will not name the type maximum. A `requires` clause written `x + 1 <= usize::MAX` is unsatisfiable, which is how an earlier revision ended up with undischarged preconditions in `ControlBytes::new` and `SwissTable::reserve`. The literal is not a guess: `capacity_bits <= 31` already implies `2^31 - 1 == 0x7FFF_FFFF`, so the bound is a consequence of the port's own capacity shape rather than a new restriction.
- **Impact:** A reader cannot use `usize::MAX` as a mental stand-in for the port's bounds, and a Verus release that changes the modelling would require re-checking each literal. Nothing in the verified contract is weakened.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-025`, `swisstable-verus-018`, `swisstable-verus-016`.
- **Generalizable lesson:** In a verifier with an opaque or unnameable type maximum, every "obviously true" bound silently becomes a real precondition. Derive each literal bound from another stated invariant so the figure is a consequence of the design, not a magic constant.

### Index vocabulary has to be chosen once: `int` and `usize` do not bridge (`swisstable-verus-028`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:1755-1768` and `raw_hash_set.cc:175-220` index with one `size_t` vocabulary throughout, so a range fact stated about a loop cursor is the same fact as a range fact stated about a predicate argument.
- **What the Rust port does instead:** `claim_first_free`'s two linear scans state their loop invariants over `int` and cast the cursor once, on the bound, never on the predicate. `control_bytes::is_empty_or_deleted_in` is an `int`-indexed spec function precisely so the counting lemmas and the scan can share it.
- **Why:** Verus leaves `i as usize` opaque in **both** directions. A `usize`-quantified invariant is therefore not a usable premise for an `int`-quantified one, and a lemma whose conclusion is in the `int` form cannot produce the `usize` form at all. An earlier revision carried both vocabularies and needed a duplicated pair of lemmas per use site whose only job was to cross the cast.
- **Impact:** None now — the bridge is gone rather than paid — but the constraint is invisible until it has been paid once. It also means loop invariants over a `usize` cursor are unusable for anything the specification talks about, which constrains how a scan can be written at all.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-028`.
- **Generalizable lesson:** Pick one index vocabulary per proof and cast at the boundary, not inside the loop. A cast that appears twice is a cast that will eventually be needed on both sides of an implication.

### `assert forall ... by { }` does not assume its antecedent (`swisstable-verus-029`)
- **Category:** Unprovable or costly obligations.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.cc:189-198` `find_first_non_full_from_h1` returns a slot and its caller does not re-test, so its *completeness* — "if any slot is reusable, the scan finds one" — is part of the contract rather than an implementation detail.
- **What the Rust port does instead:** `verif/lemmas.rs::lemma_scan_contradiction` is a `proof fn` whose `requires` restates the two scans' premises and whose postcondition is `false`, and `claim_first_free` takes the completeness half of its contract from it.
- **Why:** Verus 0.2026.05.24 warns that `assert forall ... by { }` does not assume the antecedent of its outermost implication (linking its own upstream issue, "Don't always make assert forall assume the antecedent"). The contradiction "both scans found nothing, so nothing is free" therefore cannot be discharged in an assertion at the call site. An earlier revision of the lemma omitted the existential from its `requires`, which made the lemma and its `!exists` postcondition vacuous — the `if` body was unreachable from the premises alone — and `claim_first_free` could then not claim it always succeeds. A vacuous proof is worse than a missing one, because it looks like progress.
- **Impact:** None now, but the class of failure generalises: any port obligation of the form "if the loop ended, the negation of the loop guard is unreachable" needs a lemma with the premises in `requires`, not an in-place assertion.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-029`, `swisstable-verus-015`.
- **Generalizable lesson:** When a quantified assertion will not close, check whether its body is even *reachable* from the hypotheses before adding solver help — an unreachable body verifies for the wrong reason. Put loop-derived premises in a lemma's `requires`, where they are hypotheses by construction.

### Near-end groups use empty padding where Abseil mirrors live controls (`swisstable-verus-034`)
- **Category:** Cut or simplified behaviour.
- **C++ construct / upstream location:** `absl/container/internal/raw_hash_set.h:70-77,1149-1153` lays out a sentinel and `Group::kWidth - 1` cloned bytes; `raw_hash_set.cc:523-529,1461-1467` initializes and maintains those mirrors.
- **What the Rust port does instead:** `src/control_bytes.rs:358-401` allocates 16 all-`EMPTY` bytes after the sentinel, one byte more than the width-16 reference layout. `src/group_probe.rs:121-143,150-235` copies the window into a Vec and computes masks with scalar loops. In `src/raw_table.rs:757-780`, a free bit in that tail ends the bounded group walk and the full-slot fallback preserves lookup completeness.
- **Why:** The current safe Vec model has a static all-empty padding invariant and mutator frame clauses that leave every non-target byte unchanged. It has no mirror relation for writes to preserve. The full-slot fallback supplies completeness without changing #30's frame/counting obligations.
- **Impact:** A near-end window can report a padding byte as free when Abseil's matching mirror is full, so exact group-mask and probe-cost parity are not established. For example, with capacity 31 and base 17, lane 15 corresponds to slot 0 upstream but reads as `EMPTY` in the port. The fallback keeps the logical lookup complete at the cost of abandoning the fast-path result for that probe.
- **Status:** worked-around.
- **Finding ids:** `swisstable-verus-034`, `swisstable-verus-004`.
- **Generalizable lesson:** A tail buffer that makes memory accesses safe is not equivalent to a mirrored ring buffer. If the source duplicates mutable metadata at the end of an array, model and prove the synchronization rule as part of every update and frame contract.

### Stage 8A callsite assurance remains blocked on review (`swisstable-ligature-015`)
- **Category:** Tooling blind spots in the transfer.
- **C++ construct / upstream location:** Cross-concept calls among the SwissTable layers, including construction, insertion, and iteration paths in `absl/container/internal/raw_hash_set.h` and `raw_hash_set.cc`.
- **What the Rust port does instead:** Ligature's C_static report over the real crate is explicitly a `discovered-lower-bound`: 277 callsites discovered, 46 resolved, and 231 unresolved. `validate-callsites` passes the report's G1a/G1b structure and recomputed coverage, but `gate-r1-g16` finds five definite cross-concept calls absent from the promoted interaction set and 462 medium risk decisions awaiting an operator.
- **Why:** The interaction specs are still staged `.draft` files. Stage 8A cannot treat unreviewed interaction text as a declared edge, and the G16 risk tier is intentionally not self-adjudicated by the tool.
- **Impact:** R1/G16 does not close, and the five missing edges remain uncovered. `check-bridges` sees zero promoted bridges; `validate-witness` sees no promoted witness; rendering has no valid canonical result. None of those zero-input outcomes establishes bridge or witness assurance.
- **Status:** open; blocked on spec review and operator risk decisions.
- **Finding ids:** `swisstable-ligature-015`; see `analysis/ligature/stage8a/issue31.md` for exact outputs and callsite IDs.
- **Generalizable lesson:** Passing a schema/coverage validator over a lower-bound callsite report does not establish graph completeness. Require reviewed edge declarations and explicit risk dispositions before counting R1/G16 as closed.

