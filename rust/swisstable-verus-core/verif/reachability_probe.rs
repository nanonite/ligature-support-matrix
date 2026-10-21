//! What Verus 0.2026.05.24 can and cannot say about integer bit operations.
//!
//! This file is a **standalone** probe: it declares its own bit-vector lemmas and
//! does not import anything from the crate, so it verifies on its own and its
//! transcript stands on its own.  `analysis/verus/run-verus.sh` captures it to
//! `analysis/verus/reachability-probe.txt`, and `write-findings-30.py` reads that
//! file's results line rather than a hardcoded string.
//!
//! **Chainlink #30 attempt 1 got this backwards.** It concluded from four probes
//! that Verus "supplies no axioms at all" for integer `&`, `|`, `<<`, `>>` and filed
//! that as a `blocker` (`swisstable-verus-012`, since retired), rewriting the
//! reference's operators as arithmetic substitutes. Every fact it called impossible
//! verifies here, and in the crate proper as well -- see
//! `rust/swisstable-verus-core/verif/lemmas.rs` for the same lemmas with their real
//! call sites. The correction is `swisstable-verus-014`.
//!
//! Reproduce with:
//! `nix develop <workspace>#swisstable-verus -c 'verus --crate-type=lib \
//!   rust/swisstable-verus-core/verif/reachability_probe.rs'
//!
//! The `errors` in its results line are the four deliberate negative cases at the
//! bottom of the file, each of which says in its own doc comment that it is expected
//! not to verify.`

use vstd::prelude::*;

verus! {

// ---- the four facts attempt 1 declared impossible ----------------------------

/// `x & m` is bounded by both operands.
#[verifier::bit_vector]
pub proof fn lemma_and_below(x: u64, m: u64)
    ensures
        (x & m) <= m,
        (x & m) <= x,
{
}

/// `H2`: the top seven bits, and that the shift is a division by `2^57`.
#[verifier::bit_vector]
pub proof fn lemma_shr57(x: u64)
    ensures
        x >> 57 < 128,
        x >> 57 == x / 0x0200_0000_0000_0000,
{
}

/// `1u64 << bits` is at least one and at most `2^62` for `bits <= 62`.
#[verifier::bit_vector]
pub proof fn lemma_pow2_range(bits: u32)
    requires bits <= 62
    ensures
        1u64 << bits >= 1,
        (1u64 << bits) - 1 <= 0x3FFF_FFFF_FFFF_FFFFu64,
{
}

/// Setting bit `i` of a `u16` group mask sets it.
#[verifier::bit_vector]
pub proof fn lemma_bit_set(mask: u16, i: u32)
    requires i < 16
    ensures
        (mask | (1u16 << i)) & (1u16 << i) == 1u16 << i,
        ((mask | (1u16 << i)) >> i) & 1u16 == 1u16,
{
}

// ---- the facts are callable from ordinary integer-mode executable code -------

/// Integer mode verifies `r == hash >> 57` on its own: the shift is a first-class
/// specification operation, not an opaque one.
pub fn probe_shift_is_spec_opaque(hash: u64) -> (r: u64)
    ensures r == hash >> 57
{
    hash >> 57
}

/// What integer mode does *not* derive is the bound the shift lands in, which is
/// what makes the `u64 -> u8` truncation lossless. One bit-vector lemma supplies it.
pub fn probe_shr57_fits_in_a_byte(hash: u64) -> (r: u8)
    ensures r as u64 == hash >> 57, r <= 0x7F
{
    proof { lemma_shr57(hash); }
    let t = hash >> 57;
    assert(t <= 0x7F);
    t as u8
}

/// `x & m <= m` -- the one bound every masked offset in `ProbeSeq` needs.
pub fn probe_mask_is_below_capacity(x: u64, m: u64) -> (r: u64)
    ensures r <= m
{
    proof { lemma_and_below(x, m); }
    x & m
}

/// The capacity shape `2^n - 1` cannot underflow.
pub fn probe_capacity_shape(bits: u32) -> (r: u64)
    requires bits <= 62
    ensures r == (1u64 << bits) - 1
{
    proof { lemma_pow2_range(bits); }
    let s: u64 = 1u64 << bits;
    s - 1
}

/// Setting bit `i` of a group mask sets it, which is what GroupProbe.C002 says.
pub fn probe_group_bit_is_set(mask: u16, i: u32) -> (r: u16)
    requires i < 16
    ensures (r >> i) & 1u16 == 1u16
{
    proof { lemma_bit_set(mask, i); }
    mask | (1u16 << i)
}

// ---- and what this Verus really cannot say about `usize` ---------------------

/// `std::mem::size_of::<usize>()` is **opaque**: it cannot be pinned to a width.
///
/// An earlier version of this file concluded `usize` is 32 bits, on the strength of a
/// probe whose postcondition restated its own body -- a tautology, true for any width,
/// so it "verified" and proved nothing.  Corrected to assert the literal `4`, this
/// postcondition **fails**, which is the honest result: the width is not a fact this
/// Verus will supply.  `swisstable-verus-016` is restated accordingly, and the port's
/// capacity cap no longer rests on a claimed width.
pub fn probe_size_of_usize_is_opaque() -> (r: u64)
    ensures r == 4
{
    std::mem::size_of::<usize>() as u64
}

/// `usize::MAX` is the one thing about `usize` that *cannot* be named: it is neither
/// `0xFFFF_FFFF` (32-bit) nor `0xFFFF_FFFF_FFFF_FFFF` (64-bit) in this build, so no
/// bound can be stated in terms of it and every round trip has to be phrased with a
/// literal instead.  This function is **expected not to verify**, and it is here so
/// the transcript carries the negative case rather than only this comment claiming it.
pub fn probe_usize_max_is_unnameable() -> (r: u64)
    ensures r == 0xFFFF_FFFFu64
{
    usize::MAX as u64
}

/// A `u64 -> usize` narrowing cast cannot be related to its source **at all** in
/// this Verus: no postcondition in terms of `x` is provable, whether stated as the
/// `u64` view or the `int` view.  This function is **expected not to verify**; an
/// earlier version of this file stated the postcondition as the body's own
/// expression, which made it a tautology and hid the real result.
///
/// Consequence for the port: `ProbeSeq::offset`/`offset_at` hand back a `usize`, and
/// their postconditions are therefore stated over the `int` view only.  The exact
/// masked value is still proved, in `advance`'s postcondition and in
/// `well_formed`, both of which are over `u64`.  See `swisstable-verus-016`.
pub fn probe_usize_roundtrip(x: u64) -> (r: usize)
    requires x <= 0xFFFF_FFFF_FFFF_FFFFu64
    ensures r as u64 == x
{
    x as usize
}

/// The same cast on the `int` view, which is what the port would need in order to
/// state an exact value clause.  Also **expected not to verify**.
pub fn probe_usize_roundtrip_int(x: u64) -> (r: usize)
    requires x <= 0xFFFF_FFFF_FFFF_FFFFu64
    ensures r as int == x as int
{
    x as usize
}

// ---- upstream's `WasNeverFull`, and the boundary its bit operations decide ----

/// Upstream `WasNeverFull`'s test (raw_hash_set.cc L708-L724), as a predicate over
/// the two run lengths its bit operations produce -- `fwd` is
/// `empty_after.TrailingZeros()` and `bwd` is `empty_before.LeadingZeros()`, both
/// capped at `kWidth`, so "the mask is non-zero" is exactly "the run is shorter
/// than the window".
///
/// The *sum* is the point: upstream compares `fwd + bwd` against `kWidth`, it does
/// not compare the two runs against each other.
pub open spec fn was_never_full_upstream(fwd: nat, bwd: nat) -> bool {
    &&& fwd < 16nat
    &&& bwd < 16nat
    &&& fwd + bwd < 16nat
}

/// What this port used to implement instead: the same two run lengths, compared
/// against *each other* instead of summed.  Kept here only so the transcript
/// carries the two concrete configurations where the two rules disagree;
/// `ControlBytes::was_never_full` implements `was_never_full_upstream`.
pub open spec fn was_never_full_misread(fwd: nat, bwd: nat) -> bool {
    &&& fwd < 16nat
    &&& bwd < 16nat
    &&& fwd <= bwd
}

/// `Group::MaskEmpty()` puts each byte's most significant bit at that byte's own
/// index (absl's `MoveMask`), so abstract bit `i` of the mask is set exactly when
/// the group's `i`-th control byte is `kEmpty`; and `kEmpty` is `-128`, whose MSB
/// is set.  Bit-vector mode settles the two concrete masks the boundary cases use:
///
/// * `0x0002` -- the *forward* window of a 16-wide full run around `index`: byte 0
///   non-`kEmpty`, byte 1 `kEmpty`.  `TrailingZeros()` counts the clear abstract
///   bits from bit 0, i.e. `fwd == 1`.
/// * `0x0001` -- the *backward* window of that same run, read at
///   `index_before = (index - Group::kWidth) & c.capacity()`, whose bit 15 is
///   `ctrl[index - 1]`: bytes 15..1 non-`kEmpty`, byte 0 `kEmpty`.
///   `LeadingZeros()` is `countl_zero(uint32_t(mask << 16))`
///   (`NonIterableBitMask`, hashtable_control_bytes.h L100-L104), i.e. the count of
///   clear abstract bits from bit 15 downwards, i.e. `bwd == 15`.
/// * `0x4000` / `0x0008` -- the mirror configuration: `bwd == 1`, `fwd == 3`.
///
/// The run-length *counters* are not modelled here: this file is standalone by
/// design and deliberately imports nothing from the crate, and this Verus does not
/// evaluate a bare recursive `open spec fn` over a 16-deep window inside a proof
/// body.  `control_bytes.rs` carries the real counters
/// (`empty_run_forward` / `empty_run_backward`) with their unfolding lemmas.
#[verifier::bit_vector]
pub proof fn lemma_boundary_mask_bits()
    ensures
        ((0x0002u16 >> 0u32) & 1u16) == 0u16,
        ((0x0002u16 >> 1u32) & 1u16) == 1u16,
        ((0x0001u16 >> 15u32) & 1u16) == 0u16,
        ((0x0001u16 >> 1u32) & 1u16) == 0u16,
        ((0x0001u16 >> 0u32) & 1u16) == 1u16,
        ((0x4000u16 >> 15u32) & 1u16) == 0u16,
        ((0x4000u16 >> 14u32) & 1u16) == 1u16,
        ((0x0008u16 >> 0u32) & 1u16) == 0u16,
        ((0x0008u16 >> 3u32) & 1u16) == 1u16,
{
}

/// The two boundary configurations, as run lengths.
///
/// * `fwd == 1`, `bwd == 15` is *16 consecutive full slots* around `index`.  Upstream's
///   sum is `1 + 15 == kWidth`, so it writes **`kDeleted`** -- exactly the case its own
///   comment names ("at least one probe window that might have seen a full group").
///   The `fwd <= bwd` transcription wrote `kEmpty`, because a 16-wide full run looks
///   "balanced" to it.
/// * `fwd == 3`, `bwd == 1` is the mirror image: upstream's sum is `4 < kWidth`, so it
///   writes **`kEmpty`**, while `3 <= 1` is false and the transcription wrote
///   `kDeleted`.
///
/// Both are ordinary reachable control-byte states -- neither needs a `kSentinel`
/// nor any byte the port cannot produce -- so the transcription error was
/// observable through `count_empty` and not merely a corner of the predicate.
/// See `swisstable-verus-030`.
pub proof fn lemma_was_never_full_boundary_cases()
    ensures
        !was_never_full_upstream(1, 15),
        was_never_full_misread(1, 15),
        was_never_full_upstream(3, 1),
        !was_never_full_misread(3, 1),
{
}

fn main() { }

} // verus!