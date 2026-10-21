//! ProbeSeq -- the bounded triple-step probe sequence.
//!
//! Reference: absl/container/internal/raw_hash_set.h L1770-L1810.
//!
//! ```text
//!   probe_seq(capacity, hash) : capacity_(capacity), offset_(hash & capacity_)
//!   offset()      -> offset_
//!   offset(i)     -> (offset_ + i) & capacity_
//!   next()        -> index_ += Width; offset_ += index_; offset_ &= capacity_
//!   index()       -> index_            // 0-based, a multiple of Width
//! ```
//!
//! The three state words are `u64` rather than `usize`: Verus reasons about bit
//! operations on concrete primitives in specification code (`u64` here) while
//! `usize` is `int` there, and `offset(i)`'s postcondition is written over `&`.
//! `offset`/`offset_at` hand back a `usize` index for the callers.
//!
//! The sums go through `vstd::wrapping` for the same reason.  The
//! `capacity_bits <= 31` bound in `new` keeps the narrowing into a `usize` capacity
//! safe, so `wrapping_add` and the reference's `+=` agree; it is an extra
//! precondition on top of the drafted ProbeSeq.C001 and is recorded as
//! `swisstable-spec-003`.
//! The mask facts come from `verif/lemmas.rs` (see `swisstable-verus-014`).

use crate::control_bytes::GROUP_WIDTH as GROUP_WIDTH_;
#[cfg(verus_only)]
use crate::lemmas::{
    lemma_add_group_width_mod, lemma_and_below, lemma_narrow_roundtrip, lemma_pow2_range,
    lemma_slots_roundtrip,
};
use vstd::prelude::*;
#[cfg(verus_only)]
use vstd::wrapping::u64_specs::{wrapping_add, wrapping_sub};

verus! {

/// `2^bits - 1`: the slot count a table of that `capacity_bits` has.
pub open spec fn slots_for_bits_spec(bits: u32) -> u64 {
    wrapping_sub(1u64 << (bits % 64u32), 1u64)
}

/// `slots_for_bits_spec`, as an executable function so that a constructor can size
/// an array from it.  `bits <= 31` everywhere it is called, which is what keeps the
/// shift and the subtraction inside both `u64` and the 32-bit `usize` this Verus
/// models (`swisstable-verus-016`).
pub fn slots_for_bits(bits: u32) -> (r: u64)
    requires bits <= 31,
    ensures r == slots_for_bits_spec(bits)
{
    proof { lemma_pow2_range(bits); }
    let s: u64 = 1u64 << bits;
    s - 1
}

/// `a + b`, `u64`-typed so it can be masked in a specification clause.
pub open spec fn add_u64(a: u64, b: u64) -> u64 {
    wrapping_add(a, b)
}

pub struct ProbeSeq {
    /// `NumSlots`; the mask applied to every offset.
    pub capacity_mask: u64,
    /// `capacity_mask + 1`, i.e. `2^capacity_bits`.  Carried so the overflow
    /// bounds on `offset_ + index_` are visible without a shift in the
    /// specification.
    pub capacity_size: u64,
    /// `log2(capacity_mask + 1)`, carried so ProbeSeq.C001 can be stated as the
    /// concept states it.
    pub capacity_bits: u32,
    /// The current slot index.
    pub offset_: u64,
    /// The 0-based probe index, a multiple of the group width.
    pub index_: u64,
}

impl ProbeSeq {
    /// ProbeSeq.C001: build a sequence for a capacity that is `2^n - 1` with
    /// `n >= 4`.  The concept's clause is written over `capacity_bits`; the
    /// `capacity_bits <= 31` half is an extra bound this port adds.  It is there for
    /// the *narrowing* into a `usize` capacity, not because `usize` is known to be
    /// that narrow: this Verus will not say what `usize`'s width is
    /// (`swisstable-verus-016`), so `lemma_slots_roundtrip` bounds the capacity by
    /// `0xFFFF_FFFF`, the smallest figure nameable here, and that is what fixes 31.
    /// The reference has no such bound, since its `size_t` arithmetic is unchecked.
    pub fn new(capacity_bits: u32) -> (s: Self)
        requires
            4 <= capacity_bits,
            capacity_bits <= 31,
        ensures
            s.capacity_bits == capacity_bits,
            s.capacity_mask == slots_for_bits_spec(capacity_bits),
            s.capacity_size == (1u64 << (capacity_bits as u32)),
            s.offset_ == 0,
            s.index_ == 0,
            s.well_formed(),
    {
        proof {
            lemma_pow2_range(capacity_bits);
            lemma_slots_roundtrip(capacity_bits);
        }
        let capacity_size: u64 = 1u64 << capacity_bits;
        let s = ProbeSeq {
            capacity_mask: capacity_size - 1,
            capacity_size: capacity_size,
            capacity_bits,
            offset_: 0,
            index_: 0,
        };
        s
    }

    /// Everything `offset`, `offset_at`, `index` and `advance` rely on: the
    /// capacity shape of ProbeSeq.C001, plus the bounds the triple-step maintains
    /// on the two counters (ProbeSeq.C002's offset bound and ProbeSeq.C003's
    /// `index_ % 16 == 0`, `index_ <= capacity_mask + 1`).
    pub open spec fn well_formed(&self) -> bool {
        &&& 4 <= self.capacity_bits <= 31
        &&& self.capacity_mask == slots_for_bits_spec(self.capacity_bits)  // ProbeSeq.C001
        &&& self.capacity_mask + 1 == self.capacity_size
        // `capacity_bits <= 31` is what gives the mask its `2^31 - 1` bound, and a
        // bound is what the `u64 -> usize` narrowing bridge needs: `offset` and
        // `offset_at` cast their result into a `usize` and state it *exactly*,
        // because `lemma_narrow_roundtrip` discharges the round-trip under it.
        // The reference has no such bound, since its `size_t` arithmetic is
        // unchecked; `swisstable-verus-016` / `-025` record what that costs.
        &&& self.capacity_mask <= 0x7FFF_FFFFu64
        &&& self.offset_ <= self.capacity_mask                                // ProbeSeq.C002
        &&& (self.index_ as int) % (GROUP_WIDTH_ as u64 as int) == 0
    }

    /// Upstream's `probe_seq` constructor / `probe_h1`, taking the hash as the
    /// initial value of the sequence.
    pub fn from_capacity_and_h1(&mut self, h1: u64)
        requires self.well_formed(),
        ensures
            final(self).well_formed(),
            final(self).index_ == 0,
            final(self).offset_ == (h1 & final(self).capacity_mask),
            // The constructor fields are not written, so the shape a caller matched
            // against when it built the sequence still holds afterwards.  Stating
            // this is what lets `RawTable::find` carry
            // `seq.capacity_bits == self.capacity_bits` as a loop invariant.
            final(self).capacity_bits == old(self).capacity_bits,
            final(self).capacity_mask == old(self).capacity_mask,
            final(self).capacity_size == old(self).capacity_size,
    {
        self.index_ = 0;
        self.offset_ = h1 & self.capacity_mask;
        proof { lemma_and_below(h1, self.capacity_mask); }
    }

    /// ProbeSeq.C002: the masked offset never leaves the table.
    ///
    /// The postcondition is the *exact* value, not a bound.  An earlier revision
    /// could only state `(offset_ as int) <= capacity_mask`, because it believed
    /// a `u64 -> usize` narrowing cast relates to neither its source nor its bound
    /// in this Verus (`swisstable-verus-016`).  That is true only for the unbounded
    /// cast: under `offset_ <= capacity_mask <= 0x7FFF_FFFF` the round-trip holds,
    /// and `verif/lemmas.rs::lemma_narrow_roundtrip` states it.  `RawTable::find`
    /// depends on the exact value to know the offset is inside the table.
    pub fn offset(&self) -> (r: usize)
        requires self.well_formed(),
        ensures
            r as u64 == self.offset_,                                    // ProbeSeq.C002
            (r as int) <= (self.capacity_mask as int),                    // ProbeSeq.C002
    {
        proof {
            lemma_and_below(self.offset_, self.capacity_mask);
            lemma_narrow_roundtrip(self.offset_);
        }
        self.offset_ as usize
    }

    /// ProbeSeq.C002, applied to a position `i` steps inside the current group.
    pub fn offset_at(&self, i: u64) -> (r: usize)
        requires
            self.well_formed(),
            i <= GROUP_WIDTH_ as u64,
        ensures
            r as u64 == (self.offset_.wrapping_add(i) & self.capacity_mask),  // ProbeSeq.C002
            (r as int) <= (self.capacity_mask as int),                           // ProbeSeq.C002
    {
        let s = self.offset_.wrapping_add(i);
        proof {
            lemma_and_below(s, self.capacity_mask);
            lemma_and_below(s & self.capacity_mask, self.capacity_mask);
            lemma_narrow_roundtrip(s & self.capacity_mask);
        }
        (s & self.capacity_mask) as usize
    }


    /// ProbeSeq.C003: the probe index is a multiple of the group width and never
    /// exceeds the capacity.
    ///
    /// The upper bound is a precondition, not an invariant: upstream's
    /// `index_ += Width` has no cap, and it is the *caller's* group-count loop
    /// that keeps a live sequence inside the table.  See `RawTable::find`.
    pub fn index(&self) -> (r: u64)
        requires
            self.well_formed(),
            self.index_ <= self.capacity_mask + 1,
        ensures
            r == self.index_,
            (r as int) % (GROUP_WIDTH_ as u64 as int) == 0,                        // ProbeSeq.C003
            r <= self.capacity_mask + 1,                                       // ProbeSeq.C003
    {
        self.index_
    }

    /// Upstream `probe_seq::next`.  ProbeSeq.C004.
    pub fn advance(&mut self)
        requires self.well_formed(),
        ensures
            final(self).well_formed(),
            final(self).capacity_bits == old(self).capacity_bits,
            final(self).capacity_mask == old(self).capacity_mask,
            final(self).capacity_size == old(self).capacity_size,
            final(self).index_ == add_u64(old(self).index_, GROUP_WIDTH_ as u64),
            (final(self).index_ as int) % (GROUP_WIDTH_ as u64 as int) == 0,        // ProbeSeq.C003
            // ProbeSeq.C004
            final(self).offset_
                == ((add_u64(add_u64(old(self).offset_, old(self).index_),
                    GROUP_WIDTH_ as u64)) & final(self).capacity_mask),
    {
        proof { lemma_add_group_width_mod(self.index_); }
        self.index_ = self.index_.wrapping_add(GROUP_WIDTH_ as u64);
        let s = self.offset_.wrapping_add(self.index_);
        proof {
            lemma_and_below(s, self.capacity_mask);
            lemma_and_below(s & self.capacity_mask, self.capacity_mask);
        }
        self.offset_ = s & self.capacity_mask;
    }
}

} // verus!
