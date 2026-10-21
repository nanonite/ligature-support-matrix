// Tombstone / ctrl-byte transcription (chainlink #108 fixture).
// C++ side: hashtable_control_bytes.h ctrl_t helpers (L58-L64 region) and the
// raw_hash_set.cc erase meta-only path.  codesight-mcp answered
// `Symbol not found` for ctrl::{H1,H2,IsDeleted,IsEmpty,MakeDeleted,MakeEmpty}.

// ctrl_t::kSentinel / kEmpty / kDeleted
pub const K_EMPTY: u8 = 0xFF;
pub const K_DELETED: u8 = 0x80;

pub struct Ctrl {
    pub byte: u8,
}

impl Ctrl {
    // raw_hash_set.cc L193 IsEmptyOrDeleted(ctrl[seq.offset()])
    pub fn is_deleted(&self) -> bool { self.byte == K_DELETED }
    pub fn is_empty(&self) -> bool { self.byte == K_EMPTY }
    pub fn is_empty_or_deleted(&self) -> bool { self.is_deleted() || self.is_empty() }
    pub fn make_deleted(&mut self) { self.byte = K_DELETED; }
    pub fn make_empty(&mut self) { self.byte = K_EMPTY; }
    pub fn make_sentinel(&mut self) { self.make_deleted(); }
}

pub fn is_empty(c: u8) -> bool { Ctrl { byte: c }.is_empty() }
pub fn is_deleted(c: u8) -> bool { Ctrl { byte: c }.is_deleted() }
pub fn is_empty_or_deleted(c: u8, _at: usize) -> bool {
    Ctrl { byte: c }.is_empty_or_deleted()
}

pub struct GrowthInfoAccessor {
    pub growth_left: usize,
}

// raw_hash_set.cc L421-432 OverwriteFullAsEmpty -> GetPackedIncrement L291
impl GrowthInfoAccessor {
    pub fn overwrite_full_as_empty(&mut self) {
        self.growth_left = get_packed_increment(0, 1);
    }
    // raw_hash_set.cc L469-473 ResetGrowthLeft is a free function in an anon
    // namespace -> InitGrowthLeftNoDeleted, CapacityToGrowth
    pub fn init_growth_left_no_deleted(&mut self, capacity: usize, occupied: usize) {
        self.growth_left = capacity_to_growth(capacity) - occupied;
    }
    pub fn reset_growth_left(&mut self) { self.growth_left = 0; }
}

// raw_hash_set.cc L469-473 ResetGrowthLeft
pub fn reset_growth_left(growth_info: &mut GrowthInfoAccessor, capacity: usize,
                         occupied: usize) {
    growth_info.init_growth_left_no_deleted(capacity, occupied);
}

// raw_hash_set.cc L291
pub fn get_packed_increment(lower_bound_increment: usize, overflow_increment: usize) -> usize {
    lower_bound_increment + overflow_increment
}
// raw_hash_set.cc L~300 capacity_to_growth
pub fn capacity_to_growth(capacity: usize) -> usize { capacity }

// raw_hash_set.h L395 IsValidCapacity
pub fn is_valid_capacity(capacity: usize) -> bool { capacity != 0 }
// container_memory.h L236 SanitizerPoisonMemoryRegion
pub fn poison_memory_region(addr: usize) { let _ = addr; }

pub struct Slot {
    pub ctrl: Ctrl,
    pub size: usize,
}

impl Slot {
    // raw_hash_set.h L719 set_size, L1351 set_empty_soo, L1425 infoz
    pub fn set_size(&mut self, n: usize) { self.size = n; }
    pub fn set_empty_soo(&mut self) { self.size = 0; }
    pub fn infoz(&self) -> usize { self.size }
}

pub struct Table {
    pub ctrl: Vec<Ctrl>,
    pub slots: Vec<Slot>,
}

// raw_hash_set.cc L856-866 EraseMetaOnlySmall -> SanitizerPoisonMemoryRegion,
// infoz, set_empty_soo, set_size
impl Table {
    pub fn erase_meta_only_small(&mut self, i: usize) {
        self.slots[i].set_size(0);
        self.slots[i].set_empty_soo();
        let _ = self.slots[i].infoz();
        poison_memory_region(self.slots[i].size);
    }

    // raw_hash_set.cc L868-876 EraseMetaOnlyLarge -> WasNeverFull L708, infoz
    pub fn erase_meta_only_large(&mut self, i: usize) {
        let _ = self.was_never_full(i);
        let _ = self.slots[i].infoz();
    }

    // raw_hash_set.cc L708-723 WasNeverFull -> is_single_group, Group::MaskEmpty
    pub fn was_never_full(&self, index: usize) -> bool {
        if self.is_single_group() { return true; }
        let g = crate::group::Group { ctrl: self.ctrl[index].byte };
        g.mask_empty() != 0
    }

    pub fn is_single_group(&self) -> bool { self.slots.len() <= 16 }
}

// raw_hash_set.cc L434-443 ConvertDeletedToEmptyAndFullToDeleted
// -> IsValidCapacity, Group::ConvertSpecialToEmptyAndFullToDeleted,
//    NumClonedBytes
pub fn convert_deleted_to_empty_and_full_to_deleted(table: &mut Table, capacity: usize) {
    if is_valid_capacity(capacity) {
        for i in 0..table.slots.len() {
            table.ctrl[i].convert_special();
            let _ = num_cloned_bytes();
        }
    }
}

impl Ctrl {
    pub fn convert_special(&mut self) { self.byte = K_DELETED; }
}

pub fn num_cloned_bytes() -> usize { 0 }
