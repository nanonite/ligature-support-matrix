use vstd::prelude::*;
verus! {
// u32::from_le_bytes, as P3 load_u32_le uses it.
fn load_u32_le(b0: u8, b1: u8, b2: u8, b3: u8) -> (r: u32)
    ensures r as int == b0 as int + 256 * (b1 as int) + 65536 * (b2 as int) + 16777216 * (b3 as int),
{
    u32::from_le_bytes([b0, b1, b2, b3])
}
fn main() {}
}
