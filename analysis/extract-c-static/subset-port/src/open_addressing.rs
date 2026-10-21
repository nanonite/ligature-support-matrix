// Open addressing + group probing transcription (chainlink #108 fixture).
//
// Faithful to the pinned C++ at upstream/abseil-cpp 2065f4de: a C++ free
// function is transcribed as a Rust free function, a C++ member as a Rust
// method on a type named after the C++ type.  Line citations are in
// ../edge-truth.tsv.  NOT pilot code.

use crate::group::GroupFullEmptyOrDeleted;
use crate::group::Group;

pub struct ProbeSeq {
    pub capacity: usize,
    pub offset: usize,
    pub index: usize,
}

impl ProbeSeq {
    // raw_hash_set.h L1782 / L1783 / L1785 / L1791 -- all leaves
    pub fn offset_(&self) -> usize { self.offset }
    pub fn offset_at(&self, i: usize) -> usize { (self.offset + i) & self.capacity }
    pub fn next(&mut self) { self.index += 16; self.offset += self.index; self.offset &= self.capacity; }
    pub fn index_(&self) -> usize { self.index }
}

// raw_hash_set.h L1800 probe_h1 -> probe_seq ctor
pub fn probe_h1(capacity: usize, h1: usize) -> ProbeSeq {
    ProbeSeq { capacity, offset: h1 & capacity, index: 0 }
}

// raw_hash_set.h L832 H1, L837 H2 -- leaf arithmetic
pub fn h1(hash: u64) -> usize { (hash % 64) as usize }
pub fn h2(hash: u64) -> u8 { (hash >> 56) as u8 }

// raw_hash_set.h L1803 probe -> H1 -> probe_h1
pub fn probe(capacity: usize, hash: u64) -> ProbeSeq {
    probe_h1(capacity, h1(hash))
}

// raw_hash_set.cc L94-102 ShouldRehashForBugDetection:
//   -> probe -> .offset() -> RehashProbabilityConstant
pub fn should_rehash_for_bug_detection(capacity: usize) -> bool {
    probe(capacity, 0).offset_() < rehash_probability_constant()
}

// raw_hash_set.h L846 RehashProbabilityConstant -- leaf
pub fn rehash_probability_constant() -> usize { 14 }

// raw_hash_set.cc L175-187 probe_till_first_non_full_group:
//   -> GroupFullEmptyOrDeleted::MaskEmptyOrDeleted, seq.offset(), seq.next(),
//      seq.index()
pub fn probe_till_first_non_full_group(
    ctrl: u8,
    seq: &mut ProbeSeq,
    capacity: usize,
) -> u64 {
    let g = GroupFullEmptyOrDeleted { ctrl };
    let mask = g.mask_empty_or_deleted();
    if mask != 0 {
        return mask;
    }
    seq.next();
    let _ = seq.index_() <= capacity;
    seq.offset_at(0)
}

// raw_hash_set.cc L189-198 find_first_non_full_from_h1:
//   -> capacity, probe_h1, IsEmptyOrDeleted, probe_till_first_non_full_group,
//      seq.offset(), seq.index(), LowestBitSet
pub fn find_first_non_full_from_h1(ctrl: u8, h1: usize, capacity: usize) -> (usize, usize) {
    let mut seq = probe_h1(capacity, h1);
    if crate::ctrl::is_empty_or_deleted(ctrl, seq.offset_at(0)) {
        return (seq.offset_at(0), 0);
    }
    let mask = probe_till_first_non_full_group(ctrl, &mut seq, capacity);
    (seq.offset_at(mask.trailing_zeros()), seq.index_())
}

// raw_hash_set.cc L207-210 find_first_non_full -> H1, find_first_non_full_from_h1
pub fn find_first_non_full(ctrl: u8, hash: u64, capacity: usize) -> (usize, usize) {
    find_first_non_full_from_h1(ctrl, h1(hash), capacity)
}

// raw_hash_set.cc L214-220 find_first_non_full_group:
//   -> probe, probe_till_first_non_full_group, seq.offset(), seq.index()
pub fn find_first_non_full_group(ctrl: u8, hash: u64, capacity: usize) -> (usize, u64) {
    let mut seq = probe(capacity, hash);
    let mask = probe_till_first_non_full_group(ctrl, &mut seq, capacity);
    (seq.offset_at(0), mask)
}

pub struct BlockControlBytes {
    pub ctrl: Vec<u8>,
}

impl BlockControlBytes {
    // raw_hash_set.cc L585 -> BlockCtrl L546, SetCtrlNoSanitizeImpl L523
    pub fn new(ctrl: Vec<u8>) -> BlockControlBytes { BlockControlBytes { ctrl } }
    pub fn block_ctrl(&mut self, i: usize) -> u8 { self.ctrl[i] }
    pub fn set_ctrl_no_sanitize_impl(&mut self, i: usize, v: u8) { self.ctrl[i] = v; }
    pub fn make_sentinel(&mut self, i: usize) {
        self.set_ctrl_no_sanitize_impl(i, 0x80);
    }
}
