//! ControlBytes -- one control byte per slot, plus the sentinel and the padding
//! that makes the trailing group loadable.
//!
//! Reference: absl/container/internal/hashtable_control_bytes.h L184-L230
//! (`enum class ctrl_t`, `IsEmpty`, `IsFull`, `IsDeleted`, `IsEmptyOrDeleted`)
//! and raw_hash_set.cc L434-L447 (`ConvertDeletedToEmptyAndFullToDeleted`).
//!
//! Upstream stores `ctrl_t` as an `int8_t`:
//!
//! ```text
//!   kEmpty    = -128 = 0x80
//!   kDeleted  =    -2 = 0xFE
//!   kSentinel =    -1 = 0xFF
//!   IsFull(c)           <=> (int8_t)c >= 0      <=> byte <= 0x7F
//!   IsEmptyOrDeleted(c) <=> c < kSentinel        <=> byte >= 0x80 && byte != 0xFF
//! ```
//!
//! This port keeps the same byte encoding, so `u8` rather than `i8` is the
//! representation and the tests keep the reference's exact truth values.  A
//! full byte carries its tag in its low seven bits, which is why a tag of zero
//! is a legal full byte and not an empty one.

use vstd::prelude::*;

verus! {

/// `ctrl_t::kEmpty`, the byte of a slot that was never full.
pub const EMPTY: u8 = 0x80;
/// `ctrl_t::kDeleted`, the tombstone byte.
pub const DELETED: u8 = 0xFE;
/// `ctrl_t::kSentinel`, the stop byte that sits at index `capacity`.
pub const SENTINEL: u8 = 0xFF;
/// `Group::kWidth`, the scalar group width this port probes with.
pub const GROUP_WIDTH: usize = 16;
/// Upstream's `kNumPaddingBytes`; `NumControlBytes == capacity + kWidth` with
/// `capacity == NumSlots + 1`, so a sixteen-byte group load at any slot index in
/// `[0, capacity]` stays inside the array.
pub const PAD_BYTES: usize = GROUP_WIDTH;

// ---- counting over a control-byte sequence ---------------------------------
//
// Free spec functions over the `Seq` view rather than methods, so the counting
// lemmas in `verif/lemmas.rs` can talk about two different control arrays -- the
// one before a `clear_dead` and the one after it -- without `old()`.

pub open spec fn seq_full_count(s: Seq<u8>, n: nat) -> nat
    recommends n <= s.len()
    decreases n
{
    if n == 0 {
        0
    } else {
        seq_full_count(s, (n - 1) as nat) + (if s[((n - 1) as nat) as int] as int <= 127 {
            1nat
        } else {
            0nat
        })
    }
}

pub open spec fn seq_dead_count(s: Seq<u8>, n: nat) -> nat
    recommends n <= s.len()
    decreases n
{
    if n == 0 {
        0
    } else {
        seq_dead_count(s, (n - 1) as nat) + (if s[((n - 1) as nat) as int] == DELETED {
            1nat
        } else {
            0nat
        })
    }
}

pub open spec fn seq_empty_count(s: Seq<u8>, n: nat) -> nat
    recommends n <= s.len()
    decreases n
{
    if n == 0 {
        0
    } else {
        seq_empty_count(s, (n - 1) as nat) + (if s[((n - 1) as nat) as int] == EMPTY {
            1nat
        } else {
            0nat
        })
    }
}

pub open spec fn seq_free_count(s: Seq<u8>, n: nat) -> nat
    recommends n <= s.len()
    decreases n
{
    if n == 0 {
        0
    } else {
        seq_free_count(s, (n - 1) as nat) + (if s[((n - 1) as nat) as int] == EMPTY
            || s[((n - 1) as nat) as int] == DELETED { 1nat } else { 0nat })
    }
}

// ---- `WasNeverFull` (raw_hash_set.cc L708-L724) --------------------------
//
// Upstream:
//
//   bool WasNeverFull(CommonFields& c, size_t index) {
//     if (is_single_group(c.capacity())) return true;
//     const size_t index_before = (index - Group::kWidth) & c.capacity();
//     const auto empty_after  = Group(c.control() + index).MaskEmpty();
//     const auto empty_before = Group(c.control() + index_before).MaskEmpty();
//     return empty_before && empty_after &&
//            empty_after.TrailingZeros() + empty_before.LeadingZeros() < Group::kWidth;
//   }
//
// `MaskEmpty` sets bit `i` iff the byte is `kEmpty`
// (hashtable_control_bytes.h L379), `TrailingZeros` is the index of the *lowest*
// set bit (L95) and `LeadingZeros` the index of the *highest* (L100).  So
// `empty_after.TrailingZeros()` is the length of the run of non-empty bytes
// starting at `index` inside that window, and `empty_before.LeadingZeros()` is
// the offset, from the *end* of the before-window, of its last empty byte --
// which is `15 - (the run of non-empty bytes ending at index-1)`.  The bound is
// therefore "the forward run is no longer than the backward run", plus the two
// windows each having an empty byte in them.  That is the form below, written
// over the raw control bytes instead of a `uint16_t` group mask so that it is a
// counting recursion the SMT can step.
//
// An earlier revision of this port recorded `swisstable-verus-021` as "upstream
// reads `WasNeverFull` from a `growth_info()` field this port has no field for".
// That is wrong for the pinned checkout: `growth_info()` appears on the two lines
// *after* the branch decision (`EraseMetaOnlyLarge`, raw_hash_set.cc L876/L882),
// and only feeds growth-left accounting.  `WasNeverFull` itself reads nothing but
// the control bytes, so the port implements it.

/// Control index `i`, wrapped into `[0, capacity]` the way `(x - Width) &
/// capacity` wraps: `kNumSlots + 1 == capacity + 1` is the modulus.
pub open spec fn wrap_index(cap: int, i: int) -> int {
    if i < 0 { i + cap + 1 } else { i }
}

/// The length of the run of non-`kEmpty` control bytes starting at `start` and
/// reading forward through the `n`-byte group window.  Upstream's
/// `empty_after.TrailingZeros()`, or `n` when the window holds no empty byte.
pub open spec fn empty_run_forward(s: Seq<u8>, start: int, n: nat) -> nat
    recommends
        0 <= start,
        start + n as int <= s.len(),
    decreases n
{
    if n == 0 {
        0
    } else {
        let prev = empty_run_forward(s, start, (n - 1) as nat);
        if prev < (n - 1) as nat {
            prev
        } else if s[start + (n - 1) as int] == EMPTY {
            (n - 1) as nat
        } else {
            prev + 1
        }
    }
}

/// The length of the run of non-`kEmpty` control bytes ending at `start - 1` and
/// reading backward through the `n`-byte group window.  This is upstream's
/// `15 - empty_before.LeadingZeros()`.
pub open spec fn empty_run_backward(s: Seq<u8>, cap: int, start: int, n: nat) -> nat
    recommends
        cap >= GROUP_WIDTH as int,
        0 <= start <= cap,
        n <= GROUP_WIDTH as nat,
        s.len() >= cap + 1,
    decreases n
{
    if n == 0 {
        0
    } else {
        let prev = empty_run_backward(s, cap, start, (n - 1) as nat);
        if prev < (n - 1) as nat {
            prev
        } else if s[wrap_index(cap, start - n as int)] == EMPTY {
            (n - 1) as nat
        } else {
            prev + 1
        }
    }
}

/// Both runs are bounded by the window they are read over, which is what makes
/// `fwd < GROUP_WIDTH` mean "this window holds an empty byte".
pub proof fn lemma_empty_run_forward_le(s: Seq<u8>, start: int, n: nat)
    requires
        0 <= start,
        start + n as int <= s.len(),
    ensures empty_run_forward(s, start, n) <= n,
    decreases n
{
    if n > 0 {
        lemma_empty_run_forward_le(s, start, (n - 1) as nat);
    }
}

/// One step of `empty_run_forward`, as its own lemma.
///
/// The recursion does not unfold inside the counting loop's invariant on its own:
/// the loop increments `n` and the invariant mentions `empty_run_forward(..., n)`,
/// and Verus will not connect the two without the step being stated.  Naming it
/// here is the same treatment `lemma_dead_count_eq_full_count` gets, for the same
/// reason.
pub proof fn lemma_empty_run_forward_step(s: Seq<u8>, start: int, n: nat)
    requires
        0 <= start,
        start + (n + 1) as int <= s.len(),
    ensures empty_run_forward(s, start, n + 1)
        == (if empty_run_forward(s, start, n) < n {
            empty_run_forward(s, start, n)
        } else if s[start + n as int] == EMPTY {
            n
        } else {
            empty_run_forward(s, start, n) + 1
        }),
{
}

pub proof fn lemma_empty_run_backward_le(s: Seq<u8>, cap: int, start: int, n: nat)
    requires
        cap >= GROUP_WIDTH as int,
        0 <= start <= cap,
        n <= GROUP_WIDTH as nat,
        s.len() >= cap + 1,
    ensures empty_run_backward(s, cap, start, n) <= n,
    decreases n
{
    if n > 0 {
        lemma_empty_run_backward_le(s, cap, start, (n - 1) as nat);
    }
}

/// The branch-free form of `(index - 1 - m) & capacity` used by the backward run.
///
/// Upstream computes `index_before = (index - Group::kWidth) & c.capacity()` and
/// then walks *forward* from there; this port walks *backward* from `index - 1`, which
/// is the same window read in the opposite direction and reaches the same last-empty
/// byte.  `wrap_index` is the specification form of the `& capacity_`; this lemma
/// relates the two, so the executable branch below does not have to.
pub proof fn lemma_wrapped_index(index: usize, capacity: usize, m: usize)
    requires
        0 <= index as int,
        index as int <= capacity as int,
        capacity >= GROUP_WIDTH,
        capacity <= 0x7FFF_FFFFusize,
        m < GROUP_WIDTH,
    ensures
        (if index >= m + 1 { index - (m + 1) }
         else { index + capacity + 1 - (m + 1) }) as int
            == wrap_index(capacity as int, index as int - (m + 1) as int),
{
    let ghost i = index as int;
    let ghost c = capacity as int;
    let ghost d = m as int + 1;
    if index >= m + 1 {
        assert(i - d >= 0);
        assert((index - (m + 1)) as int == i - d);
    } else {
        assert(i < d);
        assert(c >= GROUP_WIDTH as int);
        assert((index + capacity + 1 - (m + 1)) as int == i + c + 1 - d);
    }
}

/// One step of `empty_run_backward`; see `lemma_empty_run_forward_step`.
pub proof fn lemma_empty_run_backward_step(s: Seq<u8>, cap: int, start: int, n: nat)
    requires
        cap >= GROUP_WIDTH as int,
        0 <= start <= cap,
        n <= GROUP_WIDTH as nat,
        s.len() >= cap + 1,
    ensures empty_run_backward(s, cap, start, n + 1)
        == (if empty_run_backward(s, cap, start, n) < n {
            empty_run_backward(s, cap, start, n)
        } else if s[wrap_index(cap, start - (n + 1) as int)] == EMPTY {
            n
        } else {
            empty_run_backward(s, cap, start, n) + 1
        }),
{
}

/// Upstream `WasNeverFull`, over the raw control array: `cap <= GROUP_WIDTH` is
/// `is_single_group` (raw_hash_set.h L404-L406), and the conjunction is
/// `empty_before && empty_after &&
///      empty_after.TrailingZeros() + empty_before.LeadingZeros() < Group::kWidth`
/// (raw_hash_set.cc L718-L724).
///
/// The two masks' bit operations are *counts of non-empty bytes*, which is what
/// `empty_run_forward` / `empty_run_backward` are:
///
/// * `Group(c.control() + index).MaskEmpty()` sets abstract bit `a` exactly when
///   `ctrl[index + a] == kEmpty` (`MoveMask` puts each byte's MSB at that byte's
///   index), so `TrailingZeros()` is the number of consecutive non-empty bytes
///   starting at `index` -- `fwd`, capped at `kWidth`;
/// * `Group(c.control() + index_before).MaskEmpty()` with
///   `index_before = (index - Group::kWidth) & c.capacity()` sets bit `b` exactly
///   when `ctrl[index_before + b] == kEmpty`, so bit 15 is `ctrl[index - 1]` and
///   `LeadingZeros()` -- `countl_zero(mask << 16)` over the 16-bit mask
///   (`NonIterableBitMask`, hashtable_control_bytes.h L100-L104) -- is the number
///   of leading *zero* abstract bits, i.e. the number of consecutive non-empty
///   bytes ending at `index - 1` -- `bwd`, capped at `kWidth`.
///
/// So upstream's test is `fwd + bwd < kWidth`, **not** a comparison between the
/// two runs.  An earlier revision of this port transcribed it as
/// `fwd < 16 && bwd < 16 && fwd <= bwd`, which is wrong in both directions: with
/// 16 consecutive full slots around `index` (`bwd == 15`, `fwd == 1`) upstream
/// sums to `kWidth` and writes `kDeleted` -- the case its own comment describes,
/// "at least one probe window that might have seen a full group" -- while `1 <= 15`
/// would have said `kEmpty`; and with `bwd == 1`, `fwd == 3` upstream writes
/// `kEmpty` while `3 <= 1` says `kDeleted`.  The port's comment also carried the
/// derivation error as prose (`fwd + (15 - bwd) < 16`).  See
/// `swisstable-verus-021`.
pub open spec fn was_never_full_in(s: Seq<u8>, cap: int, index: int) -> bool
    recommends
        cap >= GROUP_WIDTH as int,
        s.len() >= cap + 1 + GROUP_WIDTH as int,
        0 <= index < cap,
{
    let fwd = empty_run_forward(s, index, GROUP_WIDTH as nat);
    let bwd = empty_run_backward(s, cap, index, GROUP_WIDTH as nat);
    &&& cap <= GROUP_WIDTH as int
    || (fwd < GROUP_WIDTH as nat
        && bwd < GROUP_WIDTH as nat
        && fwd + bwd < GROUP_WIDTH as nat)
}

/// "Byte `i` of the raw array is empty-or-deleted", over a `Seq<u8>` rather than
/// over a `ControlBytes`.
///
/// The counting lemmas in `verif/lemmas.rs` talk about two different control arrays
/// -- the one before a `clear_dead` and the one after it -- and need the predicate
/// without a receiver.  This is the free-function form of
/// `ControlBytes::is_empty_or_deleted_spec`.
///
/// The index is `int` and not `usize` **on purpose**.  An earlier revision of this
/// port added a `usize`-indexed twin `free_at` and restated `has_free_slot` and
/// `claim_first_free`'s precondition as `usize` existentials, to bridge the
/// `usize`-quantified loop invariants of the two linear scans.  That bridge has to
/// be paid for twice over: Verus leaves `i as usize` opaque in *both* directions,
/// so the counting lemmas (`lemma_zero_free_gives_not_has_free`,
/// `lemma_positive_free_gives_has_free`) state the `int` form and cannot produce
/// the `usize` form at all -- `RawTable::is_full` and `RawTable::insert` each
/// needed a second, duplicated lemma that existed only to cross the cast.  Stating
/// the scans' invariants in the `int` form instead (with the scan cursor cast once,
/// on the bound, not on the predicate) removes the bridge from both ends.  See
/// `swisstable-verus-028`.
pub open spec fn is_empty_or_deleted_in(s: Seq<u8>, i: int) -> bool {
    s[i] == EMPTY || s[i] == DELETED
}

pub struct ControlBytes {
    /// The raw control array: `[0, capacity)` are slots, `capacity` is the
    /// sentinel, and `[capacity + 1, len)` is `GROUP_WIDTH` bytes of padding.
    pub bytes: Vec<u8>,
    /// `NumSlots`: the number of real slots, `2^k - 1`.
    pub capacity: usize,
}

impl ControlBytes {
    /// A fresh, entirely empty control array of `capacity` slots followed by the
    /// sentinel and the padding.
    /// The upper bound is a literal rather than `usize::MAX`, because this Verus
    /// will not name `usize::MAX` at all: `usize::MAX as u64` is neither `0xFFFF_FFFF`
    /// nor `0xFFFF_FFFF_FFFF_FFFF`, so a precondition written with it can never be
    /// discharged.  `0x7FFF_FFFF` is the same figure `slots_for_bits` already
    /// guarantees, so nothing is given up.  See `swisstable-verus-018`.
    pub fn new(capacity: usize) -> (c: Self)
        requires
            capacity >= GROUP_WIDTH,
            capacity <= 0x7FFF_FFFFusize,
        ensures
            c.well_formed(),
            c.capacity == capacity,
            // A fresh array is empty *everywhere*, which is more than `well_formed`
            // says; `RawTable::new`'s element-count postcondition needs it.
            forall|i: int| 0 <= i < capacity ==> c.bytes[i] == EMPTY,
            // index `capacity` is the sentinel, so the padding starts after it
            forall|i: int| capacity < i < c.bytes@.len() ==> c.bytes[i] == EMPTY,
    {
        let len = capacity + 1 + PAD_BYTES;
        let mut bytes: Vec<u8> = Vec::new();
        let mut i: usize = 0;
        while i < len
            invariant
                i <= len,
                bytes@.len() == i,
                forall|j: usize| j < i ==> bytes[j as int] == EMPTY,
            decreases len - i,
        {
            bytes.push(EMPTY);
            i = i + 1;
        }
        bytes[capacity] = SENTINEL;
        let c = ControlBytes { bytes, capacity };
        c
    }

    /// `NumControlBytes`.  ControlBytes.C002's `capacity < byte_len`.
    pub fn byte_len(&self) -> (r: usize)
        ensures r == self.bytes.len()
    {
        self.bytes.len()
    }

    /// The shape every operation here relies on: the sentinel is exactly at
    /// index `capacity`, no real slot holds it, and the trailing padding is all
    /// empty.
    pub open spec fn well_formed(&self) -> bool {
        let cap = self.capacity as int;
        let blen = self.bytes@.len();
        &&& self.bytes.len() == self.capacity + 1 + PAD_BYTES
        &&& self.capacity >= GROUP_WIDTH
        // The literal upper bound `ControlBytes::new` already required, carried as
        // an invariant.  It is what makes the `u64 -> usize` narrowing bridge in
        // `verif/lemmas.rs` (`lemma_narrow_roundtrip`) applicable, and therefore
        // what lets `RawTable::model` state the capacity shape on the table's own
        // `usize` capacity at all.  See `swisstable-verus-016` / `-025`.
        &&& self.capacity <= 0x7FFF_FFFFusize
        &&& self.bytes[cap] == SENTINEL
        // Every real slot holds one of exactly three things: an h2 tag (`<= 0x7F`),
        // a tombstone, or an empty marker.  Upstream also has `kDeleted2`, which
        // this port does not use.  Stating the classification is what lets
        // `lemma_not_free_gives_full` turn "not empty-or-deleted" into "full"
        // without a second unfold, and it is what `clear_dead` maintains.
        &&& (forall|i: int| 0 <= i < cap ==> {
            self.bytes[i] <= 0x7F
                || self.bytes[i] == crate::control_bytes::DELETED
                || self.bytes[i] == crate::control_bytes::EMPTY
        })
        &&& (forall|i: int| cap < i < blen ==> self.bytes[i] == EMPTY)
    }

    /// The control byte at `slot`, readable from specification code.  Spec
    /// contexts index a `Vec` with an `int`, so every spec-facing read goes
    /// through here rather than casting at each use site.
    pub open spec fn slot_byte(&self, slot: usize) -> u8
        recommends self.well_formed(), slot < self.bytes@.len()
    {
        self.bytes[slot as int]
    }

    pub fn byte(&self, slot: usize) -> (r: u8)
        requires
            self.well_formed(),
            slot < self.bytes.len(),
        ensures r == self.bytes[slot as int]
    {
        self.bytes[slot]
    }

    // ---- slot-state queries, ControlBytes.C001 -----------------------------
    //
    // C001 as drafted reads "every control byte holds one of empty, deleted,
    // the sentinel, or a full byte whose low seven bits are its slot tag".  On
    // a `u8` byte the first half is a tautology, so what is proved and relied on
    // is the second half: a full byte carries its tag in its low seven bits,
    // which is what makes `is_full` and `tag` agree and what makes a zero tag a
    // legal full byte.

    pub open spec fn is_full_spec(&self, slot: int) -> bool {
        self.bytes[slot] <= 0x7F
    }

    pub open spec fn is_empty_spec(&self, slot: int) -> bool {
        self.bytes[slot] == EMPTY
    }

    pub open spec fn is_dead_spec(&self, slot: int) -> bool {
        self.bytes[slot] == DELETED
    }

    pub open spec fn is_empty_or_deleted_spec(&self, slot: int) -> bool {
        self.bytes[slot] == EMPTY || self.bytes[slot] == DELETED
    }

    /// The pointwise statement `clear_dead` maintains, as one named specification
    /// function so that the loop invariant and the quantifier that extends it can be
    /// given the *same* trigger term.  Two quantifiers over the same body with
    /// differently inferred triggers do not instantiate against each other.
    pub open spec fn reclaimed(before: Seq<u8>, after: Seq<u8>, slot: int) -> bool
        recommends 0 <= slot < before.len() && 0 <= slot < after.len()
    {
        &&& (after[slot] == DELETED <==> before[slot] <= 0x7F)
        &&& (before[slot] == DELETED ==> after[slot] == EMPTY)
        &&& (before[slot] == EMPTY ==> after[slot] == EMPTY)
    }

    pub fn is_empty(&self, slot: usize) -> (r: bool)
        requires
            self.well_formed(),
            slot < self.capacity,
        ensures r == self.is_empty_spec(slot as int)
    {
        self.bytes[slot] == EMPTY
    }

    pub fn is_dead(&self, slot: usize) -> (r: bool)
        requires
            self.well_formed(),
            slot < self.capacity,
        ensures r == self.is_dead_spec(slot as int)
    {
        self.bytes[slot] == DELETED
    }

    pub fn is_full(&self, slot: usize) -> (r: bool)
        requires
            self.well_formed(),
            slot < self.capacity,
        ensures r == self.is_full_spec(slot as int)
    {
        self.bytes[slot] <= 0x7F
    }

    /// Upstream `IsEmptyOrDeleted` is `c < kSentinel`, i.e. "the MSB is set but
    /// the byte is not the sentinel".  ControlBytes.C002 is what makes the second
    /// half true of every real slot: only index `capacity` is the sentinel.
    pub fn is_empty_or_deleted(&self, slot: usize) -> (r: bool)
        requires
            self.well_formed(),
            slot < self.capacity,
        ensures r == self.is_empty_or_deleted_spec(slot as int)
    {
        let b = self.bytes[slot];
        b == EMPTY || b == DELETED
    }

    /// ControlBytes.C007: the tag read back from a full slot is the tag that was
    /// written into it -- the low seven bits, verbatim.
    pub fn tag(&self, slot: usize) -> (r: u8)
        requires
            self.well_formed(),
            slot < self.capacity,
            self.is_full_spec(slot as int),
        ensures r == self.bytes[slot as int],
    {
        self.bytes[slot]
    }

    /// `ControlBytes::count_empty`; the query the staged witness spec
    /// `control_bytes.count_empty` describes.
    pub fn count_empty(&self) -> (r: usize)
        requires self.well_formed(),
        ensures r as nat == seq_empty_count(self.bytes@, self.capacity as nat)
    {
        let mut n: usize = 0;
        let mut i: usize = 0;
        while i < self.capacity
            invariant
                i <= self.capacity,
                n <= i,
                self.bytes@.len() == self.capacity + 1 + PAD_BYTES,
                n as nat == seq_empty_count(self.bytes@, i as nat),
            decreases self.capacity - i,
        {
            if self.bytes[i] == EMPTY {
                n = n + 1;
            }
            i = i + 1;
        }
        n
    }

    /// The number of tombstoned slots in `[0, n)`.
    pub open spec fn count_dead_prefix(&self, n: nat) -> nat
        recommends
            self.well_formed(),
            n <= self.capacity as nat,
    {
        seq_dead_count(self.bytes@, n)
    }

    // ---- `WasNeverFull`, the erase rule ----------------------------------

    /// Upstream `WasNeverFull(c, index)`, as a specification predicate.
    pub open spec fn was_never_full_spec(&self, index: int) -> bool
        recommends
            self.well_formed(),
            0 <= index < self.capacity as int,
    {
        was_never_full_in(self.bytes@, self.capacity as int, index)
    }

    /// Upstream `WasNeverFull` (raw_hash_set.cc L708-L724), used by
    /// `RawTable::erase` to choose between `kEmpty` and `kDeleted`.
    ///
    /// The two windows are read straight out of the control bytes rather than
    /// through `GroupProbe`: upstream's `Group(c.control() + index).MaskEmpty()`
    /// is a SIMD load whose `TrailingZeros`/`LeadingZeros` this port reads as the
    /// two counting recursions above, so the *bytes* consulted are identical.  The
    /// window is raw, not modular: `c.control() + index` for `index <= capacity`
    /// already runs into the sentinel and the padding, which is how the reference
    /// sees them too, and the padding is `kEmpty` so it terminates the forward run
    /// exactly as it does there.
    pub fn was_never_full(&self, index: usize) -> (r: bool)
        requires
            self.well_formed(),
            index < self.capacity,
        ensures r == self.was_never_full_spec(index as int)
    {
        // `is_single_group(c.capacity())`, raw_hash_set.cc L709-L711: a table that
        // fits inside one probing group is trivially "never full".
        if self.capacity <= GROUP_WIDTH {
            return true;
        }
        proof {
            assert(self.capacity > GROUP_WIDTH);
            assert(self.capacity >= GROUP_WIDTH);
            assert(self.bytes@.len() == self.capacity + 1 + PAD_BYTES);
        }
        let ghost start = index as int;
        let ghost cap = self.capacity as int;
        proof { assert(start + GROUP_WIDTH as int <= self.bytes@.len()); }
        // `empty_after.TrailingZeros()`: the forward run over the group window.
        let mut fwd: usize = 0;
        let mut n: usize = 0;
        while n < GROUP_WIDTH
            invariant
                0 <= start,
                start + GROUP_WIDTH as int <= self.bytes@.len(),
                n <= GROUP_WIDTH,
                start + n as int <= self.bytes@.len(),
                (start + n as int) as usize == index + n,
                (start + n as int) as usize <= self.bytes.len(),
                self.well_formed(),
                fwd <= n,
                (fwd as nat) == empty_run_forward(self.bytes@, start, n as nat),
            decreases GROUP_WIDTH - n
        {
            proof {
                lemma_empty_run_forward_le(self.bytes@, start, n as nat);
                lemma_empty_run_forward_step(self.bytes@, start, n as nat);
            }
            let at = index + n;
            let is_empty = self.bytes[at] == EMPTY;
            proof {
                assert(at as int == start + n as int);
                assert(is_empty <==> self.bytes@[at as int] == EMPTY);
            }
            if fwd == n {
                if is_empty {
                    fwd = n;
                } else {
                    fwd = fwd + 1;
                }
            }
            n = n + 1;
            proof { assert(fwd as nat == empty_run_forward(self.bytes@, start, n as nat)); }
        }
        // `empty_before.LeadingZeros()`: the backward run ending at `index - 1`,
        // over the window `[(index - 16) & capacity, index)`.
        let mut bwd: usize = 0;
        let mut m: usize = 0;
        while m < GROUP_WIDTH
            invariant
                cap >= GROUP_WIDTH as int,
                0 <= start <= cap,
                index <= self.capacity,
                start == index as int,
                cap == self.capacity as int,
                self.capacity <= 0x7FFF_FFFFusize,
                cap + 1 <= self.bytes@.len(),
                // `m <= GROUP_WIDTH`, which is what keeps the wrap arithmetic in
                // `raw` from running past one modulus step (at `m == 15` the step
                // is `m + 1 == 16`, exactly the window width).
                m <= GROUP_WIDTH,
                bwd <= m,
                self.well_formed(),
                (bwd as nat) == empty_run_backward(self.bytes@, cap, start, m as nat),
            decreases GROUP_WIDTH - m
        {
            proof {
                lemma_empty_run_backward_le(self.bytes@, cap, start, m as nat);
                lemma_empty_run_backward_step(self.bytes@, cap, start, m as nat);
                assert(0 <= start && start <= cap);
                assert(m <= GROUP_WIDTH);
            }
            // `(index - 1 - m) & capacity` (= `wrap_index(cap, index - 1 - m)`),
            // computed without letting the subtraction wrap: `index >= 1` whenever
            // the wrap is needed, and `capacity >= GROUP_WIDTH` keeps the else
            // branch non-negative.
            let raw = if index >= m + 1 {
                index - (m + 1)
            } else {
                index + self.capacity + 1 - (m + 1)
            };
            proof {
                lemma_wrapped_index(index, self.capacity, m);
                assert(raw as int == wrap_index(cap, start - (m + 1) as int));
                assert(raw < self.bytes.len());
            }
            let is_empty = self.bytes[raw] == EMPTY;
            proof { assert(is_empty <==> self.bytes@[raw as int] == EMPTY); }
            if bwd == m {
                if is_empty {
                    bwd = m;
                } else {
                    bwd = bwd + 1;
                }
            }
            m = m + 1;
            proof {
                assert(bwd as nat == empty_run_backward(self.bytes@, cap, start, m as nat));
            }
        }
        // Upstream's whole test, verbatim (raw_hash_set.cc L718-L724):
        //   empty_before && empty_after &&
        //   empty_after.TrailingZeros() + empty_before.LeadingZeros() < Group::kWidth
        // which is `fwd < 16 && bwd < 16 && fwd + bwd < 16`.
        let r = fwd < GROUP_WIDTH && bwd < GROUP_WIDTH
            && fwd + bwd < GROUP_WIDTH;
        proof { assert(r == self.was_never_full_spec(start)); }
        r
    }

    // ---- control-byte writes ----------------------------------------------

    /// Upstream `SetCtrlToFull`: mark the slot full and write its tag.
    pub fn set_full(&mut self, slot: usize, h2: u8)
        requires
            self.well_formed(),
            slot < self.capacity,
            h2 <= 0x7F,
        ensures
            final(self).well_formed(),
            final(self).bytes[slot as int] == h2,
            final(self).is_full_spec(slot as int),
            forall|j: int| 0 <= j < final(self).bytes@.len() && j != slot as int
                ==> final(self).bytes[j] == old(self).bytes[j],
    {
        self.bytes[slot] = h2;
    }

    /// Upstream `MakeDeleted`.  ControlBytes.C003 (precondition: only a full slot
    /// may be tombstoned) and ControlBytes.C004 (postcondition: the slot now
    /// reads as empty-or-deleted and nothing else moved).
    pub fn set_dead(&mut self, slot: usize)
        requires
            self.well_formed(),
            slot < self.capacity,
            self.is_full_spec(slot as int),             // ControlBytes.C003
        ensures
            final(self).well_formed(),
            final(self).is_empty_or_deleted_spec(slot as int), // ControlBytes.C004
            final(self).is_dead_spec(slot as int),
            forall|j: int| 0 <= j < final(self).bytes@.len() && j != slot as int
                ==> final(self).bytes[j] == old(self).bytes[j],
    {
        self.bytes[slot] = DELETED;
    }

    /// Upstream `MakeEmpty`.  ControlBytes.C008.
    pub fn set_empty(&mut self, slot: usize)
        requires
            self.well_formed(),
            slot < self.capacity,
        ensures
            final(self).well_formed(),
            final(self).is_empty_spec(slot as int),            // ControlBytes.C008
            forall|j: int| 0 <= j < final(self).bytes@.len() && j != slot as int
                ==> final(self).bytes[j] == old(self).bytes[j],
    {
        self.bytes[slot] = EMPTY;
    }

    /// Upstream `ConvertDeletedToEmptyAndFullToDeleted` (raw_hash_set.cc
    /// L434-L447), reached from `RawTable::resize` through
    /// `BR-CONTROLBYTES-CLEARDEAD-001`.
    ///
    /// The rewrite is: every **full** byte becomes `kDeleted`, and every byte that
    /// already had the MSB set -- `kEmpty` *and* `kDeleted` -- becomes `kEmpty`.
    /// The reference writes it as one saturating subtract over a whole group
    /// (`_mm_subs_epi8(and(msbs, ctrl), twos)`); this port writes it one slot at a
    /// time, which has the same byte-for-byte result.
    ///
    /// ## Divergence from the staged draft, recorded not hidden
    ///
    /// The staged `ControlBytes.C006` names three clauses: all full bytes become
    /// deleted, empty bytes stay empty, and "never turns a deleted byte into an
    /// empty one".  The third clause contradicts the reference (raw_hash_set.cc
    /// L434, asserted again in raw_hash_set_test.cc L960) *and* the concept's own
    /// command text for `clear_dead`, "reclaim every deleted slot as empty".
    /// `RawTable::resize` depends on the third clause being false: the whole point
    /// of the conversion is that afterwards `kDeleted` marks a live element and
    /// `kEmpty` marks a reusable slot.  Implementing C006's third clause would make
    /// resize unsound, so this port implements the reference and records the
    /// clause as a defect for the operator's Stage 4 batch -- see
    /// `findings/limitations.jsonl`, `swisstable-spec-001`.
    pub fn clear_dead(&mut self)
        requires
            self.well_formed(),
            self.bytes[(self.capacity as int)] == SENTINEL,    // ControlBytes.C005
        ensures
            final(self).well_formed(),
            // ControlBytes.C006, clause 1: every full byte is now a tombstone.
            forall|i: int| 0 <= i < final(self).capacity as int && old(self).is_full_spec(i)
                ==> final(self).is_dead_spec(i),
            // ControlBytes.C006, clause 2: empty bytes stay empty.
            forall|i: int| 0 <= i < final(self).capacity as int && old(self).is_empty_spec(i)
                ==> final(self).is_empty_spec(i),
            // The reference's third behaviour, which staged C006 denies: reclaimed
            // tombstones become empty again.
            forall|i: int| 0 <= i < final(self).capacity as int && old(self).is_dead_spec(i)
                ==> final(self).is_empty_spec(i),
            // So the live elements are exactly the bytes left as tombstones.
            forall|i: int| 0 <= i < final(self).capacity as int
                ==> (final(self).is_dead_spec(i) <==> old(self).is_full_spec(i)),
            // The rewrite is a map over the old array, so the shape is untouched.
            // `RawTable::resize`'s reclaim window needs both of these: it indexes
            // the pre-reclaim snapshot by the *same* bound afterwards.
            final(self).capacity == old(self).capacity,
            final(self).bytes@.len() == old(self).bytes@.len(),
    {
        // Upstream rewrites the whole span in one pass
        // (`ConvertDeletedToEmptyAndFullToDeleted` is `absl::bit_internal::Subtract`,
        // a map over the control bytes).  This port builds the rewritten array the
        // same way -- map the old bytes to a fresh sequence, then install it -- which
        // keeps the loop over a local `Vec` and leaves `old(self)` intact for the
        // postcondition.
        let ghost orig = old(self).bytes@;
        let mut out: Vec<u8> = Vec::new();
        let mut i: usize = 0;
        while i < self.bytes.len()
            invariant
                i <= self.bytes.len(),
                self.well_formed(),
                self.bytes@ == orig,
                out@.len() == i,
                // index `i` is being mapped; every earlier index is already its image
                forall|j: int| 0 <= j < i
                    ==> out[j] == if j < self.capacity as int {
                        if orig[j] <= 0x7F { DELETED } else { EMPTY }
                    } else {
                        orig[j]
                    },
            decreases self.bytes.len() - i,
        {
            if i < self.capacity {
                if self.bytes[i] <= 0x7F {
                    out.push(DELETED);
                } else {
                    out.push(EMPTY);
                }
            } else {
                out.push(self.bytes[i]);
            }
            i = i + 1;
        }
        proof {
            assert(self.bytes@.len() == self.capacity + 1 + PAD_BYTES);
            assert(self.bytes@[self.capacity as int] == SENTINEL);
        }
        self.bytes = out;
        proof {
            assert(self.bytes@.len() == old(self).bytes@.len());
            assert(self.capacity == old(self).capacity);
            assert forall|j: int| 0 <= j < self.bytes@.len()
                implies Self::reclaimed(old(self).bytes@, self.bytes@, j) by {
                assert(old(self).bytes@[j] == orig[j]);
            }
        }
    }
}

} // verus!
