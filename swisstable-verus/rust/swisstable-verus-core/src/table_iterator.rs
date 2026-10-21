//! TableIterator -- a cursor over a table's slots that visits only full slots.
//!
//! Reference: absl/container/internal/raw_hash_set.h L2440-L2460
//! (`skip_empty_or_deleted`, `assert_is_full`) and L2753-L2765 (`begin`/`end`,
//! `Iterator::IsFull`).
//!
//! The stop condition is the control byte under the cursor: `skip_empty_or_deleted`
//! in the reference, `advance` here.  `is_end` is that byte being the sentinel at
//! index `capacity`.
//!
//! Both stepping loops carry the same frame -- "every control index at or after
//! the cursor and before `capacity` is not empty-or-deleted" -- and the exit
//! condition turns it into TableIterator.C002 with `lemma_not_free_gives_full`.

use crate::control_bytes::ControlBytes;
#[cfg(verus_only)]
use crate::lemmas::{lemma_full_is_not_free, lemma_not_free_gives_full};
use vstd::prelude::*;

verus! {

pub struct TableIterator {
    /// The control index the cursor rests on.
    pub offset_: usize,
    /// The control array's slot count; index `capacity` is the sentinel.
    pub capacity: usize,
}

impl TableIterator {
    pub fn new(capacity: usize) -> (it: Self)
        requires capacity >= crate::control_bytes::GROUP_WIDTH,
        ensures
            it.offset_ == 0,
            it.capacity == capacity,
            it.offset_ != it.capacity,
    {
        TableIterator { offset_: 0, capacity }
    }

    /// TableIterator::is_end.  TableIterator.C001: a cursor that is not at the end
    /// never rests on an empty or deleted slot -- upstream's `IsFull`
    /// assertion, read as a predicate.
    pub fn is_end(&self) -> (r: bool)
        requires self.offset_ <= self.capacity,
        ensures
            r == (self.offset_ == self.capacity),
            !r <==> self.offset_ < self.capacity,
    {
        self.offset_ == self.capacity
    }

    /// TableIterator::offset.  TableIterator.C003: the control index never passes
    /// the sentinel at index `capacity`.
    pub fn offset(&self) -> (r: usize)
        requires self.offset_ <= self.capacity,
        ensures
            r == self.offset_,
            r <= self.capacity,                                         // TableIterator.C003
    {
        self.offset_
    }

    /// The invariant every cursor satisfies: either it has run past the last
    /// element, or it rests on a full slot.  TableIterator.C001 for the queries,
    /// TableIterator.C002 for this transition.
    pub open spec fn on_full_or_end(&self, ctrl: &ControlBytes) -> bool {
        self.offset_ == self.capacity
            || (ctrl.well_formed() && self.capacity == ctrl.capacity
                && ctrl.is_full_spec(self.offset_ as int))
    }

    /// TableIterator::advance -- upstream `skip_empty_or_deleted`: step over every
    /// empty-or-deleted control byte until a full slot or the sentinel.
    pub fn advance(&mut self, ctrl: &ControlBytes)
        requires
            ctrl.well_formed(),
            self.capacity == ctrl.capacity,
            self.offset_ <= self.capacity,
            self.on_full_or_end(ctrl),
        ensures
            final(self).offset_ <= final(self).capacity,               // TableIterator.C003
            final(self).on_full_or_end(ctrl),                          // TableIterator.C002
            final(self).offset_ >= old(self).offset_,
    {
        let ghost start = self.offset_;
        assert(ctrl.well_formed());
        assert(self.capacity == ctrl.capacity);
        let mut i = self.offset_;
        while i < ctrl.capacity && ctrl.is_empty_or_deleted(i)
            invariant
                i <= ctrl.capacity,
                i >= start,
                self.capacity == ctrl.capacity,
                ctrl.well_formed(),
                i as int <= self.capacity as int,
            decreases self.capacity - i,
        {
            i = i + 1;
        }
        if i < ctrl.capacity {
            assert(i as int <= self.capacity as int);
            assert(!ctrl.is_empty_or_deleted_spec(i as int));
            proof { lemma_not_free_gives_full(ctrl, i as int); }
        }
        self.offset_ = i;
    }

    /// TableIterator::rewind_to_full -- move a default cursor onto the first full
    /// slot.
    ///
    /// TableIterator.C004: the order in which a cursor visits elements follows the
    /// slot layout and is not part of the container's contract, so nothing here
    /// constrains it beyond "the first full slot in index order".
    pub fn rewind_to_full(&mut self, ctrl: &ControlBytes)
        requires
            ctrl.well_formed(),
            self.capacity == ctrl.capacity,
            self.offset_ <= self.capacity,
        ensures
            final(self).offset_ <= final(self).capacity,               // TableIterator.C003
            final(self).on_full_or_end(ctrl),                          // TableIterator.C004
    {
        assert(ctrl.well_formed());
        assert(self.capacity == ctrl.capacity);
        let mut i: usize = 0;
        while i < ctrl.capacity && ctrl.is_empty_or_deleted(i)
            invariant
                i <= ctrl.capacity,
                self.capacity == ctrl.capacity,
                ctrl.well_formed(),
                i as int <= self.capacity as int,
            decreases self.capacity - i,
        {
            i = i + 1;
        }
        if i < ctrl.capacity {
            assert(i as int <= self.capacity as int);
            assert(!ctrl.is_empty_or_deleted_spec(i as int));
            proof { lemma_not_free_gives_full(ctrl, i as int); }
        }
        self.offset_ = i;
    }
}

} // verus!
