//! #158 probe: P3's core-functional primitives in Creusot.
use creusot_std::prelude::*;

/// u32::wrapping_add, as P3 chacha20.rs uses it.
#[ensures(result@ == (a@ + b@) % 4294967296)]
pub fn add(a: u32, b: u32) -> u32 {
    a.wrapping_add(b)
}

/// u32::rotate_left, as P3 chacha20.rs uses it.
#[bitwise_proof]
#[ensures(result == (x << 16u32) | (x >> 16u32))]
pub fn rot16(x: u32) -> u32 {
    x.rotate_left(16)
}

/// RFC 8439 section 2.1, over u32 logic (`+` on u32 is wrapping in logic).
#[logic(open)]
pub fn rotl(x: u32, n: u32) -> u32 {
    (x << n) | (x >> (32u32 - n))
}

#[logic(open)]
pub fn qr_spec(a: u32, b: u32, c: u32, d: u32) -> (u32, u32, u32, u32) {
    pearlite! {
        let a = a + b; let d = rotl(d ^ a, 16u32);
        let c = c + d; let b = rotl(b ^ c, 12u32);
        let a = a + b; let d = rotl(d ^ a, 8u32);
        let c = c + d; let b = rotl(b ^ c, 7u32);
        (a, b, c, d)
    }
}

#[bitwise_proof]
#[requires(0u32 < n && n < 32u32)]
#[ensures(result == rotl(x, n))]
pub fn rotl_exec(x: u32, n: u32) -> u32 {
    (x << n) | (x >> (32 - n))
}

/// The same steps as P3 quarter_round, with rotation written as shifts.
#[bitwise_proof]
#[ensures(result == qr_spec(a, b, c, d))]
pub fn qr(a: u32, b: u32, c: u32, d: u32) -> (u32, u32, u32, u32) {
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 16);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 12);
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 8);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 7);
    (a, b, c, d)
}

/// u32::from_le_bytes, as P3 load_u32_le uses it.
#[ensures(result@ == b0@ + 256 * b1@ + 65536 * b2@ + 16777216 * b3@)]
pub fn load_u32_le(b0: u8, b1: u8, b2: u8, b3: u8) -> u32 {
    u32::from_le_bytes([b0, b1, b2, b3])
}

/// Poly1305 d0 (P3 poly1305.rs process_block): 26-bit limbs, h_i < 2^27, r_i < 2^26.
#[requires(h0@ < 134217728 && h1@ < 134217728 && h2@ < 134217728 && h3@ < 134217728 && h4@ < 134217728)]
#[requires(r0@ < 67108864 && r1@ < 67108864 && r2@ < 67108864 && r3@ < 67108864 && r4@ < 67108864)]
pub fn d0(h0: u64, h1: u64, h2: u64, h3: u64, h4: u64, r0: u64, r1: u64, r2: u64, r3: u64, r4: u64) -> u64 {
    let s1 = r1 * 5;
    let s2 = r2 * 5;
    let s3 = r3 * 5;
    let s4 = r4 * 5;
    h0 * r0 + h1 * s4 + h2 * s3 + h3 * s2 + h4 * s1
}

/// Control: limbs up to 2^40 can overflow u64; this must NOT prove.
#[requires(h0@ < 1099511627776 && h1@ < 1099511627776 && h2@ < 1099511627776 && h3@ < 1099511627776 && h4@ < 1099511627776)]
#[requires(r0@ < 67108864 && r1@ < 67108864 && r2@ < 67108864 && r3@ < 67108864 && r4@ < 67108864)]
pub fn d0_mutant(h0: u64, h1: u64, h2: u64, h3: u64, h4: u64, r0: u64, r1: u64, r2: u64, r3: u64, r4: u64) -> u64 {
    let s1 = r1 * 5;
    let s2 = r2 * 5;
    let s3 = r3 * 5;
    let s4 = r4 * 5;
    h0 * r0 + h1 * s4 + h2 * s3 + h3 * s2 + h4 * s1
}

/// Control: the first rotation by 15 instead of 16; this must NOT prove.
#[bitwise_proof]
#[ensures(result == qr_spec(a, b, c, d))]
pub fn qr_mutant(a: u32, b: u32, c: u32, d: u32) -> (u32, u32, u32, u32) {
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 15);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 12);
    let a = a.wrapping_add(b); let d = rotl_exec(d ^ a, 8);
    let c = c.wrapping_add(d); let b = rotl_exec(b ^ c, 7);
    (a, b, c, d)
}
