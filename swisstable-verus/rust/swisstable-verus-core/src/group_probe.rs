//! GroupProbe -- the sixteen-slot window over a control array that answers
//! "which slots here hold my tag", "which are free", "how many are empty".
//!
//! Reference: absl/container/internal/hashtable_control_bytes.h L285-L345
//! (`Group::Match`, `MaskEmptyOrDeleted`, `ConvertSpecialToEmptyAndFullToDeleted`)
//! and raw_hash_set.cc L179 (`GroupFullEmptyOrDeleted`).
//!
//! This is the **scalar** group.  The reference selects `GroupSse2Impl` (16
//! lanes), `GroupAArch64Impl` (8 lanes), or `GroupPortableImpl` (8 lanes),
//! depending on the target.  This port implements scalar 16-wide masks only;
//! issue #36 records the SIMD paths as a scope cut for the current P2 subset.
//! That records the port boundary, not a general Verus/Kani reach result for
//! future intrinsic-based code.  See `findings/limitations.jsonl`
//! (`swisstable-verus-002`, `swisstable-verus-003`).
//!
//! ## The masks are `uint16_t` masks, as the concept spec says
//!
//! Chainlink #30's first attempt replaced them with a 16-element boolean vector
//! on the (incorrect) claim that Verus could not reason about `|`/`<<`/`&`; see
//! `swisstable-verus-014`.  `#[verifier::bit_vector]` lemmas in
//! `verif/lemmas.rs` supply the three facts the loops need, so
//! `match_full`/`match_empty_or_deleted` return `u16` again, exactly as
//! `Group::Match` does.

use crate::control_bytes::{ControlBytes, DELETED, EMPTY, GROUP_WIDTH, SENTINEL};
#[cfg(verus_only)]
use crate::lemmas::{
    lemma_bit_set, lemma_one_hot_fits, lemma_or_preserves_other_bit, lemma_zero_has_no_bit,
};
use vstd::prelude::*;

verus! {

/// Bit `i` of a group mask, read the way the reference's `BitMask` reads it.
/// Bit `i` of a `uint16_t` group mask.  Named with an explicit trigger term so
/// the quantified invariants over a 16-bit mask have one.
pub open spec fn bit_set_at(mask: u16, i: int) -> bool {
    0 <= i < 16 && ((mask >> (i as u32)) & 1u16) == 1u16
}

/// `bit_set_at`, under the name `RawTable` uses.
pub open spec fn bit_i(mask: u16, i: int) -> bool {
    bit_set_at(mask, i)
}

/// `bit_i` as an executable query.  `bit_i` is a specification function, so
/// executable callers go through here; the postcondition is what keeps the two in
/// step.
pub fn bit_set(mask: u16, i: usize) -> (r: bool)
    requires i < 16,
    ensures r == bit_set_at(mask, i as int),
{
    ((mask >> (i as u32)) & 1u16) == 1u16
}

/// No bit of a mask is set outside `[0, 16)`.
pub open spec fn in_range(mask: u16, i: int) -> bool {
    (mask >> (i as u32)) & 1u16 == 0u16
}

/// The scalar implementation of a sixteen-byte group load.
pub struct GroupProbe {
    /// The group's own sixteen control bytes.  GroupProbe.C005: every answer this
    /// struct gives is a function of exactly this window.
    pub window: Vec<u8>,
}

impl GroupProbe {
    /// Window byte at `slot`, readable from specification code.
    ///
    /// **Total by construction**, for the same reason `RawTable::slot_hash` is: a
    /// `recommends` on this accessor made every mention of it inside
    /// `match_full`'s own postcondition a *recommendation* that callers had to
    /// discharge separately, and the discharge needed the very mask fact the
    /// postcondition was stating.  Reading an out-of-window slot as `EMPTY` is not a
    /// weakening: every use site reads a slot under `i < GROUP_WIDTH`, where
    /// `window@.len() == GROUP_WIDTH` and the two forms agree.
    pub open spec fn window_byte(&self, slot: usize) -> u8 {
        if slot < self.window@.len() {
            self.window[slot as int]
        } else {
            EMPTY
        }
    }

    pub fn new() -> (g: Self)
        ensures g.window.len() == GROUP_WIDTH
    {
        let mut window: Vec<u8> = Vec::new();
        let mut i: usize = 0;
        while i < GROUP_WIDTH
            invariant
                i <= GROUP_WIDTH,
                window@.len() == i,
            decreases GROUP_WIDTH - i,
        {
            window.push(0u8);
            i = i + 1;
        }
        GroupProbe { window }
    }

    /// Load the group that starts at control-array index `base`.
    ///
    /// GroupProbe.C001 as drafted states the window bound as
    /// `base + 16 <= capacity`.  That is unreachable for the probe offsets the
    /// reference actually produces: `ProbeSeq` wraps inside `[0, capacity]` and a
    /// `capacity`-sized table ends in the sentinel at index `capacity`, so offsets
    /// in `[capacity - 15, capacity]` load windows that include the sentinel and
    /// the padding -- which is exactly what makes the last group readable and the
    /// sentinel a usable stop condition.  This port therefore implements the
    /// reference's own bound, `base + GROUP_WIDTH <= byte_len()`, which holds for
    /// every offset in `[0, capacity]` because `byte_len() == capacity + 1 +
    /// PAD_BYTES`.  Recorded as `swisstable-spec-002`; C004's "never covers the
    /// sentinel" claim is not restated here because it is false of the reference.
    /// The `usize::MAX` in this function's invariant is the one place in the port that
    /// still needs it: proving `base + i` cannot wrap before it is used as a `Vec`
    /// index does require naming the type's maximum, and this Verus will not.  The
    /// split form (`base <= len`, `GROUP_WIDTH <= len - base`) was tried and does not
    /// discharge the index check.  See `swisstable-verus-018`.
    pub fn load(&mut self, ctrl: &ControlBytes, base: usize)
        requires
            ctrl.well_formed(),
            base + GROUP_WIDTH <= ctrl.bytes@.len(),
        ensures
            final(self).window@.len() == GROUP_WIDTH,
            final(self).window@
                == ctrl.bytes@.subrange(base as int, (base + GROUP_WIDTH) as int),
    {
        self.window.clear();
        let mut i: usize = 0;
        while i < GROUP_WIDTH
            invariant
                i <= GROUP_WIDTH,
                base + GROUP_WIDTH <= ctrl.bytes@.len(),
                base + GROUP_WIDTH <= usize::MAX,
                self.window@.len() == i,
                forall|j: int| 0 <= j < i
                    ==> self.window[j as int] == ctrl.bytes[(base + j) as int],
            decreases GROUP_WIDTH - i,
        {
            self.window.push(ctrl.bytes[base + i]);
            i = i + 1;
        }
    }

    /// GroupProbe.C002: bit `i` is set exactly when slot `base + i` is full and
    /// its tag is `h2`.  This is upstream `Group::Match`, building the mask one
    /// bit at a time instead of with a SIMD movemask.
    pub fn match_full(&self, h2: u8) -> (r: u16)
        requires self.window.len() == GROUP_WIDTH,
        ensures
            forall|i: int| 0 <= i < 16
                ==> bit_set_at(r, i) == (self.window_byte(i as usize) <= 0x7F
                    && self.window_byte(i as usize) == h2),
            // The same fact over `window@` directly.  `window_byte` is total, so
            // the two agree under `window@.len() == GROUP_WIDTH`, and a caller that
            // holds the window as a `Seq` (as `RawTable::find` does, to compare it
            // against the control array) needs *this* form to instantiate against --
            // `lemma_mask_bit_at` below is phrased in exactly these terms.
            forall|i: int| 0 <= i < 16
                ==> bit_set_at(r, i) == (self.window@[i] <= 0x7F && self.window@[i] == h2),
    {
        let mut mask: u16 = 0;
        assert forall|j: int| #![trigger bit_set_at(0u16, j)]
            0 <= j < 16 implies !bit_set_at(0u16, j) by {
            lemma_zero_has_no_bit(j as u32);
        }
        let mut i: usize = 0;
        while i < GROUP_WIDTH
            invariant
                i <= GROUP_WIDTH,
                self.window@.len() == GROUP_WIDTH,
                forall|j: int| 0 <= j < 16
                    ==> bit_set_at(mask, j)
                        == (j < i as int && self.window_byte(j as usize) <= 0x7F
                            && self.window_byte(j as usize) == h2),
            decreases GROUP_WIDTH - i,
        {
            proof { lemma_one_hot_fits(i as u32); }
            let mut nm: u16 = mask;
            if self.window[i] <= 0x7F && self.window[i] == h2 {
                nm = mask | (1u16 << (i as u32));
            }
            proof {
                lemma_bit_set(mask, i as u32);
                assert forall|j: int| 0 <= j < 16 && j != i as int implies
                    bit_set_at(nm, j) == bit_set_at(mask, j) by {
                    if nm != mask {
                        assert(nm == mask | (1u16 << (i as u32)));
                        lemma_or_preserves_other_bit(mask, i as u32, j as u32);
                    }
                }
            }
            assert forall|j: int| #![trigger bit_set_at(nm, j)]
                0 <= j < 16
                implies bit_set_at(nm, j)
                    == (j < i as int + 1
                        && self.window_byte(j as usize) <= 0x7F
                        && self.window_byte(j as usize) == h2) by {
                if j < i as int {
                    assert(bit_set_at(nm, j) == bit_set_at(mask, j));
                }
            }
            mask = nm;
            i = i + 1;
        }
        mask
    }

    /// GroupProbe.C003: bit `i` is set exactly when slot `base + i` is empty or
    /// deleted -- both states set the free bit, which is what a steady state after
    /// an erase needs.  This is upstream `Group::MaskEmptyOrDeleted`.
    pub fn match_empty_or_deleted(&self) -> (r: u16)
        requires self.window.len() == GROUP_WIDTH,
        ensures
            forall|i: int| 0 <= i < 16
                ==> bit_set_at(r, i) == (self.window_byte(i as usize) == EMPTY
                    || self.window_byte(i as usize) == DELETED),
    {
        let mut mask: u16 = 0;
        assert forall|j: int| #![trigger bit_set_at(0u16, j)]
            0 <= j < 16 implies !bit_set_at(0u16, j) by {
            lemma_zero_has_no_bit(j as u32);
        }
        let mut i: usize = 0;
        while i < GROUP_WIDTH
            invariant
                i <= GROUP_WIDTH,
                self.window@.len() == GROUP_WIDTH,
                forall|j: int| 0 <= j < 16
                    ==> bit_set_at(mask, j)
                        == (j < i as int && (self.window_byte(j as usize) == EMPTY
                            || self.window_byte(j as usize) == DELETED)),
            decreases GROUP_WIDTH - i,
        {
            proof { lemma_one_hot_fits(i as u32); }
            let mut nm: u16 = mask;
            if self.window[i] == EMPTY || self.window[i] == DELETED {
                nm = mask | (1u16 << (i as u32));
            }
            proof {
                lemma_bit_set(mask, i as u32);
                assert forall|j: int| 0 <= j < 16 && j != i as int implies
                    bit_set_at(nm, j) == bit_set_at(mask, j) by {
                    if nm != mask {
                        assert(nm == mask | (1u16 << (i as u32)));
                        lemma_or_preserves_other_bit(mask, i as u32, j as u32);
                    }
                }
            }
            assert forall|j: int| #![trigger bit_set_at(nm, j)]
                0 <= j < 16
                implies bit_set_at(nm, j)
                    == (j < i as int + 1
                        && (self.window_byte(j as usize) == EMPTY
                            || self.window_byte(j as usize) == DELETED)) by {
                if j < i as int {
                    assert(bit_set_at(nm, j) == bit_set_at(mask, j));
                }
            }
            mask = nm;
            i = i + 1;
        }
        mask
    }

    /// The number of empty (never-full) slots in this group.
    pub fn count_empty(&self) -> (r: usize)
        requires self.window.len() == GROUP_WIDTH,
        ensures r as nat == self.count_empty_prefix(GROUP_WIDTH as nat)
    {
        let mut n: usize = 0;
        let mut i: usize = 0;
        while i < GROUP_WIDTH
            invariant
                i <= GROUP_WIDTH,
                n <= i,
                self.window@.len() == GROUP_WIDTH,
                n as nat == self.count_empty_prefix(i as nat),
            decreases GROUP_WIDTH - i,
        {
            if self.window[i] == EMPTY {
                n = n + 1;
            }
            i = i + 1;
        }
        n
    }

    pub open spec fn count_empty_prefix(&self, n: nat) -> nat
        recommends n <= GROUP_WIDTH
        decreases n
    {
        if n == 0 {
            0
        } else {
            self.count_empty_prefix((n - 1) as nat)
                + if self.window[(n - 1) as int] == EMPTY { 1nat } else { 0nat }
        }
    }

    /// `SENTINEL` never sets the free bit, so a group whose only non-full bytes
    /// are the sentinel terminates a probe run.
    pub proof fn lemma_sentinel_is_not_free(w: &Vec<u8>)
        requires
            w.len() == GROUP_WIDTH,
        ensures
            forall|i: int| 0 <= i < 16 && w[i] == SENTINEL
                ==> !(w[i] == EMPTY || w[i] == DELETED),
    {
    }
}

/// `match_full`'s answer at one index, read off the window sequence.
///
/// Free function over `Seq<u8>` rather than a method, for two reasons.
///
/// First, `match_full`'s own `ensures` cannot be instantiated at a caller's
/// `usize` index on its own: the quantifier is over `int`, its trigger is
/// `bit_set_at(r, i)`, and the *other* side is a window term the caller has not yet
/// introduced.  Second, taking the window as a `Seq` rather than as
/// `&GroupProbe` removes the receiver from the formula on both sides, so the
/// caller's copy of `match_full`'s postcondition (which mentions `g.window`) and
/// this lemma's precondition (which mentions the `Seq`) still need the same
/// substitution -- so the caller states the precondition itself, which is a fact
/// it already has from `GroupProbe::load`.
pub proof fn lemma_mask_bit_at(window: Seq<u8>, mask: u16, h2: u8, i: int)
    requires
        window.len() == GROUP_WIDTH as int,
        0 <= i < 16,
        forall|j: int| 0 <= j < 16
            ==> bit_set_at(mask, j)
                == (window[j] <= 0x7F && window[j] == h2),
    ensures bit_set_at(mask, i) <==> (window[i] <= 0x7F && window[i] == h2),
{
    assert forall|j: int| 0 <= j < 16
        implies bit_set_at(mask, j)
            == (window[j] <= 0x7F && window[j] == h2) by {
    }
}

} // verus!
