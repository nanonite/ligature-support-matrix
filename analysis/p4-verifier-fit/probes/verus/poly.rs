use vstd::prelude::*;
verus! {
// Poly1305 d0 (P3 poly1305.rs process_block): 26-bit limbs, h_i < 2^27, r_i < 2^26.
fn d0(h0: u64, h1: u64, h2: u64, h3: u64, h4: u64, r1: u64, r2: u64, r3: u64, r4: u64, r0: u64) -> (d: u64)
    requires h0 < 0x800_0000, h1 < 0x800_0000, h2 < 0x800_0000, h3 < 0x800_0000, h4 < 0x800_0000,
             r0 < 0x400_0000, r1 < 0x400_0000, r2 < 0x400_0000, r3 < 0x400_0000, r4 < 0x400_0000,
{
    let s1 = r1 * 5;
    let s2 = r2 * 5;
    let s3 = r3 * 5;
    let s4 = r4 * 5;
    h0 * r0 + h1 * s4 + h2 * s3 + h3 * s2 + h4 * s1
}
fn main() {}
}
