use vstd::prelude::*;
verus! {
// #157 probe: the same four bitwise facts as the Creusot bits probe.
fn h2(hash: u64) -> (r: u8)
    ensures r < 128,
{
    assert(hash & 0x7f < 128) by (bit_vector);
    (hash & 0x7f) as u8
}
fn h1(hash: u64) -> (r: u64)
    ensures r == hash / 128,
{
    assert(hash >> 7 == hash / 128) by (bit_vector);
    hash >> 7
}
fn offset(hash: u64, mask: u64) -> (r: u64)
    ensures r <= mask,
{
    assert(hash & mask <= mask) by (bit_vector);
    hash & mask
}
fn lowest_bit(m: u16) -> (r: u32)
    requires m != 0,
    ensures r < 16,
{
    m.trailing_zeros()
}
fn main() {}
}
