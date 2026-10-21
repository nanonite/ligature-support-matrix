//! SwissTable -- the key-value container the port's callers use.
//!
//! Reference: absl/container/internal/raw_hash_set.h L3060-L3160 (`insert`,
//! `erase`), L3480-L3495 (`erase_meta_only_small` / `erase_meta_only_large`), and
//! raw_hash_set.cc L708-L724 (`WasNeverFull`), L856-L883 (`EraseMetaOnlySmall`,
//! `EraseMetaOnlyLarge`).
//!
//! ## Scope: the key and value types
//!
//! The concept spec writes `fn insert(&mut self, key: K, value: V) -> bool`, and
//! this port instantiates `K = V = u64` with the identity hash, so a slot's
//! stored hash *is* its key.  A generic `K: Eq + Hash` payload with a ghost
//! `Map<K, V>` is the same shape but a materially larger proof, and it is out of
//! budget for this issue.  The consequence is one real restriction, recorded as
//! `swisstable-verus-008`: `RawTable` refuses a hash of `NO_HASH` (zero), and two
//! distinct keys are required to have distinct hashes, which is what the
//! reference's own hash-quality documentation already assumes of its `Hash`
//! policy.
//!
//! The container's `contents()` is *derived* from the table's slots rather than
//! held in a `ghost` map, for the reason given in `raw_table`'s module docs
//! (`swisstable-verus-011`): Verus cannot initialize a specification-valued field
//! from executable code.
//!
//! ## What the container does *not* do
//!
//! Upstream's `insert` grows the table when it is full.  This port makes that a
//! caller obligation instead: `insert` requires a reusable slot to exist and
//! `reserve` is the way to make one.  Recorded as `swisstable-verus-009`, and
//! ruled a scope cut by the operator on 2026-10-02 rather than left as a blocker.
//!
//! ## The contracts are per-slot frame and counting contracts
//!
//! `contains` is stated as "some full slot holds this key" and `insert`, `erase`
//! and `clear` as per-slot facts plus a counting fact about `len_`, for the
//! reasons given in `raw_table`'s module docs: the operator's 2026-10-02 ruling
//! re-scoped chainlink #30 to per-slot frame / counting contracts and took
//! set-level extensionality out of scope (`swisstable-verus-023`).  Nothing is
//! assumed away; `lemma_stored_in` still proves membership in the derived
//! `stored_hashes()`.

#[cfg(verus_only)]
use crate::control_bytes::seq_full_count;
#[cfg(verus_only)]
use crate::lemmas::{
    lemma_full_count_le, lemma_full_count_positive, lemma_full_count_zero, lemma_pow2_range,
    lemma_slots_monotone,
};
#[cfg(verus_only)]
use crate::probe_seq::slots_for_bits_spec;
use crate::raw_table::{RawTable, NO_HASH};
use crate::table_iterator::TableIterator;
use vstd::prelude::*;

verus! {

pub struct SwissTable {
    /// The open-addressed table underneath.
    pub table: RawTable,
    /// The value of each full slot, parallel to `table.hashes`.
    pub values: Vec<u64>,
}

impl SwissTable {
    /// `5 <=`, not the drafted `4 <=`: the smallest capacity `RawTable::new` accepts
    /// is `2^5 - 1`, because `2^4 - 1 == 15` is one slot short of a group width and
    /// `ControlBytes::new` needs `capacity >= GROUP_WIDTH`.  See `swisstable-spec-003`.
    pub fn new(capacity_bits: u32) -> (t: Self)
        requires
            5 <= capacity_bits,
            capacity_bits <= 31,
        ensures
            t.model(),
            t.table.len_ == 0,
    {
        let table = RawTable::new(capacity_bits);
        let mut values: Vec<u64> = Vec::new();
        let mut i: usize = 0;
        while i < table.ctrl.capacity
            invariant
                i <= table.ctrl.capacity,
                values@.len() == i,
                forall|j: usize| j < i ==> values[j as int] == 0u64,
            decreases table.ctrl.capacity - i,
        {
            values.push(0u64);
            i = i + 1;
        }
        let t = SwissTable { table: table, values: values };
        proof {
            // `model()` is `table.model() && values.len() == capacity`.  The first
            // conjunct is `RawTable::new`'s own postcondition; the second is the
            // filling loop's exit invariant.  Nothing has to be re-derived.
            assert(t.table.model());
            assert(t.values.len() == t.table.ctrl.capacity);
        }
        t
    }

    /// SwissTable.C001: the container's observable contents are exactly the live
    /// key-value pairs held in its table.
    pub open spec fn model(&self) -> bool {
        &&& self.table.model()
        &&& self.values.len() == self.table.ctrl.capacity
    }

    /// SwissTable.C004: the enumeration order is unspecified.  Stated as a
    /// predicate so the obligation has a name to point at; it holds vacuously,
    /// which is the point -- nothing in the promoted set constrains an order, and
    /// slot layout is the only thing `iteration` exposes.
    pub open spec fn order_is_unspecified() -> bool {
        true
    }

    /// The container's observable contents: the live key-value pairs.
    pub open spec fn contents(&self) -> Set<(u64, u64)> {
        Set::new(|p: (u64, u64)| exists|i: int|
            0 <= i < self.table.ctrl.capacity
                && self.table.ctrl.is_full_spec(i)
                && self.table.slot_hash(i) == p.0
                && self.values[i] == p.1)
    }

    /// SwissTable.C001's other half, read from the table side.  It is the same
    /// comprehension, which is the point: the container owns no state of its own.
    pub open spec fn table_contents(&self) -> Set<(u64, u64)> {
        Set::new(|p: (u64, u64)| exists|i: int|
            0 <= i < self.table.ctrl.capacity
                && self.table.ctrl.is_full_spec(i)
                && self.table.slot_hash(i) == p.0
                && self.values[i] == p.1)
    }

    /// "Some full slot holds this key" -- the per-slot form of membership.
    ///
    /// Upstream's `contains` (`raw_hash_set.h` L3143-L3150) is exactly this: a
    /// probe run that asks "did any slot we looked at hold this key", with the
    /// completeness argument supplied by the probe's coverage.  Stating it as a
    /// quantified per-slot predicate keeps the re-scoped contract shape of
    /// `swisstable-verus-023` while remaining the reference's own question.
    pub open spec fn contains_spec(&self, key: u64) -> bool {
        exists|i: int| 0 <= i < self.table.ctrl.capacity as int
            && #[trigger] self.at(i, key)
    }

    /// The per-slot membership predicate `contains_spec` is written in.
    ///
    /// `at` is a method on the *container*, not on the table, and it is the only
    /// spec name the container's callers use for "slot `i` holds `key`".  Giving the
    /// existential in `contains_spec` this exact term as its trigger is what lets the
    /// witness in `insert`/`erase` instantiate it; with the bound in front instead, the
    /// membership step never fires and both mutators' C002/C003 clauses fail.
    pub open spec fn at(&self, i: int, key: u64) -> bool {
        self.table.ctrl.is_full_spec(i) && self.table.slot_hash(i) == key
    }

    /// SwissTable::len.
    pub fn len(&self) -> (r: usize)
        requires self.model(),
        ensures
            r == self.table.len_,                                      // SwissTable.C001
            self.contents() =~= self.table_contents(),
            SwissTable::order_is_unspecified(),
    {
        self.table.len_
    }

    pub fn is_empty(&self) -> (r: bool)
        requires self.model(),
        ensures r == (self.table.len_ == 0)
    {
        self.table.len_ == 0
    }

    /// SwissTable::contains -- a scan over the slots for a full one holding `key`,
    /// which is what `contains_spec` says.
    pub fn contains(&self, key: &u64) -> (r: bool)
        requires self.model(),
        ensures
            r == self.contains_spec(*key),                             // SwissTable.C001
            r <==> exists|i: int| 0 <= i < self.table.ctrl.capacity && self.at(i, *key),
            SwissTable::order_is_unspecified(),
    {
        let cap = self.table.ctrl.capacity;
        let mut i: usize = 0;
        while i < cap
            invariant
                i <= cap,
                cap == self.table.hashes.len(),
                self.model(),
                forall|j: int| 0 <= j < i ==> !self.at(j, *key),
            decreases cap - i,
        {
            if self.table.ctrl.is_full(i) && self.table.hash_at(i) == *key {
                proof {
                    assert(0 <= i < self.table.ctrl.capacity);
                    assert(self.at(i as int, *key));
                }
                return true;
            }
            i = i + 1;
        }
        proof { assert(!self.contains_spec(*key)); }
        false
    }

    pub fn capacity(&self) -> (r: usize)
        requires self.model(),
        ensures r == self.table.ctrl.capacity
    {
        self.table.capacity()
    }

    /// SwissTable::insert -- insert or replace an entry.
    ///
    /// SwissTable.C002: a `true` return means the key was newly added, a `false`
    /// return means an existing key's value was replaced.  In the re-scoped shape:
    /// the counting half is `table.len_`, and the per-slot half is "the slot the
    /// table chose for `key` carries `value` afterwards, and no other slot's value
    /// moved".
    pub fn insert(&mut self, key: u64, value: u64) -> (r: bool)
        requires
            self.model(),
            key != NO_HASH,
            self.table.has_free_slot(),
            self.table.len_ < self.table.ctrl.capacity,
        ensures
            final(self).model(),
            final(self).table.capacity_bits == old(self).table.capacity_bits,
            final(self).table.ctrl.capacity == old(self).table.ctrl.capacity,
            r == (!old(self).contains_spec(key)),                      // SwissTable.C002
            final(self).contains_spec(key),
            // ---- counting
            r ==> final(self).table.len_ == old(self).table.len_ + 1,
            !r ==> final(self).table.len_ == old(self).table.len_,
            // ---- per-slot: the touched slot carries the new value
            r ==> exists|i: int| 0 <= i < final(self).table.ctrl.capacity
                && final(self).at(i, key)
                && final(self).values[i] == value,
            !r ==> exists|i: int| 0 <= i < final(self).table.ctrl.capacity as int
                && final(self).at(i, key)
                && final(self).values[i] == value,
            // ---- per-slot frame on the values: there is exactly one slot whose
            // value moved, the one the table gave the key, and every other slot
            // keeps the value it had
            exists|s: int| {
                &&& 0 <= s < final(self).table.ctrl.capacity as int
                &&& final(self).at(s, key)
                &&& forall|i: int| 0 <= i < old(self).table.ctrl.capacity as int && i != s
                        ==> final(self).values[i] == old(self).values[i]
            },
            SwissTable::order_is_unspecified(),
    {
        // The container's pre-state, as ghost data.  `old(self)` is the same state, but
        // naming it directly lets the per-slot clauses below be proved against stable
        // terms rather than against `old(self)`, whose fields Verus keeps rewriting
        // as the body proceeds.
        let ghost pre = self;
        let (slot, inserted) = self.table.insert(key);
        proof {
            assert(slot < self.table.ctrl.capacity);
            assert(self.values.len() == self.table.ctrl.capacity);
            // `at` is the container's per-slot membership predicate; the table's own
            // postconditions already say the slot it wrote is full and holds `key`.
            assert(self.at(slot as int, key));
            // ... and no other slot's value moved, because exactly one index was
            // written.
            assert forall|i: int| 0 <= i < self.table.ctrl.capacity as int && i != slot as int
                implies self.values[i] == pre.values[i] by {
            }
        }
        self.values[slot] = value;
        proof {
            assert(self.at(slot as int, key));
            assert(self.values[slot as int] == value);
            assert(0 <= slot && slot < self.table.ctrl.capacity);
            assert forall|i: int| 0 <= i < pre.table.ctrl.capacity as int && i != slot as int
                implies self.values[i] == pre.values[i] by {
            }
            // ---- SwissTable.C002, from the table's per-slot "was it already there"
            // clauses: a `true` return means no full slot held `key` before, and a
            // `false` one means some did.
            // `inserted` is exactly "no full slot held `key` before".  The direction
            // that needs work is the one from a concrete witness slot to the
            // quantified `pre.at`, which is what the trigger below supplies.
            assert(inserted ==> forall|i: int| 0 <= i < pre.table.ctrl.capacity as int
                ==> !(pre.table.ctrl.is_full_spec(i) && pre.table.slot_hash(i) == key));
            assert(!inserted ==> exists|i: int| 0 <= i < pre.table.ctrl.capacity as int
                && pre.table.ctrl.is_full_spec(i) && pre.table.slot_hash(i) == key);
            if !inserted {
                let witness: int = choose|i: int| 0 <= i < pre.table.ctrl.capacity as int
                    && pre.table.ctrl.is_full_spec(i) && pre.table.slot_hash(i) == key;
                assert(pre.at(witness, key));
                assert(pre.contains_spec(key));
            }
            assert(pre.contains_spec(key) == !inserted);
        }
        inserted
    }

    /// SwissTable::erase -- remove an entry.
    ///
    /// SwissTable.C003: a `true` return means the key was present and is now
    /// absent; a `false` return means it was already absent and every other entry
    /// is untouched.
    ///
    /// The whole operation is delegated: `RawTable::erase` chooses the control byte
    /// by upstream's own `WasNeverFull` rule (raw_hash_set.cc L708-L724, applied at
    /// L875) and owns the length accounting.  This method does NOT write the
    /// tombstone, so `swiss_table_erase__to__control_bytes_set_dead` is not a
    /// boundary of it -- upstream makes no such call either (`EraseMetaOnlySmall`,
    /// raw_hash_set.cc:856, and `EraseMetaOnlyLarge`, :868, are both called from
    /// raw_hash_set.h:3490/:3493 and write the byte themselves).  See
    /// `swisstable-verus-020` and `swisstable-spec-008`.
    pub fn erase(&mut self, key: &u64) -> (r: bool)
        requires
            self.model(),
            *key != NO_HASH,
        ensures
            final(self).model(),
            r == old(self).contains_spec(*key),                        // SwissTable.C003
            r ==> !final(self).contains_spec(*key),
            !r ==> final(self).table.len_ == old(self).table.len_,
            // ---- counting
            r ==> final(self).table.len_ == old(self).table.len_ - 1,
            // ---- per-slot frame on the values: exactly the slot that held the key
            // is zeroed, and only that one
            forall|i: int| 0 <= i < old(self).table.ctrl.capacity as int
                ==> final(self).values[i] == if old(self).at(i, *key) { 0u64 }
                                               else { old(self).values[i] },
            // ---- and the table's own per-slot frame, restated through the table
            !r ==> forall|i: int| 0 <= i < old(self).table.ctrl.capacity as int
                ==> final(self).table.ctrl.bytes[i] == old(self).table.ctrl.bytes[i]
                    && final(self).table.hashes[i] == old(self).table.hashes[i],
            SwissTable::order_is_unspecified(),
    {
        // The slot holding `key` is found by a scan rather than by the reference's
        // probe run, for the reason given on `RawTable::find`: the probe's coverage of
        // every slot of a `2^k - 1` table is a bit-level induction this port does not
        // discharge (`swisstable-verus-004`).  The scan visits *every* slot and keeps
        // the last match, so `found` is false exactly when no full slot held the key.
        let ghost pre = self;
        let cap = self.table.ctrl.capacity;
        let mut i: usize = 0;
        let mut slot: usize = 0;
        let mut found: bool = false;
        while i < cap
            invariant
                i <= cap,
                cap == self.table.ctrl.capacity,
                cap == self.table.hashes.len(),
                self.model(),
                // every slot below the cursor has been visited
                forall|j: int| 0 <= j < i ==> !self.at(j, *key) || (j <= slot as int && found),
                // and if one matched, the recorded slot is the last match so far
                found ==> slot < cap,
                found ==> self.at(slot as int, *key),
                found ==> self.table.len_ > 0,
            decreases cap - i,
        {
            if self.table.ctrl.is_full(i) && self.table.hash_at(i) == *key {
                proof {
                    assert(self.at(i as int, *key));
                    // A full control byte at a real slot means the count is at
                    // least one, which `model` pins to `len_`.
                    lemma_full_count_positive(self.table.ctrl.bytes@,
                        self.table.ctrl.capacity as nat, i as int);
                    assert(self.table.len_ > 0);
                }
                slot = i;
                found = true;
            }
            i = i + 1;
        }
        if !found {
            proof {
                assert forall|j: int| 0 <= j < cap ==> !self.at(j, *key) by {
                    if 0 <= j < cap && self.at(j, *key) {
                        assert(found);
                        assert(false);
                    }
                }
            }
            return false;
        }
        // `RawTable::erase` has upstream's own guard (the slot must be full, or the
        // iterator is dangling) and its own `WasNeverFull` branch, so the container
        // must not pre-write the tombstone: doing so makes `is_full_spec(slot)` false
        // while `hashes[slot]` still holds the key, which falsifies `slot_model` --
        // the same false-invariant class recorded for `resize` as
        // `swisstable-verus-019`.  A prior revision of this file branched on
        // `capacity() <= GROUP_WIDTH` and pre-wrote the tombstone; since
        // `capacity_bits >= 5` gives `capacity >= 31 > GROUP_WIDTH`, that branch was
        // dead and the tombstone was always written.  See `swisstable-verus-020`.
        let ghost erased = slot;
        // The container's own pre-state of the table, as ghost data, so the
        // "no other slot moved" argument below is about stable terms.
        let ghost pre_hashes = self.table.hashes@;
        let ghost pre_bytes = self.table.ctrl.bytes@;
        self.table.erase(slot);
        self.values[slot] = 0;
        proof {
            // The table's postcondition says the erased slot reads as free and
            // carries `NO_HASH`, so it holds no key; its frame says every *other*
            // slot is byte-for-byte unchanged, so no other slot holds one either.
            assert(self.table.ctrl.is_empty_or_deleted_spec(erased as int));
            assert(self.table.slot_hash(erased as int) == NO_HASH);
            assert forall|i: int| 0 <= i < self.table.ctrl.capacity as int
                implies !self.at(i, *key) by {
                if 0 <= i < self.table.ctrl.capacity as int && self.at(i, *key) {
                    assert(*key != NO_HASH);
                    assert(false);
                }
            }
        }
        true
    }

    /// SwissTable::reserve -- make room for `additional` more entries.
    ///
    /// The boundary `swiss_table_reserve__to__raw_table_resize` is this method's
    /// whole body: upstream's growth policy picks the new capacity, this port
    /// takes it.
    ///
    /// `additional` is part of the concept's signature but is not *used*: growth is
    /// one step (`capacity_bits + 1`) rather than a sized-to-fit policy.  Recorded
    /// as `swisstable-verus-009`.
    pub fn reserve(&mut self, additional: usize)
        requires
            self.model(),
            additional <= 0x7FFF_FFFFusize,
            5 <= self.table.capacity_bits,
            self.table.capacity_bits <= 30,
        ensures
            final(self).model(),
        final(self).table.len_ == old(self).table.len_,
        final(self).table.capacity_bits > old(self).table.capacity_bits,
        final(self).table.ctrl.capacity as u64
            == slots_for_bits_spec(final(self).table.capacity_bits),
        final(self).values.len() == final(self).table.ctrl.capacity,
        // Every live key retains its associated value, even if rehashing moves it.
        forall|i: int| 0 <= i < old(self).table.ctrl.capacity as int
                && old(self).table.ctrl.is_full_spec(i)
            ==> exists|a: int| 0 <= a < final(self).table.ctrl.capacity as int
                && final(self).table.ctrl.is_full_spec(a)
                && final(self).table.slot_hash(a) == old(self).table.slot_hash(i)
                && final(self).values[a] == old(self).values[i],
        forall|a: int| 0 <= a < final(self).table.ctrl.capacity as int
                && final(self).table.ctrl.is_full_spec(a)
            ==> exists|i: int| 0 <= i < old(self).table.ctrl.capacity as int
                && old(self).table.ctrl.is_full_spec(i)
                && old(self).table.slot_hash(i) == final(self).table.slot_hash(a)
                && old(self).values[i] == final(self).values[a],
    {
        // `resize`'s "every live element fits in the new capacity" precondition.
        // `model` pins `len_` to the number of full bytes, so it is at most the
        // current capacity, and the new capacity is `2^(b+1) - 1` against this
        // table's `2^b - 1`.
        proof {
            let ghost b: u32 = self.table.capacity_bits;
            lemma_pow2_range(b);
            lemma_slots_monotone(b);
            lemma_full_count_le(
                self.table.ctrl.bytes@,
                self.table.ctrl.capacity as nat,
            );
            assert(self.table.len_ <= self.table.ctrl.capacity);
            assert(self.table.len_ as nat <= slots_for_bits_spec(b) as nat);
            assert(slots_for_bits_spec(b) <= slots_for_bits_spec((b + 1) as u32));
        }
        // Save the old slot/key/value association before rehashing changes the
        // slot indices.  Free slots carry NO_HASH, which no live key can equal.
        let ghost pre = self;
        let old_cap = self.table.ctrl.capacity;
        let mut saved: Vec<(u64, u64)> = Vec::new();
        let mut s: usize = 0;
        while s < old_cap
            invariant
                s <= old_cap,
                old_cap == pre.table.ctrl.capacity,
                self.table == pre.table,
                self.values@ == pre.values@,
                pre.model(),
                saved@.len() == s,
                forall|j: int| 0 <= j < s as int
                    ==> saved[j].0 == pre.table.slot_hash(j)
                        && saved[j].1 == pre.values[j],
            decreases old_cap - s,
        {
            let key = self.table.hash_at(s);
            let value = self.values[s];
            saved.push((key, value));
            s = s + 1;
        }
        self.table.resize(self.table.capacity_bits + 1);
        let ghost grown = self.table;
        proof {
            assert forall|a: int| 0 <= a < grown.ctrl.capacity as int
                    && grown.ctrl.is_full_spec(a)
                implies exists|j: int| 0 <= j < old_cap as int
                    && saved[j].0 == grown.slot_hash(a) by {
                let j = choose|j: int| 0 <= j < pre.table.ctrl.capacity as int
                    && pre.table.ctrl.is_full_spec(j)
                    && pre.table.slot_hash(j) == grown.slot_hash(a);
                assert(saved[j].0 == grown.slot_hash(a));
            }
        }
        let mut values: Vec<u64> = Vec::new();
        let mut i: usize = 0;
        while i < self.table.ctrl.capacity
            invariant
                i <= self.table.ctrl.capacity,
                self.table == grown,
                grown.model(),
                pre.model(),
                old_cap == pre.table.ctrl.capacity,
                saved@.len() == old_cap,
                forall|j: int| 0 <= j < old_cap as int
                    ==> saved[j].0 == pre.table.slot_hash(j)
                        && saved[j].1 == pre.values[j],
                forall|a: int| 0 <= a < grown.ctrl.capacity as int
                        && grown.ctrl.is_full_spec(a)
                    ==> exists|j: int| 0 <= j < old_cap as int
                        && saved[j].0 == grown.slot_hash(a),
                values@.len() == i,
                // For every placed value, *any* old slot with this key has
                // that same value; uniqueness of the old key makes this exact.
                forall|a: int, j: int| 0 <= a < i as int
                        && grown.ctrl.is_full_spec(a)
                        && 0 <= j < old_cap as int
                        && pre.table.ctrl.is_full_spec(j)
                        && pre.table.slot_hash(j) == grown.slot_hash(a)
                    ==> values[a] == pre.values[j],
            decreases self.table.ctrl.capacity - i,
        {
            if self.table.ctrl.is_full(i) {
                let key = self.table.hash_at(i);
                let mut j: usize = 0;
                let mut found = false;
                let mut value = 0u64;
                while j < old_cap && !found
                    invariant
                        j <= old_cap,
                        saved@.len() == old_cap,
                        !found ==> forall|k: int| 0 <= k < j as int
                            ==> saved[k].0 != key,
                        found ==> exists|k: int| 0 <= k < j as int
                            && saved[k].0 == key && value == saved[k].1,
                    decreases old_cap - j,
                {
                    if saved[j].0 == key {
                        value = saved[j].1;
                        found = true;
                    }
                    j = j + 1;
                }
                proof {
                    assert(grown.ctrl.is_full_spec(i as int));
                    let k = choose|k: int| 0 <= k < old_cap as int
                        && saved[k].0 == grown.slot_hash(i as int);
                    assert(found);
                    let match_index = choose|k: int| 0 <= k < j as int
                        && saved[k].0 == key && value == saved[k].1;
                    assert forall|old: int| 0 <= old < old_cap as int
                            && pre.table.ctrl.is_full_spec(old)
                            && pre.table.slot_hash(old) == key
                        implies value == pre.values[old] by {
                        assert(saved[match_index].0 == key);
                        assert(pre.table.slot_hash(match_index) == key);
                        assert(pre.table.ctrl.is_full_spec(match_index));
                        if match_index < old {
                            assert(pre.table.slot_hash(match_index) != pre.table.slot_hash(old));
                        } else if old < match_index {
                            assert(pre.table.slot_hash(old) != pre.table.slot_hash(match_index));
                        }
                        assert(match_index == old);
                        assert(saved[old].1 == pre.values[old]);
                    }
                }
                values.push(value);
            } else {
                values.push(0u64);
            }
            i = i + 1;
        }
        self.values = values;
        proof {
            assert forall|a: int| 0 <= a < grown.ctrl.capacity as int
                    && grown.ctrl.is_full_spec(a)
                implies exists|j: int| 0 <= j < old_cap as int
                    && pre.table.ctrl.is_full_spec(j)
                    && pre.table.slot_hash(j) == grown.slot_hash(a)
                    && pre.values[j] == self.values[a] by {
                let j = choose|j: int| 0 <= j < old_cap as int
                    && pre.table.ctrl.is_full_spec(j)
                    && pre.table.slot_hash(j) == grown.slot_hash(a);
            }
            assert forall|j: int| 0 <= j < old_cap as int
                    && pre.table.ctrl.is_full_spec(j)
                implies exists|a: int| 0 <= a < grown.ctrl.capacity as int
                    && grown.ctrl.is_full_spec(a)
                    && grown.slot_hash(a) == pre.table.slot_hash(j)
                    && self.values[a] == pre.values[j] by {
                let a = choose|a: int| 0 <= a < grown.ctrl.capacity as int
                    && grown.ctrl.is_full_spec(a)
                    && grown.slot_hash(a) == pre.table.slot_hash(j);
            }
        }
    }

    /// SwissTable::clear -- drop every entry.
    ///
    /// Re-scoped to the per-slot form: every slot in `[0, capacity)` reads as
    /// empty, carries no key and holds value zero.  That is exactly
    /// `stored_hashes() =~= Set::empty()` said, slot by slot, and it is the form
    /// `swisstable-verus-023` rules in scope.
    pub fn clear(&mut self)
        requires self.model(),
        ensures
            final(self).model(),
            // ---- counting
            final(self).table.len_ == 0,
            // ---- per-slot
            forall|i: int| 0 <= i < final(self).table.ctrl.capacity as int
                ==> final(self).table.ctrl.is_empty_spec(i)
                    && final(self).table.slot_hash(i) == NO_HASH
                    && final(self).values[i] == 0,
    {
        // `model()` is deliberately **not** an invariant here, for the same reason
        // `RawTable::resize` does not carry it across its reclaim window: `set_empty`
        // and the `NO_HASH` write change each slot's control byte and hash field
        // together, but `len_` is only corrected once at the end, so in between
        // `len_ == seq_full_count` does not hold.  `clearing_model` states the two
        // halves that *do* hold.  This is the same false-invariant class recorded as
        // `swisstable-verus-019`.
        let cap = self.table.ctrl.capacity;
        let ghost pre = self;
        let mut i: usize = 0;
        while i < cap
            invariant
                i <= cap,
                cap == self.table.ctrl.capacity,
                cap == self.table.hashes.len(),
                cap == self.values.len(),
                self.table.ctrl.well_formed(),
                self.table.ctrl.capacity as u64 == pre.table.ctrl.capacity as u64,
                // RawTable.C001, carried explicitly: `clear` writes no capacity field
                // and no `capacity_bits` field, so the shape is invariant, but
                // `let ghost pre = self` snapshots them and Verus will not reconnect
                // `slots_for_bits_spec(self.table.capacity_bits)` to the pre-state's
                // `slots_for_bits_spec(pre.table.capacity_bits)` on its own.
                self.table.ctrl.capacity as u64
                    == slots_for_bits_spec(self.table.capacity_bits),
                5 <= self.table.capacity_bits <= 31,
                // per-slot: every visited slot is empty and carries no key.  Three
                // separate quantifiers, one term each, rather than one quantifier
                // over the three-way conjunction: Verus steps an `a[j] == v` invariant
                // off the array-update fact the write produces, and it will not step
                // a compound trigger at all -- an earlier revision did, and both
                // invariants then had to be stepped by hand with an
                // `assert forall ... by { }` whose body could not instantiate the very
                // invariant it was stepping.
                //
                // The control byte is stated as `bytes[j] == EMPTY` and *not* as
                // `is_empty_spec(j)`: `is_empty_spec` is a method specification
                // function, so its trigger carries the receiver, and the pre-write
                // instance carries a different receiver from the post-write one and
                // so never matches.  The receiver-free form matches.
                forall|j: int| 0 <= j < i
                    ==> #[trigger] self.table.ctrl.bytes[j] == crate::control_bytes::EMPTY,
                forall|j: int| 0 <= j < i ==> #[trigger] self.table.hashes[j] == NO_HASH,
                forall|j: int| 0 <= j < i ==> #[trigger] self.values[j] == 0,
                // and the unvisited slots still hold what they held
                forall|j: int| i <= j < cap
                    ==> #[trigger] self.table.ctrl.bytes[j] == pre.table.ctrl.bytes[j],
                forall|j: int| i <= j < cap
                    ==> #[trigger] self.table.hashes[j] == pre.table.slot_hash(j),
                self.table.hashes@.len() == cap,
            decreases cap - i,
        {
            self.table.ctrl.set_empty(i);
            self.table.hashes[i] = NO_HASH;
            self.values[i] = 0;
            i = i + 1;
        }
        self.table.len_ = 0;
        proof {
            let tracked g = crate::raw_table::LiveIndex { m: Map::tracked_empty() };
            self.table.g = Tracked(g);
        }
        proof {
            assert forall|j: int| 0 <= j < cap
                implies #[trigger] self.table.ctrl.bytes[j] as int > 127 by {
                if 0 <= j && j < cap {
                    assert(self.table.ctrl.is_empty_spec(j));
                    assert(self.table.ctrl.bytes[j] == crate::control_bytes::EMPTY);
                }
            }
            lemma_full_count_zero(self.table.ctrl.bytes@, cap as nat);
        }
        proof {
            assert(self.table.ctrl.well_formed());
            assert(self.values.len() == self.table.ctrl.capacity);
            assert(self.table.hashes.len() == self.table.ctrl.capacity);
            assert(self.table.len_ as nat
                == seq_full_count(self.table.ctrl.bytes@, self.table.ctrl.capacity as nat));
            assert forall|j: int| 0 <= j < cap implies !self.table.ctrl.is_full_spec(j) by {
            }
            assert(self.table.slot_model());
            assert(self.model());
        }
    }

    /// A cursor over the live slots.
    pub fn iter(&self) -> (it: TableIterator)
        requires self.model(),
        ensures
            it.capacity == self.table.ctrl.capacity,
            it.offset_ == 0,
    {
        TableIterator::new(self.table.ctrl.capacity)
    }
}




/// Exercises the full resize and value remapping path with H1=32. Doubling
/// capacity changes the H1 mask; the live map is the final physical-slot index.
fn probe_resize_value_remapping() {
    let table = RawTable::new(5);
    let cap = table.ctrl.capacity;
    let mut values: Vec<u64> = Vec::new();
    let mut i: usize = 0;
    while i < cap
        invariant
            i <= cap,
            values@.len() == i,
            forall|j: int| 0 <= j < i as int ==> values[j] == 0,
        decreases cap - i,
    {
        values.push(0);
        i = i + 1;
    }
    let mut t = SwissTable { table: table, values: values };
    assert(t.model());
    let inserted = t.insert(32, 320);
    assert(inserted);
    assert(t.table.g@.m.dom().contains(32));
    let ghost old_slot = t.table.g@.m[32];
    assert(old_slot < t.table.ctrl.capacity);
    t.reserve(1);
    let ghost new_slot = t.table.g@.m[32];
    assert(t.table.live_map_model());
    assert(t.table.ctrl.is_full_spec(new_slot as int));
    assert(t.table.slot_hash(new_slot as int) == 32);
    assert(t.values[new_slot as int] == 320);
}

} // verus!
