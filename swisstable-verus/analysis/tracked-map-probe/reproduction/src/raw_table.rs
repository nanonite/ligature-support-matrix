//! RawTable -- the open-addressed slot array with its control bytes.
//!
//! Reference: absl/container/internal/raw_hash_set.cc L175-L220
//! (`probe_till_first_non_full_group`, `find_first_non_full_from_h1`,
//! `find_first_non_full`), L434-L447 (`ConvertDeletedToEmptyAndFullToDeleted`),
//! L593-L700 (`DropDeletesWithoutResizeAndPrepareInsert`), L708-L724
//! (`WasNeverFull`), L856-L883 (`EraseMetaOnlySmall` / `EraseMetaOnlyLarge`),
//! L2104-L2144 (`ResizeAllocatedTableWithSeedChange`), and raw_hash_set.h
//! L2451-L2456 (`skip_empty_or_deleted`).
//!
//! Representation: `Vec<u64>` control bytes plus a parallel `Vec<u64>` of slot
//! hashes.  No `unsafe`, no raw pointers, no `MaybeUninit` slots -- what that
//! costs against the reference, and what chainlink #35 still has to decide at
//! the descriptor level, is in `findings/limitations.jsonl`
//! (`swisstable-verus-001`).
//!
//! A hash of zero is refused at this level so that an erased slot can be zeroed
//! as its "no live key here" marker; see `NO_HASH`.
//!
//! ## The mutators' contracts are per-slot frame and counting contracts
//!
//! This is the contract shape chainlink #30's operator ruling of 2026-10-02
//! re-scoped the issue to.  Every mutator below states, and every `ensures`
//! discharges, exactly three kinds of obligation:
//!
//! * **per-slot** -- a fact about one named slot: after `insert` the returned
//!   slot is full, carries `hash`, and its control byte is `H2(hash)`
//!   (ControlBytes.C007); after `erase` the named slot reads as free.
//! * **per-slot frame** -- a fact about every *other* slot: `insert`, `erase`
//!   and `clear` leave `ctrl.bytes[j]` and `hashes[j]` untouched for every
//!   `j != slot`, and `resize` states the two survival directions slot by slot.
//! * **counting** -- `len_` moves by exactly the number of slots whose state
//!   changed, and `model()` pins `len_` to `seq_full_count`.
//!
//! What is *not* stated is `stored_hashes() =~= old(self).stored_hashes().insert(k)`
//! or any other set-level extensionality over the derived comprehension.  Four
//! strategies for discharging those were implemented and measured and none
//! closed (`swisstable-verus-023`); the operator ruled them out of scope and
//! recorded them as a limitation rather than a retry (`swisstable-verus-009`,
//! `-023`).  The membership fact itself is still provable
//! (`verif/lemmas.rs::lemma_stored_in`), so nothing is assumed away -- only the
//! two-directional equality is left as a stated scope cut.
//!
//! ## Why there is no `ghost` model field
//!
//! The plan's "ghost `Map` abstraction invariants" would naturally be a
//! `ghost live: Set<u64>` field.  Verus 0.2026.05.24 rejects that outright: a
//! specification-valued field initializer in executable code is an error
//! (`live: Set::<u64>::empty()` and `Ghost::new(Set::empty())` both fail to
//! compile), and a spec function cannot be called to build the field.  The model
//! is therefore *derived* -- `stored_hashes()` is a `Set::new` comprehension over
//! the full slots -- which needs no field, no ghost bookkeeping on the exec side,
//! and makes RawTable.C007 a statement about the arrays themselves.  Recorded as
//! `swisstable-verus-011`.  It is also why the per-slot contract shape is not an
//! evasion: with no model field to update, the arrays *are* the state, and a
//! frame condition on them is the honest statement.

use crate::control_bytes::{ControlBytes, DELETED, EMPTY, GROUP_WIDTH, PAD_BYTES, SENTINEL};
#[cfg(verus_only)]
use crate::control_bytes::{seq_dead_count, seq_free_count, seq_full_count};
use crate::group_probe::{bit_set, GroupProbe};
#[cfg(verus_only)]
use crate::group_probe::{bit_set_at, lemma_mask_bit_at};
use crate::hash_mix::HashMix;
#[cfg(verus_only)]
use crate::lemmas::{
    lemma_all_empty_gives_free_slot, lemma_and_below_usize,
    lemma_full_count_mono, lemma_full_count_slot, lemma_full_count_zero, lemma_full_plus_free,
    lemma_h2_roundtrip,
    lemma_narrow_le, lemma_narrow_roundtrip,
    lemma_positive_free_gives_has_free,
    lemma_pow2_range, lemma_scan_contradiction, lemma_shr57, lemma_slot_model_snapshot,
    lemma_slots_at_least_group,
    lemma_slots_roundtrip, lemma_stored_in, lemma_zero_free_gives_not_has_free,
    lemma_zero_free_means_no_free_slot,
};
use crate::probe_seq::{slots_for_bits, ProbeSeq};
#[cfg(verus_only)]
use crate::probe_seq::slots_for_bits_spec;
use vstd::prelude::*;

verus! {

broadcast use {vstd::map::group_map_axioms, vstd::set::group_set_axioms};

/// Incremental live-hash model: each key is a live hash and its value is the
/// current physical slot that stores it. This is ghost-only trusted state.
pub tracked struct LiveIndex {
    pub m: Map<u64, usize>,
}

/// The value an erased slot's hash field is reset to.  No live element ever
/// carries it, which is what lets `slot_model` read "hash zero" as "this slot
/// holds nothing".
pub const NO_HASH: u64 = 0;

/// Upstream `find_first_non_full_from_h1` (raw_hash_set.cc L189-L198) in its
/// scalar single-group form: the first empty-or-deleted slot at or after the H1
/// offset, wrapping round at the sentinel.
///
/// A module-private free function rather than a method: it is the probe
/// primitive that `insert` and `resize` share, and no concept spec attaches an
/// obligation of its own to it, so it is deliberately kept off `ControlBytes`'s
/// method list (recorded as `swisstable-verus-005`).
pub(crate) fn claim_first_free(ctrl: &ControlBytes, h1: u64) -> (r: (usize, bool))
    requires
        ctrl.well_formed(),
        // the existential form of "a reusable slot exists"; see `has_free_slot`
        exists|i: int| 0 <= i < ctrl.capacity as int
            && crate::control_bytes::is_empty_or_deleted_in(ctrl.bytes@, i),
    ensures
        // The scan is *complete*: given the precondition, it never reports failure.
        // Upstream's `find_first_non_full_from_h1` (raw_hash_set.cc L189-L198) has
        // the same shape -- it returns a slot and the caller does not re-test.
        r.1,
        r.1 ==> r.0 < ctrl.capacity,
        r.1 ==> ctrl.is_empty_or_deleted_spec(r.0 as int),
        r.0 <= ctrl.capacity,
{
    let cap = ctrl.capacity;
    proof { lemma_and_below_usize(h1 as usize, cap); }
    let mut start = (h1 as usize) & cap;
    if start == cap {
        start = 0;
    }
    // Upstream walks forward from `h1 & capacity_` and wraps at the sentinel.  This
    // port splits that into two *linear* scans -- `[start, capacity)` then
    // `[0, start)` -- which visit exactly the same slots in exactly the same order.
    // The split is not a behavioural change; it is what makes the frame a plain
    // interval, which is the form the SMT can carry: a single rotating cursor needs
    // a "which slots have been visited" set that the cyclic arithmetic does not
    // support, and the counting lemma that would supply it does not close.
    assert(ctrl.well_formed());
    assert(cap == ctrl.capacity);
    assert(start < cap);
    let mut off = start;
    while off < cap
        invariant
            off <= cap,
            start <= off,
            start < cap,
            cap == ctrl.capacity,
            ctrl.well_formed(),
            // `int`-quantified, not `usize`-quantified: the contradiction at the
            // exit of the second scan needs the `int` form, and Verus leaves
            // `i as usize` opaque in *both* directions, so a `usize`-quantified
            // invariant is not a usable premise for an `int`-quantified one.
            forall|t: int| start as int <= t && t < off as int
                ==> !ctrl.is_empty_or_deleted_spec(t),
        decreases cap - off,
    {
        assert(off < ctrl.capacity);
        if ctrl.is_empty_or_deleted(off) {
            return (off, true);
        }
        off = off + 1;
    }
    let mut lo: usize = 0;
    while lo < start
        invariant
            lo <= start,
            0 <= lo,
            start < cap,
            cap == ctrl.capacity,
            ctrl.well_formed(),
            // `[start, capacity)` is already scanned (the first loop ran to `cap`);
            // `[0, lo)` is scanned as `lo` advances.  Together they cover
            // `[0, capacity)`, which is what the contradiction below needs.  The two
            // arms are stated as two *separate* quantifiers over `int` because two
            // quantifiers over the same body with different triggers do not
            // instantiate against each other.
            forall|t: int| start as int <= t && t < cap as int
                ==> !ctrl.is_empty_or_deleted_spec(t),
            forall|t: int| 0 <= t && t < lo as int
                ==> !ctrl.is_empty_or_deleted_spec(t),
        decreases start - lo,
    {
        assert(lo < ctrl.capacity);
        if ctrl.is_empty_or_deleted(lo) {
            return (lo, true);
        }
        lo = lo + 1;
    }
    proof {
        // Both halves scanned every slot and found nothing, which contradicts the
        // existential the caller supplied.  The lemma's postcondition is `false`, so
        // the `false` arm below is unreachable and `r.1` is unconditional.
        lemma_scan_contradiction(ctrl, start as int, cap as int);
    }
    (cap, false)
}

/// The stored-hash model with no occupancy filter, as a free specification function
/// so the extensionality lemmas in `verif/lemmas.rs` can talk about two `Seq`s
/// rather than two `RawTable`s.  `RawTable::stored_hashes` is this restricted to
/// the slots `ctrl` says are full.
pub open spec fn stored_hashes_of(hashes: Seq<u64>, capacity: int) -> Set<u64> {
    Set::new(|k: u64| exists|i: int| 0 <= i < capacity && hashes[i] == k)
}

pub struct RawTable {
    /// The control array; its `capacity` field is this table's slot count.
    pub ctrl: ControlBytes,
    /// `hashes[i]` is meaningful exactly when `ctrl.is_full(i)`.
    pub hashes: Vec<u64>,
    /// The number of live elements.
    pub len_: usize,
    /// `log2(capacity + 1)`; RawTable.C001 states the capacity shape through it.
    pub capacity_bits: u32,
    /// Incrementally maintained live-hash to physical-slot map for the #120 probe.
    pub g: Tracked<LiveIndex>,
}

impl RawTable {
    pub fn new(capacity_bits: u32) -> (t: Self)
        requires
            5 <= capacity_bits,
            capacity_bits <= 31,
        ensures
            t.model(),
            t.capacity_bits == capacity_bits,
            t.len_ == 0,
            // A fresh table is entirely empty, so it has a free slot.  An earlier
            // revision asserted `!t.has_free_slot()`, which is FALSE -- every real
            // control byte is `kEmpty` -- and reached it with a lemma whose
            // precondition contradicted the very array it was applied to.
            t.has_free_slot(),
            // No slot is full.  `RawTable::resize` seeds its placement record with
            // this table and needs it: without it the "every full destination slot
            // names the tombstone it came from" invariant cannot be established
            // vacuously at the top of its loop.  It is the per-slot form of the
            // `stored_hashes() =~= Set::empty()` clause, which is set-level and
            // therefore out of scope (`swisstable-verus-023`).
            forall|i: int| 0 <= i < t.ctrl.capacity as int ==> !t.ctrl.is_full_spec(i),
            t.stored_hashes() =~= Set::<u64>::empty(),
    {
        proof {
            lemma_slots_at_least_group(capacity_bits);
            lemma_pow2_range(capacity_bits);
        }
        proof { lemma_slots_roundtrip(capacity_bits); }
        let capacity = slots_for_bits(capacity_bits) as usize;
        proof { lemma_narrow_roundtrip(slots_for_bits_spec(capacity_bits)); }
        assert(capacity >= crate::control_bytes::GROUP_WIDTH);
        assert(capacity as u64 == slots_for_bits_spec(capacity_bits));
        let ctrl = ControlBytes::new(capacity);
        let mut hashes: Vec<u64> = Vec::new();
        let mut i: usize = 0;
        while i < capacity
            invariant
                i <= capacity,
                hashes@.len() == i,
                forall|j: usize| j < i ==> hashes[j as int] == NO_HASH,
            decreases capacity - i,
        {
            hashes.push(NO_HASH);
            i = i + 1;
        }
        let tracked g = LiveIndex { m: Map::tracked_empty() };
        let t = RawTable {
            ctrl: ctrl,
            hashes: hashes,
            len_: 0,
            capacity_bits: capacity_bits,
            g: Tracked(g),
        };
        proof { lemma_full_count_zero(t.ctrl.bytes@, t.ctrl.capacity as nat); }
        proof {
            assert(t.ctrl.well_formed());
            assert(t.hashes.len() == t.ctrl.capacity);
            assert(t.ctrl.capacity as u64 == slots_for_bits_spec(capacity_bits));
            assert(5 <= t.capacity_bits <= 31);
            // a fresh table is all-`kEmpty`, so every slot is reusable
            assert forall|j: usize| j < t.ctrl.capacity
                implies t.ctrl.bytes[j as int] == crate::control_bytes::EMPTY by {
            }
            lemma_all_empty_gives_free_slot(&t.ctrl);
            assert(t.has_free_slot());
            assert forall|j: int| 0 <= j < t.ctrl.capacity as int
                implies t.ctrl.is_full_spec(j) <==> t.slot_hash(j) != NO_HASH by {
            }
            assert forall|j: int| 0 <= j < t.ctrl.capacity as int && t.ctrl.is_full_spec(j)
                implies t.ctrl.bytes[j] as u64 == t.slot_hash(j) >> 57 by {
            }
            assert forall|j: int, k: int| 0 <= j < k < t.ctrl.capacity as int
                && t.ctrl.is_full_spec(j) && t.ctrl.is_full_spec(k)
                implies t.slot_hash(j) != t.slot_hash(k) by {
            }
            assert(t.len_ as nat == seq_full_count(t.ctrl.bytes@, t.ctrl.capacity as nat));
            assert(t.hashes.len() == t.ctrl.capacity);
            assert(t.slot_model());
            assert forall|i: int| 0 <= i < t.ctrl.capacity as int
                implies !t.ctrl.is_full_spec(i) by {
                assert(t.ctrl.bytes[i] == crate::control_bytes::EMPTY);
            }
        }
        t
    }

    /// `hashes[slot]` readable from specification code.
    ///
    /// **Total by construction.**  An earlier revision carried
    /// `recommends slot < self.hashes@.len()`, which turned every mention in a
    /// `postcondition` into a "recommendation not met" note that had to be chased
    /// down separately -- the recommendation could not be discharged before
    /// `final(self).model()` was established, and `ensures` clauses are not
    /// available to each other while they are being proved.  Reading an
    /// out-of-range slot as `NO_HASH` is not a weakening: every use site in this
    /// port reads a slot under `0 <= i < ctrl.capacity`, where `slot_model` gives
    /// `hashes@.len() == ctrl.capacity`, so the two forms agree there.
    pub open spec fn slot_hash(&self, slot: int) -> u64 {
        if 0 <= slot < self.hashes@.len() {
            self.hashes[slot]
        } else {
            NO_HASH
        }
    }

    /// `hashes[slot]` readable from executable code; `slot_hash` is a
    /// specification function and cannot be called there.
    pub fn hash_at(&self, slot: usize) -> (r: u64)
        requires slot < self.hashes.len(),
        ensures r == self.slot_hash(slot as int)
    {
        self.hashes[slot]
    }

    /// The link every mutator maintains.
    ///
    /// * a slot is full exactly when its hash field is not `NO_HASH`, which is
    ///   why `NO_HASH` is refused as an input hash: a full slot never carries it
    ///   and a free slot always does;
    /// * a full slot's control byte is the `H2` tag of the key it holds, which
    ///   is the reference's own invariant and is what makes ControlBytes.C007
    ///   readable back out of any full slot (upstream's `Group::Match` depends on
    ///   exactly this);
    /// * no two full slots carry the same hash, which is what lets `erase` drop a
    ///   key and a scan stand in for an unproved probe.
    pub open spec fn slot_model(&self) -> bool {
        let cap = self.ctrl.capacity as int;
        &&& self.hashes.len() == self.ctrl.capacity
        // Written as a pair of implications rather than one `<==>`: the biconditional
        // form is logically identical but its automatically chosen trigger does not
        // instantiate against `ControlBytes::is_full_spec` / `RawTable::slot_hash`,
        // so `RawTable::new` cannot discharge it.  Verified in isolation -- see the
        // note in `raw_table.rs`'s history for the probe.
        &&& (forall|i: int| 0 <= i < cap
                ==> (self.ctrl.is_full_spec(i) ==> self.slot_hash(i) != NO_HASH)
                    && (!self.ctrl.is_full_spec(i) ==> self.slot_hash(i) == NO_HASH))
        // Stated over the `u8` tag rather than over `bytes[i] as u64`: the cast is
        // what makes the clause hard to instantiate and to compare against.  `#[trigger]`
        // on `bytes[i]` so that reading the tag back off a full slot fires.
        &&& (forall|i: int| 0 <= i < cap && self.ctrl.is_full_spec(i)
                ==> #[trigger] self.ctrl.bytes[i] == (self.slot_hash(i) >> 57) as u8)
        &&& (forall|i: int, j: int| 0 <= i < j < cap
                && self.ctrl.is_full_spec(i) && self.ctrl.is_full_spec(j)
                ==> self.slot_hash(i) != self.slot_hash(j))
    }

    /// Direct map-domain/slot relation: every live slot is indexed, and every
    /// map key names exactly one live slot with its current physical index.
    pub open spec fn live_map_model(&self) -> bool {
        let m = self.g@.m;
        let cap = self.ctrl.capacity as int;
        &&& forall|i: int| 0 <= i < cap && self.ctrl.is_full_spec(i)
            ==> m.dom().contains(self.slot_hash(i)) && m[self.slot_hash(i)] == i as usize
        &&& forall|h: u64| m.dom().contains(h)
            ==> exists|i: int| 0 <= i < cap && self.ctrl.is_full_spec(i)
                && self.slot_hash(i) == h && m[h] == i as usize
    }

    pub open spec fn model(&self) -> bool {
        &&& self.ctrl.well_formed()
        &&& self.slot_model()
        &&& self.live_map_model()
        // RawTable.C001's capacity shape: the slot count is `2^n - 1`.  This is
        // statable on the table's own `usize` capacity after all -- an earlier
        // revision recorded it as unstatable (`swisstable-verus-016`) because the
        // `u64 -> usize` narrowing cast was assumed opaque in both directions.  It
        // is opaque only *unbounded*; under `capacity <= 0x7FFF_FFFF`, which
        // `ControlBytes::well_formed` now carries and `ControlBytes::new` already
        // required, `lemma_narrow_roundtrip` closes the round trip.
        &&& self.ctrl.capacity as u64 == slots_for_bits_spec(self.capacity_bits)  // RawTable.C001
        &&& 5 <= self.capacity_bits <= 31
        // The counting contract: `len_` *is* the number of full control bytes.
        &&& self.len_ as nat == seq_full_count(self.ctrl.bytes@, self.ctrl.capacity as nat)
    }

    /// What is true of `self` in the window between `clear_dead()` and the end of
    /// `resize`, when the control bytes have been rewritten but the slot hashes have
    /// not.
    ///
    /// `model()` is deliberately **not** re-established here, because in this window
    /// it is false: `clear_dead` turns every full byte into a tombstone while
    /// `hashes` still holds that slot's key, so `slot_model`'s biconditional
    /// `is_full_spec(i) <==> slot_hash(i) != NO_HASH` does not hold.  This predicate
    /// says what does hold instead.  See `swisstable-verus-019`.
    ///
    /// `resize` no longer *uses* this predicate: it states the two facts it needs
    /// (`tombstones_are_the_old_full_slots`, plus the length and snapshot-identity
    /// invariants) directly, because the H2-tag and distinctness clauses here are
    /// about the pre-reclaim array and are needed once, not on every loop
    /// iteration.  The predicate is kept, corrected, as the recorded statement of
    /// what the reclaim window looks like.
    ///
    /// ## A third false invariant of the same class, fixed here (`swisstable-verus-019`)
    ///
    /// The first clause of this predicate read
    /// `is_full_spec(i) <==> before[i] <= 0x7F` -- "a slot is still full exactly when
    /// it was full before the reclaim" -- with a comment justifying it by
    /// "`clear_dead` never promotes a free byte".  That is **false**, and in the
    /// direction that matters: `clear_dead` writes `kDeleted` (`0xFE`) over every
    /// full byte, so after the reclaim *no* slot is full, while `before[i] <= 0x7F`
    /// holds for exactly the live ones.  The clause says `is_full <==> is_live`
    /// where it should say `is_dead <==> is_live`.  The transcript's
    /// `invariant not satisfied before loop` on this predicate is the symptom;
    /// the invariant was wrong, not unproved.  This is the same class as
    /// `swisstable-verus-019` (a `resize` invariant) and `swisstable-verus-020`
    /// (an `erase` comment): a stated predicate that is not a fact about the
    /// reference.  All three clauses that were phrased over `is_full_spec` in this
    /// window are now phrased over `is_dead_spec`.
    pub open spec fn reclaiming_model(
        &self,
        before: Seq<u8>,
        before_hashes: Seq<u64>,
    ) -> bool {
        let cap = self.ctrl.capacity as int;
        &&& self.ctrl.well_formed()
        &&& self.hashes@ == before_hashes
        &&& (self.hashes@.len() == cap)
        &&& 5 <= self.capacity_bits <= 31
        &&& self.ctrl.capacity as u64 == slots_for_bits_spec(self.capacity_bits)
        // a slot is *tombstoned* exactly when it was full before the reclaim, and
        // no slot is full any more -- `clear_dead` writes `kDeleted` over every
        // full byte and `kEmpty` over every byte that already had the MSB set
        &&& (forall|i: int| 0 <= i < cap ==> self.ctrl.is_dead_spec(i) <==> before[i] <= 0x7F)
        // and the key a tombstone still carries is a live one, not `NO_HASH`
        &&& (forall|i: int| 0 <= i < cap && self.ctrl.is_dead_spec(i)
                ==> before_hashes[i] != NO_HASH)
        // and its pre-reclaim control byte was its H2 tag, which is what lets the
        // move read the tag back off the source slot
        &&& (forall|i: int| 0 <= i < cap && self.ctrl.is_dead_spec(i)
                ==> before[i] as u64 == before_hashes[i] >> 57)
        // two live slots never share a key
        &&& (forall|i: int, j: int| 0 <= i < j < cap
                && self.ctrl.is_dead_spec(i) && self.ctrl.is_dead_spec(j)
                ==> before_hashes[i] != before_hashes[j])
    }

    /// RawTable::len.  RawTable.C002: the live count never exceeds the number of
    /// full control bytes -- here they are equal, by `model`.
    pub fn len(&self) -> (r: usize)
        requires self.model(),
        ensures
            r == self.len_,
            r as nat == seq_full_count(self.ctrl.bytes@, self.ctrl.capacity as nat), // RawTable.C002
    {
        self.len_
    }

    /// RawTable::capacity -- RawTable.C001: the capacity is `2^n - 1` and the
    /// sentinel sits at index `capacity`.
    pub fn capacity(&self) -> (r: usize)
        requires self.model(),
        ensures
            r == self.ctrl.capacity,
            5 <= self.capacity_bits <= 31,                                // RawTable.C001
            self.ctrl.bytes@.len() > r,
            self.ctrl.bytes[r as int] == SENTINEL,
    {
        self.ctrl.capacity
    }

    /// RawTable::is_full -- no slot is left to insert into.
    pub fn is_full(&self) -> (r: bool)
        requires self.model(),
        ensures r == !self.has_free_slot()
    {
        // `has_free_slot` is the existential form, so the counting form is
        // discharged here by the counting lemma rather than at each use site.
        let n = self.count_empty_or_deleted();
        proof {
            assert(n as nat == seq_free_count(self.ctrl.bytes@, self.ctrl.capacity as nat));
        }
        if n == 0 {
            proof {
                lemma_zero_free_gives_not_has_free(&self.ctrl);
                assert(!self.has_free_slot());
            }
            true
        } else {
            proof {
                assert(seq_free_count(self.ctrl.bytes@, self.ctrl.capacity as nat) > 0);
                lemma_positive_free_gives_has_free(&self.ctrl, self.ctrl.capacity as nat);
                assert(self.has_free_slot());
            }
            false
        }
    }

    /// RawTable.C003's precondition, as a specification predicate: at least one
    /// slot is empty or deleted.
    ///
    /// Stated as the **existential**, not as `seq_free_count > 0`.  The two are the
    /// same fact, but the existential is the one a *scan* can consume: it hands
    /// `claim_first_free` a witness slot directly, whereas the counting form needs
    /// `lemma_free_count_positive` and `lemma_free_count_zero` to be turned back into
    /// a witness at every call site.  `model()` keeps the counting form
    /// (`len_ == seq_full_count`) as the counting contract, so both are present.
    ///
    /// The index is `int`, not `usize`; see the note on
    /// `control_bytes::is_empty_or_deleted_in` for why that is not cosmetic.
    pub open spec fn has_free_slot(&self) -> bool {
        exists|i: int| 0 <= i < self.ctrl.capacity as int
            && crate::control_bytes::is_empty_or_deleted_in(self.ctrl.bytes@, i)
    }

    pub fn count_full_ctrl(&self) -> (r: usize)
        requires self.ctrl.well_formed(),
        ensures
            r as nat == seq_full_count(self.ctrl.bytes@, self.ctrl.capacity as nat),
            r <= self.ctrl.capacity,
    {
        let mut n: usize = 0;
        let mut i: usize = 0;
        while i < self.ctrl.capacity
            invariant
                i <= self.ctrl.capacity,
                n <= i,
                self.ctrl.well_formed(),
                n as nat == seq_full_count(self.ctrl.bytes@, i as nat),
            decreases self.ctrl.capacity - i,
        {
            if self.ctrl.bytes[i] <= 0x7F {
                n = n + 1;
            }
            i = i + 1;
        }
        n
    }

    /// The number of empty-or-deleted slots, i.e. the reusable ones.
    pub fn count_empty_or_deleted(&self) -> (r: usize)
        requires self.ctrl.well_formed(),
        ensures r as nat == seq_free_count(self.ctrl.bytes@, self.ctrl.capacity as nat)
    {
        let mut n: usize = 0;
        let mut i: usize = 0;
        while i < self.ctrl.capacity
            invariant
                i <= self.ctrl.capacity,
                n <= i,
                self.ctrl.well_formed(),
                n as nat == seq_free_count(self.ctrl.bytes@, i as nat),
            decreases self.ctrl.capacity - i,
        {
            let b = self.ctrl.bytes[i];
            if b == EMPTY || b == DELETED {
                n = n + 1;
            }
            i = i + 1;
        }
        n
    }

    /// RawTable.C007 / SwissTable.C001: the set of stored hashes, derived from
    /// the full slots.  Kept, because `contains` and `has_free_slot` are stated
    /// through it and the membership step is provable (`lemma_stored_in`); what is
    /// *not* stated anywhere is a two-directional equality over it.
    pub open spec fn stored_hashes(&self) -> Set<u64> {
        Set::new(|k: u64| exists|i: int|
            0 <= i < self.ctrl.capacity
                && self.ctrl.is_full_spec(i)
                && self.hashes[i] == k)
    }

    /// The same model with the membership predicate named.  Every extensionality proof
    /// over `stored_hashes()` needs to see through `Set::new`, which is closed in vstd;
    /// naming the predicate gives the unfolding a single stable term to fire on
    /// (`swisstable-verus-017`).
    pub open spec fn stored_at(&self, i: int, k: u64) -> bool {
        self.ctrl.is_full_spec(i) && self.hashes[i] == k
    }

    pub open spec fn stored_in(&self, k: u64) -> bool {
        exists|i: int| #[trigger] self.stored_at(i, k)
            && 0 <= i < self.ctrl.capacity
    }

    /// Read-only access to the control array.
    pub fn ctrl_ref(&self) -> &ControlBytes
        requires self.model(),
        ensures self.ctrl.well_formed()
    {
        &self.ctrl
    }

    /// The number of groups a probe run visits before it must have terminated.
    pub open spec fn num_groups(&self) -> int {
        self.ctrl.capacity as int / (GROUP_WIDTH as int) + 1
    }

    /// `num_groups` as an executable query; the postcondition is what lets loop
    /// invariants and `decreases` clauses use the specification form.
    pub fn num_groups_exec(&self) -> (r: usize)
        requires self.ctrl.well_formed(),
        ensures (r as int) == self.num_groups(), r >= 1, r * GROUP_WIDTH >= self.ctrl.capacity
    {
        self.ctrl.capacity / GROUP_WIDTH + 1
    }

    /// The probe sequence for this table's capacity.
    pub fn new_seq(&self) -> (s: ProbeSeq)
        requires
            self.model(),
            4 <= self.capacity_bits,
            self.capacity_bits <= 31,
        ensures
            s.well_formed(),
            s.capacity_bits == self.capacity_bits,
            s.capacity_mask == self.ctrl.capacity as u64,
            s.index_ == 0,
            s.offset_ == 0,
    {
        ProbeSeq::new(self.capacity_bits)
    }

    // ---- lookup ------------------------------------------------------------

    /// RawTable::find -- walk the probe sequence, checking the matching-tag slots
    /// of every group and stopping at the first group that has a reusable slot,
    /// exactly as `find_first_non_full` does upstream.
    ///
    /// RawTable.C006, in the re-scoped per-slot form: a slot this reports is full,
    /// holds `hash`, and its control byte is `H2(hash)`; and a `None` means **no**
    /// full slot holds `hash`.
    ///
    /// ## One deviation from the reference, made for the proof
    ///
    /// The reference relies on the probe sequence visiting every slot of a
    /// `2^k - 1` table exactly once, which is what makes "ran out of groups" mean
    /// "not there".  That property is the bijection `j |-> j(j+1)/2 mod 2^(k-4)`,
    /// and it needs a bit-level induction over the quadratic-probing offset that
    /// this port does not discharge.  So the probe run is bounded by the group
    /// count -- which terminates unconditionally -- and is followed by a full scan
    /// of the slot array.  `find` is therefore *complete* (`None` provably means
    /// absent) at the cost of its worst case; the reference's expected O(1) is
    /// not what is proved.  Recorded as `swisstable-verus-004`.
    pub fn find(&mut self, hash: u64) -> (r: Option<usize>)
        requires
            self.model(),
            4 <= self.capacity_bits,
            self.capacity_bits <= 31,
            hash != NO_HASH,
        ensures
            *final(self) == *old(self),
            match r {
                None => forall|i: int| 0 <= i < final(self).ctrl.capacity as int
                        ==> !(final(self).ctrl.is_full_spec(i)
                            && final(self).slot_hash(i) == hash),
                Some(slot) => {
                    &&& slot < final(self).ctrl.capacity
                    &&& final(self).ctrl.is_full_spec(slot as int)
                    &&& final(self).slot_hash(slot as int) == hash
                    &&& final(self).ctrl.bytes[slot as int] as u64 == hash >> 57
                },
            },
    {
        let mut mix = HashMix::new();
        mix.from_hash(hash);
        // `new_seq` and `from_capacity_and_h1` are read-only with respect to `self`;
        // their postconditions are hoisted into the loop invariant's first facts so
        // the invariant can be established before the loop rather than at its head.
        let mut seq = self.new_seq();
        seq.from_capacity_and_h1(mix.h1());
        proof {
            assert(seq.well_formed());
            assert(seq.capacity_bits == self.capacity_bits);
            assert(seq.capacity_mask == self.ctrl.capacity as u64);
            assert(mix.supplied);
        }
        let mut g = GroupProbe::new();
        let mut steps: usize = 0;
        while steps < self.num_groups_exec()
            invariant
                steps <= self.num_groups(),
                self.model(),
                4 <= self.capacity_bits,
                self.capacity_bits <= 31,
                mix.supplied,
                seq.well_formed(),
                seq.capacity_bits == self.capacity_bits,
                seq.capacity_mask == self.ctrl.capacity as u64,
            decreases self.num_groups() - steps,
        {
            steps = steps + 1;
            let base = seq.offset();
            proof {
                // `ProbeSeq::offset` now gives the exact value, and the mask *is*
                // the table's capacity, so the group window is inside the array.
                lemma_narrow_le(base, self.ctrl.capacity);
            }
            assert(base <= self.ctrl.capacity);
            assert(base + GROUP_WIDTH <= self.ctrl.bytes.len());
            g.load(&self.ctrl, base);
            let free = g.match_empty_or_deleted();
            let h2 = mix.h2();
            let full = g.match_full(h2);
            // The loaded window, as ghost data.  The scan below is stated over
            // `self.ctrl.bytes@` (which is what `g.window@` is tied to by
            // `GroupProbe::load`), and a ghost snapshot of the mask answers keeps the
            // quantifier's terms identical on both sides across the loop boundary.
            let ghost win = g.window@;
            proof {
                assert forall|j: int| 0 <= j < 16
                    implies bit_set_at(full, j)
                        == (g.window@[j] <= 0x7F && g.window@[j] == h2) by {
                }
                assert forall|j: int| 0 <= j < 16
                    implies bit_set_at(full, j)
                        <==> (g.window@[j] <= 0x7F && g.window@[j] == h2) by {
                }
            }
            let mut i: usize = 0;
            while i < GROUP_WIDTH
                invariant
                    i <= GROUP_WIDTH,
                    self.model(),
                    base <= self.ctrl.capacity,
                    base + GROUP_WIDTH <= self.ctrl.bytes.len(),
                    // the loaded window is the control array's window at `base`, so
                    // `GroupProbe`'s answers can be read back off the control bytes
                    g.window@ == self.ctrl.bytes@.subrange(base as int,
                        (base + GROUP_WIDTH) as int),
                    g.window@ == win,
                    g.window@.len() == GROUP_WIDTH,
                    // `match_full`'s answer, over the window: Verus drops the
                    // postcondition at the loop boundary, so it is restated here.
                    forall|j: int| 0 <= j < 16
                        ==> (bit_set_at(full, j)
                            ==> (g.window@[j] <= 0x7F && g.window@[j] == h2)),
                    // the inner scan's own frame: `base + i` is bounded before it is
                    // used both as a `Vec` index and as an offset into the table
                    base + i <= base + GROUP_WIDTH,
                    base + i <= self.ctrl.capacity + GROUP_WIDTH,
                decreases GROUP_WIDTH - i,
            {
                if bit_set(full, i) && base + i < self.ctrl.capacity {
                    let slot = base + i;
                    proof {
                        // The mask's per-index answer, established before the loop.
                        assert(bit_set_at(full, i as int));
                        assert(win[i as int] <= 0x7F);
                        assert(win[i as int] == h2);
                        assert(win[i as int] == g.window@[i as int]);
                        assert(g.window@[i as int] == self.ctrl.bytes[slot as int]);
                        assert(self.ctrl.is_full_spec(slot as int));
                    }
                    if self.hash_at(slot) == hash {
                        // `slot_model`'s tag clause reads the H2 byte back off a full
                        // slot, so the two agree without this site re-deriving it.
                        // `lemma_h2_roundtrip` is what makes the `>>` and the `u8`
                        // truncation step through in integer mode.
                        proof {
                            lemma_shr57(hash);
                            lemma_h2_roundtrip(hash);
                            assert forall|j: int| 0 <= j < self.ctrl.capacity as int
                                && self.ctrl.is_full_spec(j)
                                implies #[trigger] self.ctrl.bytes[j]
                                    == (self.slot_hash(j) >> 57) as u8 by {
                            }
                        }
                        assert(self.slot_hash(slot as int) == hash);
                        assert(self.ctrl.bytes[slot as int] == (hash >> 57) as u8);
                        assert(self.ctrl.bytes[slot as int] as u64 == hash >> 57);
                        assert(0 <= slot && slot < self.ctrl.capacity);
                        return Some(slot);
                    }
                }
                i = i + 1;
            }
            if free != 0 {
                break;
            }
            seq.advance();
        }
        // The fallback scan that makes `find` complete; see the note above.
        let cap = self.ctrl.capacity;
        let mut i: usize = 0;
        while i < cap
            invariant
                i <= cap,
                cap == self.ctrl.capacity,
                cap == self.hashes.len(),
                self.model(),
                forall|j: int| 0 <= j < i
                    ==> !(self.ctrl.is_full_spec(j) && self.slot_hash(j) == hash),
            decreases cap - i,
        {
            if self.ctrl.is_full(i) && self.hash_at(i) == hash {
                proof { lemma_shr57(hash); lemma_h2_roundtrip(hash); }
                assert(self.slot_hash(i as int) == hash);
                assert(self.ctrl.bytes[i as int] as u64 == hash >> 57);
                assert(0 <= i && i < self.ctrl.capacity);
                return Some(i);
            }
            i = i + 1;
        }
        proof {
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int
                ==> !(self.ctrl.is_full_spec(j) && self.slot_hash(j) == hash) by {
            }
        }
        None
    }

    // ---- insertion ---------------------------------------------------------

    /// RawTable::insert -- upstream's find-or-open.
    ///
    /// RawTable.C003 is the precondition (at least one empty-or-deleted slot).
    /// RawTable.C004 is the **counting** contract: on `true` the element count
    /// rose by exactly one, on `false` it did not move.  The rest is per-slot:
    /// the returned slot is full, holds `hash` and carries `H2(hash)`
    /// (ControlBytes.C007), and every *other* slot is untouched.
    pub fn insert(&mut self, hash: u64) -> (r: (usize, bool))
        requires
            self.model(),
            hash != NO_HASH,
            self.has_free_slot(),                                           // RawTable.C003
            self.len_ < self.ctrl.capacity,
        ensures
            final(self).model(),
            // ---- the shape of the table is untouched: `insert` never resizes, so
            // the container's `values.len() == capacity` side condition survives it
            final(self).ctrl.capacity == old(self).ctrl.capacity,
            final(self).capacity_bits == old(self).capacity_bits,
            // ---- per-slot
            r.0 < final(self).ctrl.capacity,
            final(self).ctrl.is_full_spec(r.0 as int),
            final(self).slot_hash(r.0 as int) == hash,
            final(self).ctrl.bytes[r.0 as int] as u64 == hash >> 57,         // ControlBytes.C007
            r.1 ==> old(self).ctrl.is_empty_or_deleted_spec(r.0 as int),
            r.1 ==> final(self).g@.m == old(self).g@.m.insert(hash, r.0),
            !r.1 ==> final(self).g@.m == old(self).g@.m,
            // ---- counting
            r.1 ==> final(self).len_ == old(self).len_ + 1,                 // RawTable.C004
            !r.1 ==> final(self).len_ == old(self).len_,                    // RawTable.C004
            // ---- per-slot: a `true` return means no full slot held `hash` before,
            // and a `false` one means some full slot did.  This is the per-slot form
            // of the `true`/`false` distinction `SwissTable.C002` needs, and it is
            // what `find`'s completeness gives.
            r.1 ==> forall|j: int| 0 <= j < old(self).ctrl.capacity as int
                    ==> !(old(self).ctrl.is_full_spec(j)
                        && old(self).slot_hash(j) == hash),
            !r.1 ==> exists|j: int| 0 <= j < old(self).ctrl.capacity as int
                    && old(self).ctrl.is_full_spec(j)
                    && old(self).slot_hash(j) == hash,
            // ---- per-slot frame
            forall|j: int| 0 <= j < final(self).ctrl.capacity as int
                    && j != r.0 as int
                ==> final(self).ctrl.bytes[j] == old(self).ctrl.bytes[j]
                    && final(self).hashes[j] == old(self).hashes[j],
    {
        let mut mix = HashMix::new();
        mix.from_hash(hash);
        match self.find(hash) {
            Some(slot) => {
                return (slot, false);
            }
            None => { }
        }
        let (slot, claimed) = claim_first_free(&self.ctrl, mix.h1());
        proof {
            // `has_free_slot` and `claim_first_free`'s precondition are literally the
            // same existential now, so the `exists` carries over without a bridge.
            assert(self.ctrl.well_formed());
            assert(self.has_free_slot());
            assert(claimed);
            assert(exists|j: int| 0 <= j < self.ctrl.capacity as int
                && crate::control_bytes::is_empty_or_deleted_in(self.ctrl.bytes@, j));
        }
        // The pre-write facts the three writes' postconditions need.  `&mut self`
        // postconditions can only see `old(self)`, and the per-slot frame is a
        // statement about which slots moved; both are captured here, before the
        // first write.
        let ghost before_bytes = self.ctrl.bytes@;
        let ghost before_hashes = self.hashes@;
        proof {
            // The pre-state `slot_model`, restated over the two ghost snapshots; see
            // `lemma_slot_model_snapshot` for why the receiver's own terms do not
            // survive the writes and why the bridge has to be taken here, while
            // `self` still is the pre-state.
            lemma_slot_model_snapshot(self, before_bytes, before_hashes);
        }
        self.ctrl.set_full(slot, mix.h2());
        self.hashes[slot] = hash;
        self.len_ = self.len_ + 1;
        proof { self.g.borrow_mut().m.tracked_insert(hash, slot); }
        proof {
            assert(self.slot_hash(slot as int) == hash);
            assert(self.ctrl.bytes[slot as int] as u64 == hash >> 57);
            assert(self.ctrl.is_full_spec(slot as int));
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int && j != slot as int
                implies self.ctrl.is_full_spec(j) <==> before_bytes[j] <= 0x7F by {
            }
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int && j != slot as int
                implies self.slot_hash(j) == before_hashes[j] by {
            }
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int && j != slot as int
                implies !(self.ctrl.is_full_spec(j) && self.slot_hash(j) == hash) by {
            }
            assert(self.hashes@.len() == self.ctrl.capacity);
            assert(self.ctrl.well_formed());
        }
        proof { lemma_full_count_slot(self.ctrl.bytes@, before_bytes, self.ctrl.capacity as nat, slot as int); }
        (slot, true)
    }

    // ---- erase -----------------------------------------------------------

    /// RawTable::erase -- upstream `erase_meta_only`: drop the element in `slot`
    /// and pick the control byte it leaves behind.
    ///
    /// The choice is upstream's, verbatim: `EraseMetaOnlyLarge` (raw_hash_set.cc
    /// L868-L883) writes `kEmpty` when `WasNeverFull(c, index)` holds (L708-L724)
    /// and `kDeleted` otherwise, and this port does the same by calling
    /// `ControlBytes::was_never_full`.
    ///
    /// `swisstable-verus-021` earlier recorded this port as always writing
    /// `kDeleted`, and justified that by saying `WasNeverFull` reads a
    /// `growth_info()` field the port has no field for.  **That was wrong for the
    /// pinned checkout.**  `WasNeverFull` is a pure function of the control bytes
    /// -- two `Group(...).MaskEmpty()` windows -- and the `growth_info()` calls sit
    /// on the two lines *after* the branch decision (L876/L882) and only feed
    /// growth-left accounting.  The operator's 2026-10-02 ruling directed that
    /// upstream be matched, and it is.
    ///
    /// The small-table arm (`EraseMetaOnlySmall`, raw_hash_set.cc L856-L866, which
    /// writes nothing because the whole table is one probing group) is not a
    /// separate path here: `was_never_full` reproduces its `is_single_group`
    /// short-circuit, and under this port's `capacity_bits >= 5` that arm is dead,
    /// since the capacity is then at least 31 > 16.  `len_` is decremented once,
    /// which is what both upstream arms do.
    ///
    /// RawTable.C005, in the re-scoped per-slot and counting form: the element
    /// count fell by exactly one, the erased slot reads as empty-or-deleted and
    /// carries no key, and every other slot is untouched.
    ///
    /// The control-byte write is guarded on `is_full(slot)`, and the caller must NOT
    /// pre-write the tombstone: this function's `model()` precondition requires the
    /// erased slot to still be full while its key is still in `hashes`.  An earlier
    /// revision of the container's `erase` pre-wrote it, which falsified `slot_model`
    /// -- see `swisstable-verus-020`.
    pub fn erase(&mut self, slot: usize)
        requires
            self.model(),
            self.len_ > 0,
            slot < self.ctrl.capacity,
            self.ctrl.is_full_spec(slot as int),          // upstream: no dangling iterator
        ensures
            final(self).model(),
            // ---- the shape of the table is untouched, so a container's
            // `values.len() == capacity` side condition survives an erase
            final(self).ctrl.capacity == old(self).ctrl.capacity,
            final(self).capacity_bits == old(self).capacity_bits,
            // ---- counting
            final(self).len_ == old(self).len_ - 1,                        // RawTable.C005
            // ---- per-slot
            final(self).ctrl.is_empty_or_deleted_spec(slot as int),        // RawTable.C005
            final(self).slot_hash(slot as int) == NO_HASH,
            final(self).g@.m == old(self).g@.m.remove(old(self).slot_hash(slot as int)),
            // ---- upstream's erase rule, raw_hash_set.cc L875-L883
            old(self).ctrl.was_never_full_spec(slot as int)
                ==> final(self).ctrl.is_empty_spec(slot as int)
                    && final(self).live_map_model(),
            !old(self).ctrl.was_never_full_spec(slot as int)
                ==> final(self).ctrl.is_dead_spec(slot as int)
                    && final(self).live_map_model(),
            // ---- per-slot frame
            forall|j: int| 0 <= j < final(self).ctrl.capacity as int
                    && j != slot as int
                ==> #[trigger] final(self).hashes[j] == old(self).hashes[j]
                    && final(self).ctrl.bytes[j] == old(self).ctrl.bytes[j],
            // ---- and the consequence the container needs: the erased key is gone
            // from every slot, which is `slot_model`'s distinctness clause plus the
            // frame above.  Stated here so the container does not have to re-derive it
            // across the `old(self)` boundary.
            forall|j: int| 0 <= j < final(self).ctrl.capacity as int
                ==> !(final(self).ctrl.is_full_spec(j)
                    && final(self).slot_hash(j) == old(self).slot_hash(slot as int)),
    {
        let erased_hash = self.hash_at(slot);
        let was_nf = self.ctrl.was_never_full(slot);
        let ghost nf_spec = self.ctrl.was_never_full_spec(slot as int);
        assert(was_nf == nf_spec);
        let ghost before_bytes = self.ctrl.bytes@;
        let ghost before_hashes = self.hashes@;
        proof {
            // The pre-state `slot_model`, restated over the two ghost snapshots; see
            // `lemma_slot_model_snapshot` for why the receiver's own terms do not
            // survive the writes and why the bridge has to be taken here, while
            // `self` still is the pre-state.
            lemma_slot_model_snapshot(self, before_bytes, before_hashes);
        }
        if was_nf {
            self.ctrl.set_empty(slot);
        } else {
            self.ctrl.set_dead(slot);
        }
        self.hashes[slot] = NO_HASH;
        self.len_ = self.len_ - 1;
        proof { let tracked _old_slot = self.g.borrow_mut().m.tracked_remove(erased_hash); }
        proof {
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int && j != slot as int
                implies self.ctrl.is_full_spec(j) <==> before_bytes[j] <= 0x7F by {
            }
            assert forall|j: int| 0 <= j < self.ctrl.capacity as int && j != slot as int
                implies self.slot_hash(j) == before_hashes[j] by {
            }
            assert(self.hashes@.len() == self.ctrl.capacity);
            assert(self.ctrl.well_formed());
        }
        proof { lemma_full_count_slot(self.ctrl.bytes@, before_bytes, self.ctrl.capacity as nat, slot as int); }
    }

    // ---- rehash ------------------------------------------------------------

    /// RawTable::resize -- upstream `DropDeletesWithoutResizeAndPrepareInsert`
    /// (raw_hash_set.cc L593-L700) followed by the transfer into the new capacity
    /// that `ResizeAllocatedTableWithSeedChange` (raw_hash_set.cc L2104-L2144)
    /// performs.
    ///
    /// Step 1 is the `ControlBytes::clear_dead` edge
    /// (`BR-CONTROLBYTES-CLEARDEAD-001`): every full byte becomes a tombstone and
    /// every byte that already had the MSB set becomes empty.  Afterwards the live
    /// elements are *exactly* the tombstoned slots, which is what makes step 2 a
    /// straight move of every tombstone into a table of the new capacity.
    ///
    /// Step 2 walks the tombstoned slots once and re-inserts each key with the
    /// ordinary find-or-open.  The reference instead moves the slots *in place*
    /// with a swap chain, because its control bytes and its slots are one
    /// allocation; this port's slots are a `Vec<u64>` beside the control bytes
    /// (`swisstable-verus-001`), so the transfer follows the reference's *other*
    /// resize path, `FindNewPositionsAndTransferSlots`, which does move slots into
    /// a fresh table.  The observable result is the same -- the keys live again,
    /// at positions the probe sequence chooses -- and the record of where each key
    /// went is a ghost `Seq` pair, `dest`/`owner`, because nothing in the port's
    /// representation keeps it otherwise.
    ///
    /// RawTable.C007, in the re-scoped form: **counting** -- the element count is
    /// unchanged -- plus the **per-slot** survival statement, in both directions
    /// and one slot at a time:
    ///
    /// * every slot that was full still has its key in some full slot, and
    /// * every full slot's key was in some slot that was full.
    ///
    /// That is the per-slot form of "every live element survives the rehash", and
    /// it replaces `stored_hashes() =~= old(self).stored_hashes()`, which is out of
    /// scope by the operator's ruling (`swisstable-verus-023`).  Note what is *not*
    /// claimed: slot indices are *not* preserved, and a fresh `ControlBytes` means
    /// the whole array is rewritten -- so a frame condition in the
    /// `insert`/`erase` sense does not exist for `resize`, and the two survival
    /// directions are its contract instead.
    ///
    /// RawTable.C001 keeps holding because the new table is built by
    /// `RawTable::new`, which builds it through `ControlBytes::new`.
    ///
    /// ## The previous shape of this loop, and why it went (`swisstable-verus-031`)
    ///
    /// An earlier revision rebuilt the control bytes and the slot hashes by hand
    /// and carried the two survival directions as loop invariants of the form
    /// "every full slot of the new array holds a key that came from a tombstone
    /// this loop has already walked past", i.e. `exists`-inside-`forall`.  Five
    /// clauses of that shape, plus a distinctness clause and an H2-tag clause,
    /// were enough for Verus to report `Resource limit (rlimit) exceeded` on the
    /// loop itself, and nine of its invariants did not close.  Recording the
    /// placement in two ghost `Seq`s indexed by the *source* slot (`dest`) and the
    /// *destination* slot (`owner`) turns both directions into pointwise facts
    /// about a single index, and the loop closes.  Nothing about the port's
    /// behaviour changed; what changed is the shape of the statement.
    pub fn resize(&mut self, new_capacity_bits: u32)
        requires
            self.model(),
            4 <= self.capacity_bits,
            self.capacity_bits <= 31,
            5 <= new_capacity_bits,
            new_capacity_bits <= 31,
            // Every live element must fit in the new capacity.  Upstream never has
            // to say this -- `ResizeAllocatedTableWithSeedChange` is only ever
            // reached after `NormalizeCapacity` has sized the table for the live
            // elements -- but this port takes the target capacity as a parameter,
            // so the fact has to be a precondition rather than an implicit promise.
            // Without it the re-insert loop below can run out of slots, which is
            // exactly the overflow the reference's policy step rules out.
            self.len_ as nat <= slots_for_bits_spec(new_capacity_bits) as nat,
        ensures
            final(self).model(),
            // ---- counting
            final(self).len_ == old(self).len_,                              // RawTable.C007
            // ---- per-slot survival, both directions
            forall|i: int| 0 <= i < old(self).ctrl.capacity as int
                    && old(self).ctrl.is_full_spec(i)
                ==> exists|a: int| 0 <= a < final(self).ctrl.capacity as int
                    && final(self).ctrl.is_full_spec(a)
                    && final(self).slot_hash(a) == old(self).slot_hash(i),
            forall|a: int| 0 <= a < final(self).ctrl.capacity as int
                    && final(self).ctrl.is_full_spec(a)
                ==> exists|i: int| 0 <= i < old(self).ctrl.capacity as int
                    && old(self).ctrl.is_full_spec(i)
                    && old(self).slot_hash(i) == final(self).slot_hash(a),
            final(self).capacity_bits == new_capacity_bits,
            final(self).ctrl.capacity as u64 == slots_for_bits_spec(new_capacity_bits),
            final(self).ctrl.bytes[final(self).ctrl.capacity as int] == SENTINEL,
    {
        proof {
            lemma_pow2_range(new_capacity_bits);
            lemma_slots_roundtrip(new_capacity_bits);
        }
        let new_capacity = slots_for_bits(new_capacity_bits) as usize;
        proof { lemma_narrow_roundtrip(slots_for_bits_spec(new_capacity_bits)); }
        assert(new_capacity as u64 == slots_for_bits_spec(new_capacity_bits));

        let old_cap: usize = self.ctrl.capacity;
        let ghost old_cap_i = old_cap as int;
        let ghost old_cap_nat = old_cap as nat;
        let ghost before = self.ctrl.bytes@;
        let ghost before_hashes = self.hashes@;
        let ghost old_len = self.len_;
        proof {
            assert(old(self).ctrl.capacity == old_cap);
            assert(old(self).ctrl.bytes@ == before);
            assert(old(self).hashes@ == before_hashes);
            assert(old(self).len_ == old_len);
        }

        // The pre-state `slot_model`, restated over the two ghost snapshots, taken
        // while `self` still *is* the pre-state.  See
        // `verif/lemmas.rs::lemma_slot_model_snapshot` for why this has to happen
        // here rather than being read off `old(self)` later.
        proof {
            lemma_slot_model_snapshot(self, before, before_hashes);
        }

        // Step 1: reclaim.  Full -> kDeleted, kDeleted/kEmpty -> kEmpty.  This is
        // the `ControlBytes::clear_dead` edge, `BR-CONTROLBYTES-CLEARDEAD-001`.
        self.ctrl.clear_dead();

        proof {
            // `clear_dead`'s last postcondition is over the receiver; the loop
            // below needs it over the snapshot, because `before` is the term that
            // survives to the postconditions.  Both directions at once, so the
            // `iff` fires on either side.
            assert forall|i: int| 0 <= i < old_cap_i implies
                #[trigger] self.ctrl.is_dead_spec(i) <==> (#[trigger] before[i] <= 0x7F) by {
            }
            // ... which transfers the key facts of `slot_model` onto the tombstones.
            assert forall|i: int| 0 <= i < old_cap_i && self.ctrl.is_dead_spec(i)
                implies #[trigger] before_hashes[i] != NO_HASH
                    && #[trigger] before_hashes[i] == self.hashes@[i] by {
            }
            // Two live elements never share a key; this is what makes every
            // re-insert below a *new* element rather than a repeat.
            assert forall|j: int| 0 <= j < old_cap_i implies
                forall|i: int| 0 <= i < j
                    ==> self.ctrl.is_dead_spec(i) && self.ctrl.is_dead_spec(j)
                        ==> #[trigger] before_hashes[j] != before_hashes[i] by {
            }
            assert forall|i: int, j: int| 0 <= i < j < old_cap_i
                && self.ctrl.is_dead_spec(i) && self.ctrl.is_dead_spec(j)
                implies #[trigger] before_hashes[i] != #[trigger] before_hashes[j] by {
            }
        }

        // Step 2: move every live element into a table of the new capacity.
        //
        // The reference runs this in place with a swap chain, which needs the
        // control array and the slot array to be a single allocation.  This port's
        // slots are a `Vec<u64>` beside the control bytes, so the transfer is done
        // the way the reference's *other* resize path does it
        // (`FindNewPositionsAndTransferSlots`): walk the source once and place each
        // live element with the ordinary find-or-open, which is what
        // `insert` already proves.  The split allocation is what that costs, and the
        // two upstream constructs it could not carry over -- raw slots (chainlink #35)
        // and SIMD groups (#36) -- are separate entries in PORT-GAPS.md.
        //
        // The two ghost sequences are the placement record.  `dest` is indexed by
        // the *source* slot and `owner` by the *destination* slot, so both
        // survival directions are pointwise facts about one index rather than
        // existential statements -- which is the whole difference between this
        // loop verifying and the previous one, whose `exists`-inside-`forall`
        // invariants hit the solver's resource limit (see `swisstable-verus-031`).
        let mut t = RawTable::new(new_capacity_bits);
        assert(t.ctrl.capacity == new_capacity);
        let ghost dest: Seq<int> = Seq::new(old_cap_nat, |i: int| -1);
        let ghost owner: Seq<int> = Seq::new(new_capacity as nat, |i: int| -1);
        let mut x: usize = 0;
        while x < old_cap
            invariant
                x <= old_cap,
                old_cap == self.ctrl.capacity,
                old_cap_i == old_cap as int,
                old_cap_nat == old_cap as nat,
                old(self).ctrl.capacity == old_cap,
                old(self).ctrl.bytes@ == before,
                old(self).hashes@ == before_hashes,
                old(self).len_ == old_len,
                old_cap_nat <= before.len(),
                self.hashes@ == before_hashes,
                self.hashes@.len() == old_cap_i,
                self.hashes.len() == old_cap,
                before.len() == old_cap_i + 1 + PAD_BYTES as int,
                before_hashes.len() == old_cap_i,
                self.ctrl.well_formed(),
                self.tombstones_are_the_old_full_slots(before),
                forall|i: int| 0 <= i < old_cap_i && self.ctrl.is_dead_spec(i)
                    ==> #[trigger] before_hashes[i] != NO_HASH,
                forall|i: int, j: int| 0 <= i < j < old_cap_i
                    && self.ctrl.is_dead_spec(i) && self.ctrl.is_dead_spec(j)
                    ==> #[trigger] before_hashes[i] != #[trigger] before_hashes[j],
                // the window predicate: shape, snapshot identity, and dead-iff-full
                t.model(),
                t.capacity_bits == new_capacity_bits,
                t.ctrl.capacity == new_capacity,
                t.hashes@.len() == new_capacity as int,
                // ---- counting: one live element placed per tombstone walked past
                (t.len_ as nat) == seq_full_count(before, x as nat),
                (old_len as nat) == seq_full_count(before, old_cap_nat),
                old_len <= new_capacity,
                // ---- the placement record, both indices
                dest.len() == old_cap_nat,
                owner.len() == new_capacity as nat,
                // every tombstone walked past has been placed, and where
                forall|i: int| 0 <= i < x as int && #[trigger] self.ctrl.is_dead_spec(i)
                    ==> #[trigger] dest[i] >= 0,
                forall|i: int| 0 <= i < old_cap_i && #[trigger] dest[i] >= 0
                    ==> dest[i] < t.ctrl.capacity as int
                        && t.ctrl.is_full_spec(dest[i])
                        && t.slot_hash(dest[i]) == before_hashes[i],
                // and every full destination slot names the tombstone it came from
                forall|a: int| 0 <= a < t.ctrl.capacity as int && t.ctrl.is_full_spec(a)
                    ==> 0 <= #[trigger] owner[a] < x as int
                        && self.ctrl.is_dead_spec(owner[a])
                        && t.slot_hash(a) == before_hashes[owner[a]],
            decreases old_cap - x,
        {
            proof {
                assert(x < old_cap);
                assert(0 <= (x as int) && (x as int) < (old_cap_nat as int));
                assert((x as nat) <= before.len());
                assert((old_cap_nat as int) <= before.len());
                assert(old_cap_nat == old_cap as nat);
            }
            if self.ctrl.is_dead(x) {
                assert(0 <= (x as int) && (x as int) < old_cap_i);
                assert(self.ctrl.is_dead_spec(x as int));
                assert(before_hashes[x as int] != NO_HASH);
                assert(x < self.hashes.len());
                let key = self.hash_at(x);
                // The key is live, so it is not `NO_HASH` -- `RawTable::insert`'s
                // own precondition, discharged from the tombstone fact above.
                assert(key != NO_HASH);
                assert(key == self.slot_hash(x as int));
                assert(key == before_hashes[x as int]);
                // `insert` reports `false` only when the key is already stored, and
                // no two tombstones carry the same key, so this is always `true`.
                assert forall|j: int| 0 <= j < t.ctrl.capacity as int
                    implies !(t.ctrl.is_full_spec(j) && t.slot_hash(j) == key) by {
                    if 0 <= j < t.ctrl.capacity as int && t.ctrl.is_full_spec(j)
                        && t.slot_hash(j) == key {
                        assert(0 <= owner[j] && owner[j] < x as int);
                        assert(0 <= owner[j] && owner[j] < before_hashes.len());
                        assert(before_hashes[owner[j]] == key);
                        assert(owner[j] != x as int);
                        assert(before_hashes[owner[j]] != before_hashes[x as int]);
                        assert(false);
                    }
                }
                // ... and a slot is left, because the elements placed so far are
                // strictly fewer than the elements the new capacity must hold.
                proof {
                    assert(x + 1 <= old_cap);
                    assert(seq_full_count(before, (x + 1) as nat)
                        == seq_full_count(before, x as nat) + 1);
                    lemma_full_count_mono(before, (x + 1) as nat, old_cap_nat);
                }
                assert((t.len_ as nat) < old_len as nat);
                assert(t.len_ <= old_len);
                assert(old_len <= new_capacity);
                assert(t.len_ < t.ctrl.capacity);
                proof {
                    lemma_full_plus_free(t.ctrl.bytes@, t.ctrl.capacity as nat);
                    assert(seq_free_count(t.ctrl.bytes@, t.ctrl.capacity as nat) > 0);
                    lemma_positive_free_gives_has_free(&t.ctrl, t.ctrl.capacity as nat);
                }
                assert(t.has_free_slot());
                let (slot, claimed) = t.insert(key);
                assert(claimed);
                proof {
                    assert(slot < t.ctrl.capacity);
                    assert(0 <= (slot as int) && (slot as int) < t.ctrl.capacity as int);
                    assert(0 <= (slot as int) && (slot as int) < owner.len());
                    dest = dest.update(x as int, slot as int);
                    owner = owner.update(slot as int, x as int);
                }
            }
            x = x + 1;
        }
        proof {
            assert(x == old_cap);
            assert(t.len_ as nat == old_len as nat);
            assert forall|i: int| 0 <= i < old_cap_i implies
                (old(self).ctrl.is_full_spec(i) <==> before[i] <= 0x7F) by {
            }
            assert forall|i: int| 0 <= i < old_cap_i implies
                (#[trigger] dest[i] >= 0 <==> self.ctrl.is_dead_spec(i)) by {
            }
            assert forall|i: int| 0 <= i < old_cap_i implies
                (#[trigger] old(self).slot_hash(i) == before_hashes[i]) by {
            }
            // Turn the loop's two indexed placement records into the public
            // existential postconditions before moving `t` into `self`.  Keeping
            // these bridges explicit avoids asking SMT to discover that the
            // source-indexed `dest` and destination-indexed `owner` are witnesses.
            assert forall|i: int| 0 <= i < old_cap_i
                && old(self).ctrl.is_full_spec(i)
                implies exists|a: int| 0 <= a < t.ctrl.capacity as int
                    && t.ctrl.is_full_spec(a)
                    && t.slot_hash(a) == old(self).slot_hash(i) by {
                if 0 <= i < old_cap_i && old(self).ctrl.is_full_spec(i) {
                    assert(before[i] <= 0x7F);
                    assert(self.ctrl.is_dead_spec(i));
                    assert(dest[i] >= 0);
                    let a = dest[i];
                    assert(0 <= a < t.ctrl.capacity as int);
                    assert(t.ctrl.is_full_spec(a));
                    assert(t.slot_hash(a) == before_hashes[i]);
                    assert(before_hashes[i] == old(self).slot_hash(i));
                }
            }
            assert forall|a: int| 0 <= a < t.ctrl.capacity as int
                && t.ctrl.is_full_spec(a)
                implies exists|i: int| 0 <= i < old_cap_i
                    && old(self).ctrl.is_full_spec(i)
                    && old(self).slot_hash(i) == t.slot_hash(a) by {
                if 0 <= a < t.ctrl.capacity as int && t.ctrl.is_full_spec(a) {
                    assert(0 <= owner[a] < old_cap as int);
                    assert(0 <= owner[a] < old_cap_i);
                    assert(self.ctrl.is_dead_spec(owner[a]));
                    assert(old(self).ctrl.is_full_spec(owner[a]));
                    assert(t.slot_hash(a) == before_hashes[owner[a]]);
                    assert(before_hashes[owner[a]] == old(self).slot_hash(owner[a]));
                }
            }
        }
        *self = t;
    }

    /// The step-1 invariant `resize` runs on: after `clear_dead`, a tombstone is
    /// exactly where a full byte stood, so the live elements are exactly the
    /// tombstoned slots.
    pub open spec fn tombstones_are_the_old_full_slots(&self, before: Seq<u8>) -> bool {
        forall|i: int| 0 <= i < self.ctrl.capacity as int
            ==> (self.ctrl.is_dead_spec(i) <==> (before[i] as int <= 127))
    }
}




/// Isolated control-window fixture for the upstream kEmpty erase outcome.
fn probe_was_never_full_kempty_branch() {
    let mut c = ControlBytes::new(31);
    c.set_full(0, 0);
    proof {
        reveal_with_fuel(crate::control_bytes::empty_run_forward, 18);
        reveal_with_fuel(crate::control_bytes::empty_run_backward, 18);
        reveal(crate::control_bytes::was_never_full_in);
    }
    assert(c.was_never_full_spec(0));
}

/// Isolated control-window fixture for the upstream kDeleted erase outcome:
/// sixteen consecutive full bytes surround the erased index.
fn probe_was_never_full_kdeleted_branch() {
    let mut c = ControlBytes::new(31);
    let mut i: usize = 0;
    while i < 16
        invariant
            i <= 16,
            c.well_formed(),
            forall|j: int| 0 <= j < i as int ==> c.bytes[j] == 0,
            forall|j: int| i as int <= j < 31 ==> c.bytes[j] == crate::control_bytes::EMPTY,
        decreases 16 - i,
    {
        c.set_full(i, 0);
        i = i + 1;
    }
    proof {
        reveal_with_fuel(crate::control_bytes::empty_run_forward, 18);
        reveal_with_fuel(crate::control_bytes::empty_run_backward, 18);
        reveal(crate::control_bytes::was_never_full_in);
    }
    assert(!c.was_never_full_spec(8));
}

} // verus!
