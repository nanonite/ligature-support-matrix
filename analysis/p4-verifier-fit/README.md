# P3 verifier fit: Creusot and Verus (P4-4, chainlink #158)

How P3's concepts map to Creusot and Verus; Kani is done (#44, #134, #135,
#49). The starting point is the original plan's split:
- a `core-functional` cluster (quarter-round, block, Poly1305 limbs) with a
  deductive closure;
- a `bytes-layer` cluster (slices, endianness, in-place buffers) for Kani;
- plus the Verus deferral at #43.

It feeds cells A7 (P4-13, #167) and A8 (P4-14, #168) of `VERIFIER-MATRIX.md`,
and the P3-based composition rows B1-B5.

The pilot itself was not changed. The claims rest on small probes run in
temporary directories. `probes/replay.sh` reruns them (a few minutes) and
checks 16 expected results; `probes/logs/` holds the committed run.

## Summary

- **The plan's split is sound, but the core-functional cluster has no
  obligations yet.** All 6 obligations and 3 bridges P3 holds today are
  bytes-layer properties: lengths, counter capacity, and segment-invariant
  tags. A Creusot or Verus cell starts by writing new concept-spec
  obligations for the quarter-round, the block function and the Poly1305
  limb arithmetic.
- **The quarter-round transfers well.** Both verifiers prove P3's
  quarter-round equal to an RFC 8439 spec, with no lemmas, once rotation is
  written as shifts. A one-constant mutant is refuted in both.
- **Poly1305 limb bounds favour Creusot.** The `d0` limb products of
  `process_block` cannot overflow `u64`. Creusot proves this unaided. Verus
  needs one `by(nonlinear_arith)` line per product: these are genuine
  variable-by-variable products, unlike P1's constant multipliers.
  Loosening the bounds to 2^40 makes Creusot's proof fail, as it should.
- **Neither verifier specifies the byte-order and rotation primitives P3
  calls.** `rotate_left`, `from_le_bytes`, `to_le_bytes` and slice `fill`
  are missing in both. Verus also lacks `copy_from_slice` and slice
  `try_into`; Creusot lacks `extend_from_slice`. Each one needs a trusted
  specification (Verus `assume_specification`, Creusot `extern_spec!`) or a
  rewrite into shifts and indexed loops (`crypto-verus-001`,
  `crypto-creusot-001`).
- **No generic code here either.** So, as in P1 and P2, the CG3 condition
  only arises for the Kani owner.

## Probe results

| Probe | Verus | Creusot |
|---|---|---|
| `u32::wrapping_add` | Proved | Proved |
| `u32::rotate_left` | "not supported" | No contract ("impossible precondition") |
| Rotation as shifts vs a spec | Proved | Proved (`#[bitwise_proof]`) |
| Quarter-round vs RFC 8439 §2.1 | Proved, no hints | Proved (`#[bitwise_proof]`), no lemmas |
| Quarter-round mutant (rotate 15, not 16) | Refuted | Refuted |
| `u32::from_le_bytes` | "not supported" | No contract |
| Poly1305 `d0`: no `u64` overflow for h < 2^27, r < 2^26 | Fails unaided; proved with 5 `by(nonlinear_arith)` hints | Proved unaided |
| Poly1305 `d0` mutant (h < 2^40) | n/a | Refuted |
| P3's 16 std calls (`probes/*/stdcalls.rs`) | 6 unsupported | 5 without contracts |

Tools: Verus 0.2026.05.24.ecee80a and cargo-creusot 0.14.0-dev (Why3
1.8.2), both from the `crypto-mixed` shell.

## Standard-library coverage

| Call (uses in P3) | Verus | Creusot |
|---|---|---|
| `len`, `is_empty`, `wrapping_add`, `wrapping_sub`, `checked_add`, `min`, `split_at`, `Vec::with_capacity`, `Option::ok_or` | Specified | Specified |
| `rotate_left` (4) | Missing | Missing |
| `u32::from_le_bytes` (2 loaders) | Missing | Missing |
| `to_le_bytes` (4) | Missing | Missing |
| slice `fill` (1) | Missing | Missing |
| `copy_from_slice` (7) | Missing | Specified |
| slice `try_into` (1) | Missing (`TryFromSliceError`) | Specified |
| `extend_from_slice` (2) | Specified | Missing |

**Trusted specs or rewrites.** A trusted specification is easy to write,
but it is trusted code that the verifier does not check. Rewriting removes
that trust at the cost of touching production code:
- `rotate_left` becomes shifts (proved above);
- the byte loads and stores become shifts and masks;
- `copy_from_slice` and `fill` become indexed loops.

The rewrite has to keep oracle parity: P3's 2580 nextest cases.

## Per-layer fit

| Layer | Creusot | Verus | Notes |
|---|---|---|---|
| Quarter-round | Strong (bitvector mode) | Strong | Both proved against RFC 8439 in the probes |
| Block function (10 double rounds on `[u32; 16]`) | Expected: loop invariant `state == rounds_spec(initial, i)` | Same | Not probed. Should be structural once the quarter-round proves; in-place `[u32; 16]` index updates were not tested in either verifier |
| Poly1305 limb bounds and carries | Strong (unaided) | Needs `by(nonlinear_arith)` per product | `d0` probed; `d1`-`d4` and the carry chain have the same shape |
| Poly1305 functional correctness (`h = (h + m)·r mod 2^130 − 5` over 26-bit limbs) | Hard | Hard | Not probed. This is the deep part: a full proof needs a limb-to-integer interpretation and modular-reduction lemmas. If it is not attempted, Poly1305 is `partial`, with Kani and the oracle covering the rest |
| Existing bytes-layer obligations (6) and bridges (3) | Feasible after the std gaps | Feasible after the std gaps | Lengths and counter arithmetic are linear. Poly1305.C005 (segment-invariant tag) needs a buffer invariant over the 16-byte partial block |

## What each cell needs

**A7 (Creusot) and A8 (Verus).** Both cells need:
- **a separate crate**: Creusot needs nightly-2026-04-21 with `creusot_std`;
  Verus needs 1.95.0 with `vstd` and `verus!`. P3's crate depends on neither,
  and its Kani harnesses (`#[cfg(kani)]`) can overlay either;
- **new concept-spec obligations** for the core-functional layer, plus the
  6 existing obligations and 3 bridges restated with `verifier: creusot` or
  `verifier: verus`;
- **interactions re-declared** with the owner's evidence kind (#151);
- **a decision on each missing std spec**: trusted spec or rewrite;
- **a decision on Poly1305**: attempt functional correctness (deep) or
  declare `partial`;
- **for Verus only**: `by(nonlinear_arith)` on every limb product.

**Expected outcomes:**
- **A7 (Creusot):** D over the core-functional layer and the
  bytes-layer obligations, or P if Poly1305 functional correctness is not
  attempted.
- **A8 (Verus):** the same; under Q1 a refusal on the pure Verus closure
  would be a Ligature defect.

**For the composition rows.** The plan's split is the natural shape for B3,
B4 and B5:
- the core-functional layer (quarter-round, block, Poly1305 limbs) goes to
  a deductive owner;
- the bytes layer (AEAD, keystream application, the existing 6 obligations)
  goes to Kani.

For B5 (all three verifiers), this analysis suggests:
- ChaCha20's core to Verus, which handles bit arithmetic well;
- Poly1305's limbs to Creusot, which proves the products unaided;
- the AEAD bytes layer to Kani.

## Findings recorded

- `crypto-verus-001` (verus, friction): 6 of P3's 16 std calls have no Verus
  specification.
- `crypto-creusot-001` (creusot, friction): 5 of the 16 have no Creusot
  contract.
- `crypto-verus-002` (verus, friction): Poly1305 limb products need
  `by(nonlinear_arith)` per product, where Creusot needs none.

All three are also in `PORT-GAPS.md`.
