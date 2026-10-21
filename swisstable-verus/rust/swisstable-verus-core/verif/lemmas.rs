//! Manual lemmas this port needed.
//!
//! Everything here is a *real* lemma over the port's own definitions: no
//! `assume`, no `admit`, no `external_body`, no `#[verifier::external]`.  Each
//! one exists because SMT could not derive it from the surrounding loop
//! invariants, and each is reported in `findings/limitations.jsonl` rather than
//! left as an invisible convenience.
//!
//! ## The bit-vector bridge
//!
//! Verus 0.2026.05.24 *does* reason about integer `&`, `|`, `<<` and `>>`: a
//! `#[verifier::bit_vector]` proof function is discharged by Z3's bit-vector
//! theory, and an integer-mode `ensures` mentioning them only needs those facts
//! stated as lemmas first.  Chainlink #30's first attempt concluded otherwise --
//! see `swisstable-verus-014` for the correction -- and rewrote the reference's
//! operators as arithmetic substitutes on the strength of that.  The bridge
//! lemmas below are what the reference's own operators need, and they restore the
//! operators: `H2` is `hash >> 57` again, the probe wraps with `& capacity_mask`
//! again, and the group answers are `uint16_t` masks again.
//!
//! Verified by: `verus --crate-type=lib src/lib.rs` (see `analysis/verus/` for
//! the captured transcript).

use crate::control_bytes::{ControlBytes, DELETED};
#[cfg(verus_only)]
use crate::control_bytes::{seq_dead_count, seq_free_count, seq_full_count};
use vstd::prelude::*;

verus! {

/// `TableIterator::advance` needs this to turn its exit condition into "rests on
/// a full slot": in a real slot a control byte that is not empty-or-deleted is a
/// full byte, because ControlBytes.C002 makes the sentinel the only byte that is
/// neither and it sits at index `capacity`.
pub proof fn lemma_not_free_gives_full(ctrl: &ControlBytes, slot: int)
    requires
        ctrl.well_formed(),
        0 <= slot < ctrl.capacity as int,
        !ctrl.is_empty_or_deleted_spec(slot),
    ensures ctrl.is_full_spec(slot),
{
    if ctrl.bytes[slot] >= crate::control_bytes::EMPTY {
        assert(ctrl.bytes[slot] == crate::control_bytes::SENTINEL);
        assert(false);
    }
}

/// The converse of `lemma_not_free_gives_full`: a full slot is never free, which is
/// what discharges `TableIterator::advance`'s frame invariant at loop entry.
pub proof fn lemma_full_is_not_free(ctrl: &ControlBytes, slot: int)
    requires
        ctrl.well_formed(),
        0 <= slot < ctrl.capacity as int,
        ctrl.is_full_spec(slot),
    ensures !ctrl.is_empty_or_deleted_spec(slot),
{
    if ctrl.bytes[slot] == crate::control_bytes::EMPTY
        || ctrl.bytes[slot] == crate::control_bytes::DELETED
    {
        assert(false);
    }
}

// Verus allows exactly one module-level `broadcast use` per module, and both of
// these are needed by almost every proof in this file: `lemma_add_group_width_mod`
// needs the `%` facts, and every extensionality proof needs `Set::new` /
// `Set::insert` / `Set::remove`, which are closed in vstd and so cannot be unfolded
// at a use site.
broadcast use {
    vstd::arithmetic::div_mod::group_mod_properties,
    vstd::set::group_set_axioms,
};

// ===========================================================================
// Bit-vector bridge: integer-mode facts about `&`, `|`, `<<`, `>>`.
// ===========================================================================

/// `x & m` is bounded by both operands.  This is the one fact every masked
/// offset in `ProbeSeq` needs (`offset_ & capacity_mask <= capacity_mask`), and
/// integer mode cannot derive it on its own.
#[verifier::bit_vector]
pub proof fn lemma_and_below(x: u64, m: u64)
    ensures
        (x & m) <= m,
        (x & m) <= x,
{
}

/// `x & m <= m` for `usize`, which `claim_first_free` needs for its start index.
#[verifier::bit_vector]
pub proof fn lemma_and_below_usize(x: usize, m: usize)
    ensures
        (x & m) <= m,
        (x & m) <= x,
{
}

/// `H2`: the top seven bits of a hash, and the fact that the shift is a division
/// by `2^57`.  The second conjunct is what makes `hash >> 57` fit in a `u8`.
#[verifier::bit_vector]
pub proof fn lemma_shr57(x: u64)
    ensures
        x >> 57 < 128,
        x >> 57 == x / 0x0200_0000_0000_0000,
{
}

/// `1u64 << bits` is at least one and at most `2^62` for `bits <= 62`.
/// The first conjunct discharges the `- 1` in `slots_for_bits`; the second keeps
/// `offset_ + index_` overflow-free (ProbeSeq's `capacity_bits <= 62` bound).
///
/// The upper bound is `2^62`, not `2^63`: `2^63 + 2^63` overflows, so the triple-step
/// `offset_ + index_ + 16` needs the headroom that `capacity_bits <= 62` buys.
#[verifier::bit_vector]
pub proof fn lemma_pow2_range(bits: u32)
    requires
        bits <= 62,
    ensures
        1u64 << bits >= 1,
        (1u64 << bits) - 1 <= 0x3FFF_FFFF_FFFF_FFFFu64,
{
}

/// The narrowing bridge, in its *bounded* form.
///
/// An earlier revision of this file recorded (`swisstable-verus-016`) that "no
/// postcondition crossing the narrowing cast is provable".  That is true only of
/// the **unbounded** cast: `fn(x: u64) -> usize { x as usize }` with no bound has
/// no postcondition relating the result to its source.  Under an explicit
/// `x <= 0x7FFF_FFFF` precondition the cast round-trips in both views, and this
/// lemma is what the port's constructors use.
///
/// This is not an axiom about the width of `usize` -- it holds for a target at
/// least as wide as `2^31 - 1`, which is the only property the port needs and
/// which `ControlBytes::new` already required as a literal.  What is *still*
/// unprovable is the unbounded form, and `usize::MAX` is nameable only as a
/// disjunction; see `swisstable-verus-025`.
pub proof fn lemma_narrow_roundtrip(x: u64)
    requires x <= 0x7FFF_FFFFu64,
    ensures
        (x as usize) as u64 == x,
        (x as usize) as int == x as int,
        (x as usize) as nat == x as nat,
{
}

/// Two bounded `usize` values with the same `u64` view are the same value, and
/// the same in the `<=` direction.  This is what lets `ProbeSeq`'s `u64` mask be
/// compared against the table's `usize` capacity without naming `usize`'s width.
pub proof fn lemma_narrow_eq(a: usize, b: usize)
    requires
        a <= 0x7FFF_FFFFusize,
        b <= 0x7FFF_FFFFusize,
        a as u64 == b as u64,
    ensures a == b
{
}

pub proof fn lemma_narrow_le(a: usize, b: usize)
    requires
        a <= 0x7FFF_FFFFusize,
        b <= 0x7FFF_FFFFusize,
        a as u64 <= b as u64,
    ensures a <= b
{
}

/// `usize::MAX` is nameable as a disjunction -- more than "opaque", less than a
/// usable maximum, since no `usize` arithmetic bound is discharged from it.
/// Recorded as `swisstable-verus-025`; the port states every upper bound as a
/// literal instead.
pub fn lemma_usize_max_is_one_of_two() -> (r: u64)
    ensures r == 0xFFFF_FFFFu64 || r == 0xFFFF_FFFF_FFFF_FFFFu64
{
    usize::MAX as u64
}

/// `2^n - 1` is at least the group width for `n >= 5`, and exactly `15` at `n == 4`.
/// This is what makes a `RawTable`'s capacity large enough for `ControlBytes::new`
/// (`capacity >= GROUP_WIDTH`) and for a whole group to be loadable.
///
/// Note the off-by-one this records: the smallest drafted capacity, `2^4 - 1 == 15`,
/// is one slot short of a group.  `RawTable::new` therefore asks for `5 <=
/// capacity_bits`, one more than `ProbeSeq.C001` states, and says so.
#[verifier::bit_vector]
pub proof fn lemma_slots_at_least_group(bits: u32)
    requires
        5 <= bits,
        bits <= 62,
    ensures
        (1u64 << bits) - 1 >= 16u64,
{
}

/// `2^bits - 1 <= 0xFFFF_FFFF` for `bits <= 31`, the bound the constructors need
/// before narrowing the capacity into a `usize`.
///
/// The bound is `2^31 - 1 == 0x7FFF_FFFF`, not `0xFFFF_FFFF`: that is the figure
/// `ControlBytes::new`'s precondition asks for, and since `bits <= 31` the stronger
/// bound is equally true. An earlier revision carried `0xFFFF_FFFF`, which left
/// `raw_table.rs:138`'s call with an undischarged precondition and moved the failure
/// rather than fixing it (`swisstable-verus-018`).
///
/// This is a statement about `u64` only; it does not depend on how wide `usize` is.
/// What the port cannot state is the *reverse* direction -- that the narrowed value
/// round-trips -- because Verus leaves `x as usize` opaque in both directions and
/// will not name `usize::MAX`.  See `swisstable-verus-016`.
#[verifier::bit_vector]
pub proof fn lemma_slots_roundtrip(bits: u32)
    requires bits <= 31
    ensures (1u64 << bits) - 1 <= 0x7FFF_FFFFu64
{
}

/// `2^bits - 1` grows with `bits`.
///
/// `SwissTable::reserve` grows by one bit and `RawTable::resize` asks that the
/// new capacity hold every live element, so the container has to know the new
/// capacity is at least the old one.  Upstream gets this from `NormalizeCapacity`'s
/// `NormalizeCapacity`/`MaxValidCapacity` arithmetic in `raw_hash_set.h`; the port
/// takes the capacity as a parameter, so the monotonicity has to be a fact.
#[verifier::bit_vector]
pub proof fn lemma_slots_monotone(bits: u32)
    requires bits <= 30
    ensures (1u64 << bits) - 1 <= (1u64 << (bits + 1)) - 1
{
}

/// A prefix count is at most the prefix length.
///
/// Together with `model`'s `len_ == seq_full_count` this is how a caller knows a
/// table is no fuller than its capacity without inverting the recursion.
pub proof fn lemma_full_count_le(s: Seq<u8>, n: nat)
    requires n <= s.len()
    ensures seq_full_count(s, n) <= n,
    decreases n,
{
    if n > 0 {
        assert((n - 1) as nat <= s.len());
        lemma_full_count_le(s, (n - 1) as nat);
        assert(seq_full_count(s, n) == seq_full_count(s, (n - 1) as nat)
            + (if s[((n - 1) as nat) as int] as int <= 127 { 1nat } else { 0nat }));
    }
}

/// A prefix count never shrinks as the prefix grows.
///
/// `RawTable::resize` re-inserts one live element per tombstone it walks past, and
/// has to know that the elements placed so far are still fewer than the new
/// capacity holds -- otherwise `insert`'s "a slot is left" precondition is not
/// derivable from the counting invariant alone.
pub proof fn lemma_full_count_mono(s: Seq<u8>, m: nat, n: nat)
    requires
        m <= n,
        n <= s.len(),
    ensures seq_full_count(s, m) <= seq_full_count(s, n),
    decreases n - m,
{
    if m < n {
        assert((m + 1) as nat <= n);
        lemma_full_count_mono(s, (m + 1) as nat, n);
        assert(seq_full_count(s, (m + 1) as nat) == seq_full_count(s, m)
            + (if s[m as int] as int <= 127 { 1nat } else { 0nat }));
    }
}

/// `seq_free_count` is at least one when some byte in the prefix is empty-or-deleted.
///
/// `claim_first_free` walks forward from `start` for at most `capacity` steps and
/// returns `(off, true)` as soon as it finds one.  Proving it always succeeds needs
/// the connection between `seq_free_count` (which counts over a *prefix*) and the
/// cyclic scan, and the counting recursion's trigger does not instantiate against
/// the scan's indices -- so the step is stated here and applied at the call site,
/// where `has_free_slot()` has already established the antecedent.
pub proof fn lemma_free_count_positive(s: Seq<u8>, n: nat, slot: int)
    requires
        n as int <= s.len(),
        0 <= slot < n as int,
        s[slot] == crate::control_bytes::EMPTY || s[slot] == crate::control_bytes::DELETED,
    ensures seq_free_count(s, n) >= 1,
    decreases n
{
    if n == 0 {
        assert(false);
    } else if slot < (n - 1) as int {
        lemma_free_count_positive(s, (n - 1) as nat, slot);
        assert(seq_free_count(s, n) == seq_free_count(s, (n - 1) as nat)
            + (if s[(n - 1) as int] == crate::control_bytes::EMPTY
                    || s[(n - 1) as int] == crate::control_bytes::DELETED {
                    1nat } else { 0nat }));
    } else {
        assert(slot == (n - 1) as int);
        assert(seq_free_count(s, n) == seq_free_count(s, (n - 1) as nat)
            + (if s[(n - 1) as int] == crate::control_bytes::EMPTY
                    || s[(n - 1) as int] == crate::control_bytes::DELETED {
                    1nat } else { 0nat }));
    }
}

/// `seq_free_count` is zero when no byte in the prefix is empty-or-deleted.
///
/// The other half of `lemma_free_count_positive`, and the step that lets
/// `claim_first_free` conclude its scan *always* succeeds when a free slot exists:
/// having scanned every slot and found none free would make the count zero.
pub proof fn lemma_free_count_zero(s: Seq<u8>, n: nat)
    requires
        n <= s.len(),
        forall|i: int| 0 <= i < n as int
            ==> !crate::control_bytes::is_empty_or_deleted_in(s, i),
    ensures seq_free_count(s, n) == 0,
    decreases n
{
    if n > 0 {
        assert((n - 1) as nat <= s.len());
        assert forall|i: int| 0 <= i < (n - 1) as int
            implies !crate::control_bytes::is_empty_or_deleted_in(s, i) by {
        }
        lemma_free_count_zero(s, (n - 1) as nat);
        assert(!crate::control_bytes::is_empty_or_deleted_in(s, (n - 1) as int));
    }
}

/// The converse of `lemma_free_count_zero`: a zero count means no byte in the
/// prefix is empty-or-deleted.
///
/// This is what `RawTable::is_full` needs -- it counts with
/// `count_empty_or_deleted`, whose postcondition is the counting form, and the
/// `has_free_slot` form is the existential.
pub proof fn lemma_free_count_zero_inv(s: Seq<u8>, n: nat)
    requires
        n <= s.len(),
        seq_free_count(s, n) == 0,
    ensures forall|i: int| 0 <= i < n as int
        ==> !crate::control_bytes::is_empty_or_deleted_in(s, i),
    decreases n
{
    if n > 0 {
        assert((n - 1) as nat <= s.len());
        assert(seq_free_count(s, (n - 1) as nat)
            + (if s[(n - 1) as int] == crate::control_bytes::EMPTY
                    || s[(n - 1) as int] == crate::control_bytes::DELETED {
                    1nat } else { 0nat }) == 0);
        assert(!(s[(n - 1) as int] == crate::control_bytes::EMPTY
            || s[(n - 1) as int] == crate::control_bytes::DELETED));
        lemma_free_count_zero_inv(s, (n - 1) as nat);
    }
}

/// A zero free count means no slot is empty-or-deleted, stated over the
/// `ControlBytes` method form rather than the free-function one.
///
/// `RawTable::is_full` needs this and the existential `has_free_slot` in the same
/// breath, and the two are separate triggers over separate terms: the counting
/// recursion gives the `Seq` form, `has_free_slot` asks about
/// `is_empty_or_deleted_spec`, and the SMT will not connect them.  Doing it here
/// puts both in one place, where the recursion is available.
pub proof fn lemma_zero_free_means_no_free_slot(ctrl: &crate::control_bytes::ControlBytes)
    requires
        ctrl.well_formed(),
        seq_free_count(ctrl.bytes@, ctrl.capacity as nat) == 0,
    ensures forall|i: int| 0 <= i < ctrl.capacity as int
        ==> !ctrl.is_empty_or_deleted_spec(i),
{
    lemma_free_count_zero_inv(ctrl.bytes@, ctrl.capacity as nat);
    assert forall|i: int| 0 <= i < ctrl.capacity as int
        implies !ctrl.is_empty_or_deleted_spec(i) by {
        if 0 <= i && i < ctrl.capacity as int {
            assert(!crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i));
            assert(!ctrl.is_empty_or_deleted_spec(i));
        }
    }
}

/// `RawTable::is_full`'s `true` arm: a zero free count means `has_free_slot` is
/// false, where `has_free_slot` is the *existential* over `is_empty_or_deleted_in`.
///
/// Turning a universal into the negation of an existential needs its own step when
/// the two are stated over different terms, which is the case here.
pub proof fn lemma_zero_free_gives_not_has_free(
    ctrl: &crate::control_bytes::ControlBytes,
)
    requires
        ctrl.well_formed(),
        seq_free_count(ctrl.bytes@, ctrl.capacity as nat) == 0,
    ensures !exists|i: int| 0 <= i < ctrl.capacity as int
        && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i),
{
    lemma_free_count_zero_inv(ctrl.bytes@, ctrl.capacity as nat);
    if exists|i: int| 0 <= i < ctrl.capacity as int
        && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i) {
        let witness: int = choose|i: int| 0 <= i < ctrl.capacity as int
            && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i);
        assert(crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, witness));
        assert(false);
    }
}

/// `RawTable::is_full`'s `false` arm: a positive free count means `has_free_slot`.
///
/// By induction on the prefix length: a positive count at `n` means either the last
/// byte is free (witness it) or the count at `n - 1` was already positive.
pub proof fn lemma_positive_free_gives_has_free(
    ctrl: &crate::control_bytes::ControlBytes,
    n: nat,
)
    requires
        ctrl.well_formed(),
        (ctrl.capacity as nat) >= n,
        seq_free_count(ctrl.bytes@, n) > 0,
    ensures exists|i: int| 0 <= i < ctrl.capacity as int
        && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i),
    decreases n
{
    if n == 0 {
        assert(false);
    } else {
        assert(seq_free_count(ctrl.bytes@, n)
            == seq_free_count(ctrl.bytes@, (n - 1) as nat)
                + (if ctrl.bytes@[((n - 1) as nat) as int] == crate::control_bytes::EMPTY
                        || ctrl.bytes@[((n - 1) as nat) as int] == crate::control_bytes::DELETED {
                    1nat } else { 0nat }));
        if seq_free_count(ctrl.bytes@, (n - 1) as nat) > 0 {
            lemma_positive_free_gives_has_free(ctrl, (n - 1) as nat);
        } else {
            assert(crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@,
                ((n - 1) as nat) as int));
            assert(0 <= ((n - 1) as nat) as int);
            assert((ctrl.capacity as nat) >= n);
            assert(exists|i: int| 0 <= i < ctrl.capacity as int
                && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i));
        }
    }
}

/// The contradiction `claim_first_free`'s exit needs: if the two linear scans
/// found nothing in `[start, cap)` and in `[0, start)`, no slot is reusable at all.
///
/// `Verus 0.2026.05.24` does **not** let `assert forall ... by { }` assume the
/// antecedent of its outermost implication, so the contradiction has to be stated
/// where the loop invariants are available -- which is why this is a lemma over
/// the two scans' facts rather than an assertion at the call site.  (The behaviour
/// is the subject of Verus issue "Don't always make assert forall assume the
/// antecedent".)
///
/// The postcondition is `false`, because `claim_first_free` needs the
/// **completeness** half of the contract -- that the scan never comes back empty
/// handed -- and a `!exists` would not give it that.  That is only sound because
/// the existential is a *precondition*: the two scans found nothing, so nothing is
/// free, so the existential the caller supplied is refuted.  An earlier revision of
/// this lemma left the existential out of the `requires`, which made both the
/// lemma and its `!exists` postcondition vacuous -- the `if` body was not
/// reachable from the premises alone -- and `claim_first_free` was then unable to
/// claim that it always finds a slot.  See `swisstable-verus-029`.
pub proof fn lemma_scan_contradiction(
    ctrl: &crate::control_bytes::ControlBytes,
    start: int,
    cap: int,
)
    requires
        ctrl.well_formed(),
        cap == ctrl.capacity as int,
        0 <= start,
        start < cap,
        // `[start, cap)` scanned and found nothing
        forall|t: int| start <= t && t < cap ==> !ctrl.is_empty_or_deleted_spec(t),
        // `[0, start)` scanned and found nothing -- the second loop ran to `start`
        forall|t: int| 0 <= t && t < start ==> !ctrl.is_empty_or_deleted_spec(t),
        // ... and the caller had a reusable slot to begin with
        exists|t: int| 0 <= t && t < cap
            && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, t),
    ensures false,
{
    if exists|t: int| 0 <= t && t < cap
        && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, t) {
        let witness: int = choose|t: int| 0 <= t && t < cap
            && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, t);
        assert(0 <= witness);
        assert(witness < cap);
        assert(crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, witness));
        if witness < start {
            assert(witness < start);
            assert(!ctrl.is_empty_or_deleted_spec(witness));
        } else {
            assert(start <= witness);
            assert(!ctrl.is_empty_or_deleted_spec(witness));
        }
        assert(false);
    }
}

/// "Every slot in `[0, n)` is empty-or-deleted" implies one is, as the existential
/// `has_free_slot` states it.
///
/// The two directions of that predicate are separate triggers -- the universal one
/// has `bytes[i]` at its core, the existential one is stated in the same order
/// `has_free_slot` states it -- and the SMT will not connect them on its own.
pub proof fn lemma_all_free_gives_one_free(s: Seq<u8>, n: nat)
    requires
        n as int <= s.len(),
        n > 0,
        forall|i: int| 0 <= i < n as int ==> crate::control_bytes::is_empty_or_deleted_in(s, i),
    ensures exists|i: int| 0 <= i < n as int
        && crate::control_bytes::is_empty_or_deleted_in(s, i),
{
    assert(crate::control_bytes::is_empty_or_deleted_in(s, 0));
}

/// `RawTable::new`'s step: a fresh table has a reusable slot.
pub proof fn lemma_all_empty_gives_free_slot(
    ctrl: &crate::control_bytes::ControlBytes,
)
    requires
        ctrl.well_formed(),
        forall|i: int| 0 <= i < ctrl.capacity as int
            ==> ctrl.bytes@[i] == crate::control_bytes::EMPTY,
    ensures exists|i: int| 0 <= i < ctrl.capacity as int
        && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i),
{
    assert(ctrl.capacity >= crate::control_bytes::GROUP_WIDTH);
    assert(0 < ctrl.capacity);
    assert(crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, 0));
}

/// `RawTable::slot_model` restated over the two ghost snapshots a mutator takes
/// before its writes -- `before_bytes` = the control array, `before_hashes` = the
/// parallel hash array -- with both `i`-indices and the `NO_HASH` test in the
/// *snapshot* vocabulary instead of the receiver's.
///
/// `insert`, `erase` and `resize` all need this.  After the writes, the only
/// surviving facts about the old contents are the frame assertions
/// (`is_full_spec(j) <==> before_bytes[j] <= 0x7F`, `slot_hash(j) == before_hashes[j]`),
/// while the pre-state contract is phrased over the *receiver*
/// (`old(self).is_full_spec`, `old(self).slot_hash`).  Verus does not relate
/// `old(self).slot_hash(i)` to `before_hashes[i]` for us -- `slot_hash` is
/// `if 0 <= slot < hashes@.len() { hashes[slot] } else { NO_HASH }`, so the
/// pre-state term only unfolds under a length bound the post-state no longer has in
/// the same form.
///
/// The one non-obvious ingredient is that each proof block first asserts the
/// pre-state model's *own* trigger term (`t.ctrl.is_full_spec(i)`) at the bound
/// index.  Those facts are universally quantified, and a universally quantified
/// axiom does not instantiate at another universally quantified goal's bound
/// variable unless a matching instance of its trigger is already in context.  With
/// the trigger asserted first, each block closes on the body facts alone.
pub proof fn lemma_slot_model_snapshot(
    t: &crate::raw_table::RawTable,
    before_bytes: Seq<u8>,
    before_hashes: Seq<u64>,
)
    requires
        t.model(),
        t.ctrl.bytes@ == before_bytes,
        t.hashes@ == before_hashes,
    ensures
        forall|i: int| 0 <= i < t.ctrl.capacity as int
            ==> (before_bytes[i] <= 0x7F
                    ==> before_hashes[i] != crate::raw_table::NO_HASH)
                && (before_bytes[i] > 0x7F
                    ==> before_hashes[i] == crate::raw_table::NO_HASH),
        forall|i: int| 0 <= i < t.ctrl.capacity as int && before_bytes[i] <= 0x7F
            ==> #[trigger] before_bytes[i] == (before_hashes[i] >> 57) as u8,
        forall|i: int, j: int| 0 <= i < j < t.ctrl.capacity as int
                && before_bytes[i] <= 0x7F && before_bytes[j] <= 0x7F
            ==> before_hashes[i] != before_hashes[j],
{
    let cap = t.ctrl.capacity as int;
    assert forall|i: int| 0 <= i < cap && before_bytes[i] <= 0x7F
        implies before_hashes[i] != crate::raw_table::NO_HASH by {
        if 0 <= i < cap && before_bytes[i] <= 0x7F {
            assert(t.ctrl.is_full_spec(i));
            assert(t.slot_hash(i) == before_hashes[i]);
            assert(t.slot_hash(i) != crate::raw_table::NO_HASH);
        }
    }
    assert forall|i: int| 0 <= i < cap && before_bytes[i] > 0x7F
        implies before_hashes[i] == crate::raw_table::NO_HASH by {
        if 0 <= i < cap && before_bytes[i] > 0x7F {
            assert(!t.ctrl.is_full_spec(i));
            assert(t.slot_hash(i) == before_hashes[i]);
            assert(t.slot_hash(i) == crate::raw_table::NO_HASH);
        }
    }
    assert forall|i: int| 0 <= i < cap && before_bytes[i] <= 0x7F
        implies before_bytes[i] == (before_hashes[i] >> 57) as u8 by {
        if 0 <= i < cap && before_bytes[i] <= 0x7F {
            assert(t.ctrl.is_full_spec(i));
            assert(#[trigger] t.ctrl.bytes[i] == (t.slot_hash(i) >> 57) as u8);
            assert(t.slot_hash(i) == before_hashes[i]);
        }
    }
    assert forall|i: int, j: int| 0 <= i < j < cap
            && before_bytes[i] <= 0x7F && before_bytes[j] <= 0x7F
        implies before_hashes[i] != before_hashes[j] by {
        if 0 <= i < j < cap && before_bytes[i] <= 0x7F && before_bytes[j] <= 0x7F {
            assert(t.ctrl.is_full_spec(i));
            assert(t.ctrl.is_full_spec(j));
            assert(t.slot_hash(i) == before_hashes[i]);
            assert(t.slot_hash(j) == before_hashes[j]);
            assert(t.slot_hash(i) != t.slot_hash(j));
        }
    }
}

/// `seq_full_count` is zero when no byte in the prefix is full.  `RawTable::new`
/// needs it to discharge `len_ == 0` and `stored_hashes() =~= Set::empty()`.
pub proof fn lemma_full_count_zero(s: Seq<u8>, n: nat)
    requires
        n <= s.len(),
        forall|i: int| 0 <= i < n ==> s[i] as int > 127,
    ensures seq_full_count(s, n) == 0,
    decreases n,
{
    if n > 0 {
        assert(n - 1 <= s.len());
        assert forall|i: int| 0 <= i < (n - 1) as int implies s[i] as int > 127 by {
            assert(s[i] as int > 127);
        }
        lemma_full_count_zero(s, (n - 1) as nat);
    }
}

/// `seq_full_count` is at least one when some byte in the prefix is full.
///
/// `RawTable::erase` needs the element count to be positive before it may
/// decrement it, and `find`/`contains` need it to be positive once they have
/// located a full slot.  `model` pins `len_` to `seq_full_count`, so this is the
/// step that turns "that slot is full" into "`len_ > 0`".
pub proof fn lemma_full_count_positive(s: Seq<u8>, n: nat, slot: int)
    requires
        n as int <= s.len(),
        0 <= slot < n as int,
        s[slot] as int <= 127,
    ensures seq_full_count(s, n) >= 1,
    decreases n
{
    if n == 0 {
        assert(false);
    } else if slot < (n - 1) as int {
        lemma_full_count_positive(s, (n - 1) as nat, slot);
        assert(s[(n - 1) as int] as int <= 127 || s[(n - 1) as int] as int > 127);
        assert(seq_full_count(s, n) == seq_full_count(s, (n - 1) as nat)
            + (if s[(n - 1) as int] as int <= 127 { 1nat } else { 0nat }));
    } else {
        assert(slot == (n - 1) as int);
        assert(seq_full_count(s, n) == seq_full_count(s, (n - 1) as nat)
            + (if s[(n - 1) as int] as int <= 127 { 1nat } else { 0nat }));
    }
}

/// `seq_full_count` on two arrays that agree everywhere in `[0, n)`.
pub proof fn lemma_full_count_same(a: Seq<u8>, b: Seq<u8>, n: nat)
    requires
        a.len() == b.len(),
        n as int <= a.len(),
        forall|i: int| 0 <= i < n as int ==> a[i] == b[i],
    ensures seq_full_count(a, n) == seq_full_count(b, n),
    decreases n
{
    if n > 0 {
        assert((n - 1) as nat <= a.len());
        assert(a[(n - 1) as int] == b[(n - 1) as int]);
        assert forall|i: int| 0 <= i < (n - 1) as int implies a[i] == b[i] by {
            assert(a[i] == b[i]);
        }
        lemma_full_count_same(a, b, (n - 1) as nat);
    }
}

/// `seq_full_count` moved by exactly the one slot the two arrays disagree about.
///
/// This is the **counting contract** every mutator in the re-scoped
/// `raw_table.rs` rests on: `insert` and `erase` write one control byte, and this
/// is what turns "that byte's full-ness flipped" into "the element count moved by
/// one", without any mention of the derived `Set`.
pub proof fn lemma_full_count_slot(a: Seq<u8>, b: Seq<u8>, n: nat, slot: int)
    requires
        a.len() == b.len(),
        n as int <= a.len(),
        0 <= slot < n as int,
        forall|i: int| 0 <= i < n as int && i != slot ==> a[i] == b[i],
    ensures
        seq_full_count(a, n) + (if b[slot] as int <= 127 { 1nat } else { 0nat })
            == seq_full_count(b, n) + (if a[slot] as int <= 127 { 1nat } else { 0nat }),
    decreases n
{
    if n > 0 {
        assert((n - 1) as nat <= a.len());
        if slot < (n - 1) as int {
            lemma_full_count_slot(a, b, (n - 1) as nat, slot);
            assert(a[(n - 1) as int] == b[(n - 1) as int]);
        } else {
            assert(slot == (n - 1) as int);
            assert forall|i: int| 0 <= i < (n - 1) as int implies a[i] == b[i] by {
                assert(a[i] == b[i]);
            }
            lemma_full_count_same(a, b, (n - 1) as nat);
        }
        assert(seq_full_count(a, n) == seq_full_count(a, (n - 1) as nat)
            + (if a[(n - 1) as int] as int <= 127 { 1nat } else { 0nat }));
        assert(seq_full_count(b, n) == seq_full_count(b, (n - 1) as nat)
            + (if b[(n - 1) as int] as int <= 127 { 1nat } else { 0nat }));
    }
}

/// Membership in the derived comprehension, unfolded.
pub proof fn lemma_stored_hashes_contains(hashes: Seq<u64>, capacity: int, k: u64)
    requires hashes.len() == capacity,
    ensures
        crate::raw_table::stored_hashes_of(hashes, capacity).contains(k)
            <==> (exists|i: int| 0 <= i < capacity && #[trigger] hashes[i] == k),
{
}

/// Membership in the table's own `stored_hashes()`, seen through the named predicate
/// `RawTable::stored_in`.
///
/// This is the step every insert/erase/clear obligation needs, and the one
/// `assert_sets_equal!` could not reach: `Set::new` is closed in vstd, so the
/// comprehension has to be named before anything can be seen through it.
pub proof fn lemma_stored_in(t: &crate::raw_table::RawTable, k: u64)
    requires
        t.slot_model(),
        t.ctrl.well_formed(),
    ensures t.stored_hashes().contains(k) <==> t.stored_in(k),
{
    assert forall|i: int| 0 <= i < t.ctrl.capacity as int
        implies t.stored_at(i, k)
            <==> (t.ctrl.is_full_spec(i) && t.hashes[i] == k) by {
    }
}

/// `x < 128` makes the `u64 -> u8` truncation lossless, which is what lets the tag
/// invariant `bytes[i] as u64 == slot_hash(i) >> 57` be *read back* in `slot_model`.
#[verifier::bit_vector]
pub proof fn lemma_narrow_u8(x: u64)
    requires x < 128
    ensures
        (x as u8) as u64 == x,
        (x as u8) as int == x as int,
{
}

/// The reference's `H2` tag as a `u8`, and the fact that reading it back out of a
/// control byte is lossless.
///
/// This is the shape `RawTable::slot_model`'s tag clause needs: the clause is stated
/// over `bytes[i] as u64` (so a caller can compare it against a `u64` hash), and
/// this lemma is what shows that comparison is the same as comparing the `u8` tag
/// against `(hash >> 57) as u8`.  Without it, `find` and `insert` cannot discharge
/// ControlBytes.C007 from `slot_model` alone.
#[verifier::bit_vector]
pub proof fn lemma_h2_roundtrip(hash: u64)
    ensures
        (hash >> 57) <= 127,
        ((hash >> 57) as u8) as u64 == hash >> 57,
{
}

// The derived-comprehension extensionality obligations -- `stored_hashes() =~=""
// Set::empty()` after `new`, the singleton after `insert`, the removal after `erase`
// -- are NOT discharged here.  `assert_sets_equal!` does not close them in this vstd
// even with `group_set_axioms` broadcast and the membership unfolding available
// (`lemma_stored_hashes_contains`, which does verify).  Nothing was stubbed out: the
// port contains no `assume`, `admit`, `external_body` or `axiom fn`, so the
// obligations simply remain open and are reported as `swisstable-verus-017`.

/// ProbeSeq.C003's step: adding the group width keeps the probe index a multiple of
/// it.  The reference's `index_ += Width` is the same statement.
///
/// The divisor is written as the literal `16` rather than as
/// `control_bytes::GROUP_WIDTH`: the broadcast group's instantiation needs the divisor
/// to be a numeral for Z3 to match it.
pub proof fn lemma_add_group_width_mod(x: u64)
    requires (x as int) % 16 == 0,
    ensures ((x + 16u64) as int) % 16 == 0,
{
    broadcast use vstd::arithmetic::div_mod::group_mod_properties;
    assert((x as int) / 16 * 16 == x);
    assert(((x + 16u64) as int) / 16 == (x as int) / 16 + 1);
}

/// Setting bit `i` of a `u16` group mask sets it, and leaves the rest of the
/// word to the matching loop invariant.
#[verifier::bit_vector]
pub proof fn lemma_bit_set(mask: u16, i: u32)
    requires i < 16
    ensures
        (mask | (1u16 << i)) & (1u16 << i) == 1u16 << i,
        ((mask | (1u16 << i)) >> i) & 1u16 == 1u16,
{
}

/// Setting bit `i` leaves bit `j` alone when `i != j`.
#[verifier::bit_vector]
pub proof fn lemma_or_preserves_other_bit(mask: u16, i: u32, j: u32)
    requires
        i < 16,
        j < 16,
        i != j,
    ensures
        ((mask | (1u16 << i)) >> j) & 1u16 == (mask >> j) & 1u16,
{
}

/// An empty `u16` mask has no bit set.
#[verifier::bit_vector]
pub proof fn lemma_zero_has_no_bit(j: u32)
    requires j < 16
    ensures ((0u16 >> j) & 1u16) == 0u16
{
}

/// `1u16 << i` is in range for `i < 16`, so building a mask by summing one-hot
/// terms cannot overflow `u16`.
#[verifier::bit_vector]
pub proof fn lemma_one_hot_fits(i: u32)
    requires i < 16
    ensures 1u16 << i >= 1u16
{
}

// ===========================================================================
// Counting
// ===========================================================================

/// `clear_dead` preserves the element count, *stated over the snapshot*.
///
/// An earlier revision of `RawTable::resize` needed this as a lemma: it counted
/// the tombstones the reclaim created and had to transfer that count to the
/// number of full bytes the rewrite destroyed.  The re-scoped `resize` states
/// its counting invariant as
/// `t.len_ == seq_full_count(before, x)` -- over the *pre-reclaim* array, where
/// the full bytes are still countable -- so the transfer is no longer needed
/// and the lemma had no caller left.  Deleted rather than left behind; see
/// `swisstable-verus-031` for the restructure that removed the need.

/// In a control array whose bytes are classified, every slot is exactly one of
/// "full" or "reusable", so the two prefix counts add up to the prefix length.
///
/// This is what turns `model`'s counting clause (`len_ == seq_full_count`) into
/// "a slot is left to insert into": `RawTable::resize` re-inserts one live
/// element per tombstone and needs a free slot to exist at *every* step, and the
/// existential `has_free_slot()` does not follow from `len_ < capacity` without
/// it.  Upstream's equivalent step is inside `Group::MatchEmptyOrDeleted` /
/// `find_first_non_full`, where the two classes are a `uint16_t` bit and its
/// complement rather than two recursive counts.
pub proof fn lemma_full_plus_free(s: Seq<u8>, n: nat)
    requires
        n <= s.len(),
        forall|i: int| 0 <= i < n as int
            ==> s[i] as int <= 127
                || s[i] == crate::control_bytes::EMPTY
                || s[i] == crate::control_bytes::DELETED,
    ensures seq_full_count(s, n) + seq_free_count(s, n) == n,
    decreases n,
{
    if n > 0 {
        assert((n - 1) as nat <= s.len());
        assert forall|i: int| 0 <= i < (n - 1) as int
            implies s[i] as int <= 127
                || s[i] == crate::control_bytes::EMPTY
                || s[i] == crate::control_bytes::DELETED by {
        }
        lemma_full_plus_free(s, (n - 1) as nat);
        let last = (n - 1) as int;
        assert(0 <= last && last < s.len());
        assert(s[last] as int <= 127
            || s[last] == crate::control_bytes::EMPTY
            || s[last] == crate::control_bytes::DELETED);
        assert(seq_full_count(s, n) == seq_full_count(s, (n - 1) as nat)
            + (if s[last] as int <= 127 { 1nat } else { 0nat }));
        assert(seq_free_count(s, n) == seq_free_count(s, (n - 1) as nat)
            + (if s[last] == crate::control_bytes::EMPTY
                    || s[last] == crate::control_bytes::DELETED { 1nat } else { 0nat }));
        // The classification makes the two last-byte indicators sum to one.
        assert((if s[last] as int <= 127 { 1nat } else { 0nat })
            + (if s[last] == crate::control_bytes::EMPTY
                    || s[last] == crate::control_bytes::DELETED { 1nat } else { 0nat })
            == 1nat);
    }
}

} // verus!
