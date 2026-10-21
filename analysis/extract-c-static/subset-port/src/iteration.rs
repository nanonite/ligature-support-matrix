// Iteration transcription (chainlink #108 fixture).
// C++ side: raw_hash_set.h L2451-L2765 iteration layer plus the AssertIsFull
// boundary at L1586.

use crate::ctrl::Ctrl;

pub struct FindInfo {
    pub offset: usize,
    pub probe_length: usize,
}

// raw_hash_set.h L1270 generation, L1280 generation_ptr
pub struct GenerationInfo;
impl GenerationInfo {
    pub fn generation(&self) -> usize { 0 }
    pub fn generation_ptr(&self) -> usize { 0 }
}

pub struct Table {
    pub ctrl: Vec<Ctrl>,
    pub slots: Vec<usize>,
    pub gen: GenerationInfo,
}

impl Table {
    // raw_hash_set.h L1341 slot_array, L1152 NumControlBytes,
    // L398 IsSmallCapacity
    pub fn slot_array(&self) -> &Vec<usize> { &self.slots }
    pub fn num_control_bytes(&self) -> usize { self.ctrl.len() }
    pub fn is_small_capacity(&self) -> bool { self.num_control_bytes() <= 16 }

    // raw_hash_set.h L2753-2761 begin -> end L2754, empty L2754, is_small
    // L2755, slot_array L2756, capacity L2756, generation_ptr L2757,
    // skip_empty_or_deleted L2758, IsFull L2759.
    // codesight-mcp recorded end / skip_empty_or_deleted / slot_array /
    // NumControlBytes / IsSmallCapacity and missed the other four.
    pub fn begin(&self) -> Iterator {
        if self.empty() { return self.end(); }
        let _ = self.is_small();
        let mut it = Iterator {
            pos: 0,
            end: self.slot_array(self.capacity()).len(),
        };
        it.skip_empty_or_deleted();
        let _ = is_full(it.control().byte);
        it
    }
    pub fn empty(&self) -> bool { self.slots.is_empty() }
    pub fn is_small(&self) -> bool { self.is_small_capacity() }
    pub fn capacity(&self) -> usize { self.ctrl.len() }
    pub fn end(&self) -> Iterator { Iterator { pos: self.slots.len(), end: self.slots.len() } }
    pub fn generation_ptr(&self) -> usize { self.gen.generation_ptr() }

    // raw_hash_set.h L2451-2456 skip_empty_or_deleted -> IsEmptyOrDeleted
    pub fn skip_empty_or_deleted(&self, at: usize) -> bool {
        self.ctrl[at].is_empty_or_deleted()
    }

    // raw_hash_set.h L2445-2449 assert_is_full -> AssertIsFull L1586.
    // codesight-mcp answers btree.h::generation L1094 here instead.
    pub fn assert_is_full(&self, pos: usize) {
        self.assert_is_full_boundary(self.ctrl[0].byte, pos);
    }

    // raw_hash_set.h L1586 AssertIsFull: generation()/generation_ptr() are its
    // *parameters*, evaluated at the call site h:2446, not calls inside it.
    pub fn assert_is_full_boundary(&self, ctrl: u8, _slot: usize) {
        self.swisstable_debug_enabled(ctrl);
    }
    pub fn swisstable_debug_enabled(&self, ctrl: u8) -> bool { ctrl != 0 }

    // raw_hash_set.h L445-448 IterateOverFullSlots -> IterateOverFullSlotsImpl
    pub fn iterate_over_full_slots(&self) -> u64 { self.iterate_over_full_slots_impl() }
    pub fn iterate_over_full_slots_impl(&self) -> u64 { self.num_control_bytes() as u64 }

    // raw_hash_set.cc L479-484 FindEmptySlot -> IsEmpty
    pub fn find_empty_slot(&self, start: usize, end: usize) -> usize {
        for i in start..end {
            if self.ctrl[i].is_empty() { return i; }
        }
        end
    }

    // raw_hash_set.cc FindFirstFullSlot -> ctrl::IsFull
    pub fn find_first_full_slot(&self) -> usize {
        self.ctrl[0].is_full()
    }
}

impl Ctrl {
    pub fn is_full(&self) -> bool { !self.is_empty() && !self.is_deleted() }
}

// raw_hash_set.h L2759 IsFull(*it.control())
pub fn is_full(c: u8) -> bool { Ctrl { byte: c }.is_full() }

// raw_hash_set.h L2762 end, L2451 skip_empty_or_deleted, L1785 next,
// L1783 offset
pub struct Iterator {
    pub pos: usize,
    pub end: usize,
}

impl Iterator {
    pub fn skip_empty_or_deleted(&mut self) -> usize { self.pos }
    pub fn next(&mut self) -> usize { self.pos += 1; self.pos }
    pub fn offset(&self) -> usize { self.pos }
    pub fn control(&self) -> Ctrl { Ctrl { byte: 0 } }
}
