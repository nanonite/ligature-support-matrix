use vstd::prelude::*;
verus! {
// u32::wrapping_add, as P3 chacha20.rs uses it.
fn add(a: u32, b: u32) -> (r: u32)
    ensures r as int == (a as int + b as int) % 0x1_0000_0000,
{
    a.wrapping_add(b)
}
fn main() {}
}
