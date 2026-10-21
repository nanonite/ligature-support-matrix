// Rehash / capacity transcription (chainlink #108 fixture).
// C++ side: raw_hash_set.{h,cc} capacity + resize layer.  Every template
// function in this layer takes `const PolicyFunctions& __restrict policy`,
// the shape analysis/codesight found the C grammar drops.

pub trait PolicyFunctions {
    fn is_deleted(&self) -> bool;
    fn slot_size(&self) -> usize;
}

use crate::open_addressing::BlockControlBytes;
use crate::open_addressing::find_first_non_full;
use crate::open_addressing::probe;
use crate::tombstones::convert_deleted_to_empty_and_full_to_deleted;
use crate::tombstones::is_deleted;
use crate::tombstones::is_empty;

// raw_hash_set.h NormalizeCapacity / GrowToNextCapacity -- Symbol not found
pub fn normalize_capacity(n: usize) -> usize { n }
pub fn grow_to_next_capacity(n: usize) -> usize { n * 2 }
// raw_hash_set.h NextCapacity / PreviousCapacity -- the most called pair
pub fn next_capacity(n: usize) -> usize { n * 2 }
pub fn previous_capacity(n: usize) -> usize { n / 2 }

// raw_hash_set.cc L74 ValidateMaxCapacity -> PreviousCapacity
pub fn validate_max_capacity(cap: usize) -> bool { previous_capacity(cap) > 0 }

// raw_hash_set.cc L108 SingleGroupTableH1
pub fn single_group_table_h1(hash: u64, seed: u64) -> usize { (hash ^ seed) as usize }

// raw_hash_set.cc L112-124 Resize1To3NewOffset -> SingleGroupTableH1,
// raw_hash_set.h L2027 SooSlotIndex
pub fn resize_1_to_3_new_offset(hash: u64, seed: u64, single_l2: usize) -> usize {
    let h1 = single_group_table_h1(hash, seed);
    soo_slot_index(single_l2) + h1
}
pub fn soo_slot_index(single_l2: usize) -> usize { single_l2 }

pub struct Table {
    pub capacity: usize,
}

// raw_hash_set.h L1526 OverflowBufferStart -> NextCapacity
impl Table {
    pub fn overflow_buffer_start(&self) -> usize { next_capacity(self.capacity) }
}

// The resize template layer.  codesight-mcp: Resize, ResizeImpl,
// ResizeWithoutDeletingOrCreatingNewSlots, NormalizeCapacity,
// GrowToNextCapacity, RehashOrGrowToNextCapacityAndPrepareInsert,
// DropDeletesWithoutResizeAndPrepareInsert are all `Symbol not found`.
impl Table {
    pub fn resize<P: PolicyFunctions>(&mut self, policy: &P) {
        self.resize_impl(policy);
    }
    pub fn resize_impl<P: PolicyFunctions>(&mut self, policy: &P) {
        self.resize_without_deleting_or_creating_new_slots(policy);
    }
    pub fn resize_without_deleting_or_creating_new_slots<P: PolicyFunctions>(
        &mut self,
        policy: &P,
    ) {
        let _ = normalize_capacity(self.capacity);
        let _ = policy.is_deleted();
    }
    pub fn rehash_or_grow_to_next_capacity_and_prepare_insert<P: PolicyFunctions>(
        &mut self,
        policy: &P,
    ) {
        // raw_hash_set.cc L1958 the if branch ...
        self.drop_deletes_without_resize_and_prepare_insert(policy);
        // ... and L1961 the else branch
        self.grow_to_next_capacity_and_prepare_insert(policy);
    }
    // raw_hash_set.cc L1961 the else branch
    pub fn grow_to_next_capacity_and_prepare_insert<P: PolicyFunctions>(
        &mut self,
        policy: &P,
    ) {
        self.capacity = grow_to_next_capacity(self.capacity);
        let _ = policy.is_deleted();
    }
    // raw_hash_set.cc L1966-1993 PrepareInsertLargeSlow
    pub fn prepare_insert_large_slow<P: PolicyFunctions>(&mut self, policy: &P) {
        self.grow_to_next_capacity_and_prepare_insert(policy);
        self.rehash_or_grow_to_next_capacity_and_prepare_insert(policy);
    }
    pub fn drop_deletes_without_resize_and_prepare_insert<P: PolicyFunctions>(
        &mut self,
        policy: &P,
    ) {
        let _ = normalize_capacity(self.capacity);
        let _ = policy.is_deleted();
    }
    pub fn grow_into_single_group_shuffle_control_bytes(&mut self) {
        self.capacity = normalize_capacity(self.capacity);
    }
}

// raw_hash_set_resize_impl.h: indexed as one symbol named `(module)`;
// ProbedItem4Bytes / ProbedItem8Bytes / ProbedItem16Bytes / ProbedItemImpl
// and all three resize-impl probes are gone.
pub struct ProbedItem4Bytes;
pub struct ProbedItem8Bytes;
pub struct ProbedItem16Bytes;

pub struct ProbedItemImpl {
    pub tag: u8,
}

impl ProbedItemImpl {
    pub fn is_full(&self) -> bool { true }
    // raw_hash_set_resize_impl.h resize_allowed_without_rehash -> NormalizeCapacity
    pub fn resize_allowed_without_rehash(&self, n: usize) -> bool {
        normalize_capacity(n) == n
    }
}

// raw_hash_set.cc L593-700 DropDeletesWithoutResizeAndPrepareInsert.
// It takes `const PolicyFunctions& __restrict policy`, the shape the C
// grammar drops, and it is the hub the whole rehash area hangs off.
pub fn drop_deletes_without_resize_and_prepare_insert<P: PolicyFunctions>(
    table: &mut Table,
    ctrl: &[u8],
    policy: &P,
) {
    if !is_valid_capacity(table.capacity) {
        return;
    }
    convert_deleted_to_empty_and_full_to_deleted(table);
    let mut block = BlockControlBytes::new(ctrl.to_vec());
    block.make_sentinel(0);
    if is_empty(ctrl[0]) {
        return;
    }
    if !is_deleted(ctrl[0]) {
        return;
    }
    let _ = find_first_non_full(ctrl[0], 0, table.capacity);
    let _ = probe(table.capacity, 0).offset_();
    let _ = policy.is_deleted();
    let _ = policy.slot_size();
}

pub fn is_valid_capacity(capacity: usize) -> bool { capacity != 0 }
