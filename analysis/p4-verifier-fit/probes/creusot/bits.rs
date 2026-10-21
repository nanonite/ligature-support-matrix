//! #157 probe: P2's bitwise operations in Creusot.
use creusot_std::prelude::*;

/// H2: the low seven hash bits (P2 hash_mix; Abseil H2).
#[ensures(result@ < 128)]
#[bitwise_proof]
pub fn h2(hash: u64) -> u8 {
    (hash & 0x7f) as u8
}

/// H1: the hash without its low seven bits.
#[ensures(result@ == hash@ / 128)]
#[bitwise_proof]
pub fn h1(hash: u64) -> u64 {
    hash >> 7
}

/// Probe offset under a capacity mask.
#[ensures(result <= mask)]
#[bitwise_proof]
pub fn offset(hash: u64, mask: u64) -> u64 {
    hash & mask
}

/// Index of the lowest set bit of a non-empty 16-lane group mask.
#[requires(m != 0u16)]
#[ensures(result@ < 16)]
pub fn lowest_bit(m: u16) -> u32 {
    m.trailing_zeros()
}
