# P2 verifier fit: Creusot, Verus and Kani (P4-3, chainlink #157)

How P2's concepts map to each verifier. This covers:
- the incomplete Verus closure;
- Creusot's reach on the map model;
- Kani for unsafe slots and SIMD probing (#35, #36).

It feeds cells A4 (P4-8, #162), A5 (P4-11, #165) and A6 (P4-12, #166) of
`VERIFIER-MATRIX.md` at the workspace root.

The pilot itself was not changed. The claims rest on small probes run in
temporary directories. `probes/replay.sh` reruns all of them (about 3½
minutes) and checks 14 expected results; `probes/logs/` holds the committed
run.

## First, a correction to the matrix

The matrix described P2 as "generics, ghost maps, unsafe, SIMD". That
describes Abseil, not this port:

| Feature | Abseil | This port | Recorded as |
|---|---|---|---|
| Generics | Policy-parameterized keys, values, hash and equality | `u64` keys and values with identity hashing | Scope cut `swisstable-verus-008` |
| Slots | Raw, uninitialized slot storage | Initialized parallel `Vec<u8>` / `Vec<u64>` arrays | Scope cut `-001`; no `unsafe` code (#35) |
| Group probing | 16-lane SSE2 (8-lane on AArch64 and portable) | Scalar 16-byte loops | Scope cut `-002` (#36) |
| Map model | n/a | Spec-level `Map`/`Seq`/`Set` views | Real; 27 uses across 4 files |

So the port has no generic code. For matrix question Q1 (does a pure Verus
closure get CG3 VERIFIED?), P2 is as clean a test as P1, not the "heaviest
generics" test the matrix assumed. The upstream features only matter if a
cell adds a new implementation of them. Section 4 shows Kani can verify two
of them.

## 1. Verus (A4, P4-8): the proof is mostly done; the pipeline is not

**The proof.** `cargo verus verify` reports 149 verified, 0 errors. Of the 36
draft constraints, 35 are tagged on proved code (`// <Concept>.C0xx` next to
an `ensures` clause). The exception is `GroupProbe.C004`, which the draft
states wrongly (`swisstable-spec-002`).

**What blocks a closure under Ligature 1.4.2 is pipeline state, not proof:**

- **Nothing is approved yet.** All Stage 3 artifacts are `.draft`: 7 concept
  specs (36 constraints), 14 boundaries, 15 interactions and 6 bridges. So
  there is no promotion receipt, no work package and no closure profile.
- **No proof-note markers.** Verus intake (`record-assurance --verus-json`
  with `--verus-function OBLIGATION=FUNCTION`) needs
  `#![verifier::proof_note("ligature:<obligation>")]` inside each bound
  function's `ensures`. The source has none.
- **R1/G16 is not closed.** It is blocked on 462 medium-risk operator
  decisions plus five missing edges (`swisstable-ligature-015`). Under 1.4.2
  the C-static report also has no source binding, which shows as 3 high
  findings until `extract-c-static` is re-run.
- **Stage 7 now has its Git root** (P2 became its own repo on 2026-10-20).

**Proof gaps that remain scope cuts:**
- probe coverage, which is bounded instead of proved (`-004`);
- no growth on insert (`-009`);
- derived-set equality (`-017`, `-023`);
- the exact slot-index change on resize (`-033`).

**Probe: the derived-set lemma, minimal form** (`probes/verus/`). P2's
`stored_hashes` is a `Set::new` comprehension with an `exists` inside.
Isolated from `RawTable` and asked with `=~=`:
- the erase lemma proves unaided;
- the insert lemma fails unaided, and proves with about 15 lines of explicit
  witnesses (`set_ext_manual.rs`);
- a deliberately false erase lemma is refuted, as it should be.

P2's earlier attempts worked inside the `RawTable` proofs, where the
quantifiers spread (PORT-GAPS, `-031`). Factoring the equality into a
standalone `Seq`-level lemma like this one is a cheap thing for P4-8 to try
before keeping `-023` as a scope cut (`swisstable-verus-038`).

**Expected outcome:** D over a scope trimmed to what is proved. If the
scope-cut properties stay in the declared obligations, the honest
declaration is `partial`.

## 2. Creusot (A5, P4-11): strong on the map model, weaker on bit arithmetic

A Creusot cell is a rewrite of contracts and proofs. The executable code is
plain Rust and carries over, but every `requires`/`ensures`, `spec fn`,
`proof fn` and loop invariant inside `verus!` has to be rewritten in Pearlite:
- `#[requires]` and `#[ensures]` for contracts;
- `#[logic]` functions for specs and lemmas;
- `#[invariant]` and `#[variant]` for loops;
- `Vec` models through `Seq` and `@`.

There is a lot of it: P2 has 66 `requires` and 71 `ensures` clauses, 63
loop invariants, 44 spec functions and 7 proof functions. Concept specs and interactions are
restated with `verifier: creusot` and `creusot-deductive-check`, as in P1.

**The map model is where Creusot is strong** (`probes/creusot/set_ext*.rs`).
The same two derived-set lemmas, with `Set::from_predicate` over `Seq`
models, both prove unaided at P1's default prover budget. The false erase
lemma is refuted. Creusot's `Set` is Why3's built-in set, which carries an
extensionality axiom, so this is exactly the step that has kept `-023` a
scope cut in Verus.

**Bit arithmetic is where Creusot is weaker** (`probes/creusot/bits*.rs`,
`swisstable-creusot-001`). The facts tested are P2's H2 mask, H1 shift,
probe-offset mask and lowest set bit:

- **Default mode:** 3 of 4 fail, even at 10 times the time budget. Only
  `trailing_zeros` (lowest set bit) proves.
- **With `#[bitwise_proof]` and specs compared on `u64`:** the mask facts
  prove. `hash >> 7 == hash / 128` still fails: `u64` division is not
  available in logic, and the `@`-integer form does not close in either mode.
- **For comparison:** Verus proves all four with a one-line
  `by(bit_vector)` each (`probes/verus/bits.rs`).

P2 uses masks and shifts throughout `hash_mix`, `probe_seq`, `group_probe`
and the control bytes. Each such fact needs bitwise mode, or a lemma where
the fact mixes shifts and arithmetic.

**Expected outcome:** D, or P if the bitwise facts stall.

## 3. Kani on the port as it is (A6, P4-12)

- **The crate needs no changes.** Kani compiles P2's Verus crate unchanged:
  `vstd` builds, and `verus!` drops the ghost code. On a 31-slot table (the
  smallest allowed), one harness checks insert → contains → erase → not
  contains for any key and value, in about 48 s with unwind 50.
- **Not vacuous.** A version claiming the key survives erase is refuted.
- **Unsupported constructs.** Kani lists 4 (the allocation-error handler and
  panic-location paths). None is reachable in these harnesses.
- **Claims are bounded by capacity.** Every loop runs over the capacity, so
  the claim holds only for the capacities harnessed. Expected outcome:
  B/CG3, released under the per-instantiation record G14 requires of every
  Kani closure.
- **Kani can cover what Verus cut.** Probe coverage (`-004`) and the exact
  slot change (`-033`) are checkable at small capacities. That makes Kani a
  candidate source of evidence for the matrix's supporting-verifier rows
  (B1). Under #151, supporting evidence cannot replace the owner's.
- **Tooling gotcha.** `--harness` matches substrings, so
  `--harness insert_contains_erase` also runs `insert_contains_erase_mutant`.
  Use `--exact` with the full path (`swisstable-kani-002`).

## 4. Kani on the shapes P2 scoped out (#35, #36)

`probes/kani/upstream_shapes/` writes the two Abseil shapes the way upstream
does:

- **SIMD group probing: verifiable.** `GroupSse2Impl::Match` and
  `MaskEmptyOrDeleted` are written with `_mm_loadu_si128`, `_mm_set1_epi8`,
  `_mm_cmpeq_epi8`, `_mm_cmpgt_epi8` and `_mm_movemask_epi8`, per
  `hashtable_control_bytes.h:277-315`. Kani proves both equal to the scalar
  masks for every 16-byte group, in about 2 s each. A Kani-owned cluster
  could therefore own a real SSE2 `GroupProbe`. That changes the picture #36
  left open. The 8-lane AArch64 and portable variants would each need their
  own harness.
- **Raw slots: not fully verifiable today** (`swisstable-kani-001`). Slots
  are `MaybeUninit<u64>` with a control byte saying which are live.
  - Insert, get and erase check.
  - But an uninitialized `assume_init_read` passes under default checks.
  - With `-Z uninit-checks`, Kani 0.67 refuses outright: "Checking memory
    initialization of type `[MaybeUninit<u64>; 4]` is not supported".
  - So Kani cannot currently check the initialization discipline that raw
    slots exist for. The workaround is a hand-written shadow "is
    initialized" map, asserted before every read.

## What each cell needs

| Cell | Crate and layout | New spec work | Main risk |
|---|---|---|---|
| A4 Verus | Existing crate | Approve the Stage 3 drafts; add proof-note markers; promotion, Stage 7 and closure profile; resolve R1/G16; re-run `extract-c-static` | Pipeline volume, not proof. Decide the `-023` scope (try the standalone lemma) |
| A5 Creusot | New crate (nightly-2026-04-21, `creusot_std`) in its own single-verifier workspace | Rewrite every contract, invariant and lemma in Pearlite; concept specs with `verifier: creusot` | Bitwise facts (`swisstable-creusot-001`) |
| A6 Kani | Harnesses can overlay the existing crate, which compiles unchanged; its own workspace for a clean cell | One harness per obligation at fixed capacities; concept specs with `verifier: kani` | Capacity-bounded claims. Any raw-slot variant runs into `swisstable-kani-001` |

## Findings recorded

- `swisstable-verus-038` (verus, friction): the minimal derived-set insert
  lemma needs explicit witnesses; erase proves unaided.
- `swisstable-creusot-001` (creusot, friction): P2's shift and mask facts
  need `#[bitwise_proof]`, and the shift-as-division fact still does not
  close.
- `swisstable-kani-001` (kani, friction): uninitialized `MaybeUninit` reads
  are not detected, and `-Z uninit-checks` refuses `MaybeUninit` arrays.
- `swisstable-kani-002` (kani, friction): `--harness` matches substrings.

The first three are also in `PORT-GAPS.md`. The SSE2 result is positive
evidence and is not a limitation. The SIMD gap (`-002`) stays a scope cut
for the current port.
