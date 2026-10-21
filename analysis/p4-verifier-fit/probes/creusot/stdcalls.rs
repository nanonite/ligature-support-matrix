#![allow(unused)]
use creusot_std::prelude::*;
pub fn c_len(s: &[u8]) -> usize { s.len() }
pub fn c_is_empty(s: &[u8]) -> bool { s.is_empty() }
pub fn c_copy_from_slice(d: &mut [u8; 4], s: &[u8; 4]) { d.copy_from_slice(s) }
pub fn c_to_le_bytes(x: u32) -> [u8; 4] { x.to_le_bytes() }
pub fn c_from_le_bytes(b: [u8; 4]) -> u32 { u32::from_le_bytes(b) }
pub fn c_rotate_left(x: u32) -> u32 { x.rotate_left(7) }
pub fn c_wrapping_add(a: u32, b: u32) -> u32 { a.wrapping_add(b) }
pub fn c_wrapping_sub(a: u64, b: u64) -> u64 { a.wrapping_sub(b) }
pub fn c_checked_add(a: usize, b: usize) -> Option<usize> { a.checked_add(b) }
pub fn c_min(a: usize, b: usize) -> usize { a.min(b) }
pub fn c_split_at(s: &[u8]) -> usize { if s.len() >= 2 { let (a, _b) = s.split_at(1); a.len() } else { 0 } }
pub fn c_with_capacity(n: usize) -> Vec<u8> { Vec::with_capacity(n) }
pub fn c_extend_from_slice(v: &mut Vec<u8>, s: &[u8]) { v.extend_from_slice(s) }
pub fn c_fill(s: &mut [u8; 4]) { s.fill(0) }
pub fn c_try_into(s: &[u8]) -> u8 { let r: Result<[u8; 2], _> = s.try_into(); match r { Ok(a) => a[0], Err(_) => 0 } }
pub fn c_ok_or(o: Option<u8>) -> Result<u8, ()> { o.ok_or(()) }
