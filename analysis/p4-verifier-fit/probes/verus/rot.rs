use vstd::prelude::*;
verus! {
// u32::rotate_left, as P3 chacha20.rs uses it.
fn rot16(x: u32) -> (r: u32)
    ensures r == ((x << 16u32) | (x >> 16u32)),
{
    x.rotate_left(16)
}
fn main() {}
}
