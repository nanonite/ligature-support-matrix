// The SIMD group layer, transcribed (chainlink #108 fixture).
// C++ side: hashtable_control_bytes.h -- the file codesight-mcp indexes as a
// single symbol literally named `class`.

// raw_hash_set.cc L179 GroupFullEmptyOrDeleted{ctrl + seq.offset()}
pub struct GroupFullEmptyOrDeleted {
    pub ctrl: u8,
}

impl GroupFullEmptyOrDeleted {
    // hashtable_control_bytes.h L318 MaskEmptyOrDeleted
    pub fn mask_empty_or_deleted(&self) -> u64 { self.ctrl as u64 }
    // hcb L438 ConvertSpecialToEmptyAndFullToDeleted
    pub fn convert_special_to_empty_and_full_to_deleted(&mut self) { self.ctrl = 0xFF; }
}

pub struct GroupSse2Impl {
    pub ctrl: u8,
}

impl GroupSse2Impl {
    // hcb L291 Match, L297 MaskEmpty, L310 MaskFull, L315 MaskNonFull
    pub fn match_hash(&self, h2: u8) -> u64 { (self.ctrl & h2) as u64 }
    pub fn mask_empty(&self) -> u64 { self.ctrl as u64 }
    pub fn mask_full(&self) -> u64 { !self.ctrl as u64 }
    pub fn mask_non_full(&self) -> u64 { self.ctrl as u64 }
}

pub struct Group {
    pub ctrl: u8,
}

impl Group {
    // raw_hash_set.cc L713-714 WasNeverFull -> Group::MaskEmpty
    pub fn mask_empty(&self) -> u64 { self.ctrl as u64 }
    // hcb ConvertSpecialToEmptyAndFullToDeleted
    pub fn convert_special_to_empty_and_full_to_deleted(&mut self) { self.ctrl = 0xFF; }
}

// hcb NonIterableBitMask / BitMask: LowestBitSet, LeadingZeros, TrailingZeros
pub struct BitMask {
    pub bits: u64,
}

impl BitMask {
    pub fn lowest_bit_set(&self) -> u64 { self.bits & self.bits.wrapping_neg() }
    pub fn leading_zeros(&self) -> u32 { self.bits.leading_zeros() }
    pub fn trailing_zeros(&self) -> u32 { self.bits.trailing_zeros() }
}
