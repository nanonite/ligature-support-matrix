use vstd::prelude::*;
verus! {
// The ChaCha20 quarter-round (RFC 8439 section 2.1) against a spec, rotation by shifts.
pub open spec fn add32(a: u32, b: u32) -> u32 { ((a as int + b as int) % 0x1_0000_0000) as u32 }
pub open spec fn rotl(x: u32, n: u32) -> u32 { (x << n) | (x >> ((32 - n) as u32)) }
pub open spec fn qr_spec(a: u32, b: u32, c: u32, d: u32) -> (u32, u32, u32, u32) {
    let a = add32(a, b); let d = rotl(d ^ a, 16);
    let c = add32(c, d); let b = rotl(b ^ c, 12);
    let a = add32(a, b); let d = rotl(d ^ a, 8);
    let c = add32(c, d); let b = rotl(b ^ c, 7);
    (a, b, c, d)
}
fn rotl_exec(x: u32, n: u32) -> (r: u32)
    requires 0 < n < 32,
    ensures r == rotl(x, n),
{
    (x << n) | (x >> (32 - n))
}
// The same steps as P3 quarter_round, with rotation written as shifts.
fn qr(a: u32, b: u32, c: u32, d: u32) -> (r: (u32, u32, u32, u32))
    ensures r == qr_spec(a, b, c, d),
{
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 15);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 12);
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 8);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 7);
    (a, b, c, d)
}
fn main() {}
}
