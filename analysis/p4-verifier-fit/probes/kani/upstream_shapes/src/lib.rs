//! #157 probe: the two Abseil shapes P2 scoped out (#35, #36), written the
//! way upstream does them, to see what a Kani-owned cluster would verify.
//! - `GroupSse2Impl::Match` / `MaskEmptyOrDeleted`
//!   (absl/container/internal/hashtable_control_bytes.h:277-315).
//! - Raw, uninitialized slot storage indexed by control bytes
//!   (absl/container/internal/raw_hash_set.h:67-79).
#![allow(clippy::missing_safety_doc)]
use core::arch::x86_64::*;
use core::mem::MaybeUninit;

pub const EMPTY: i8 = -128;
pub const DELETED: i8 = -2;
pub const SENTINEL: i8 = -1;

/// Bitmask of lanes whose control byte equals `h2` (SSE2, 16 lanes).
pub fn match_sse2(ctrl: &[i8; 16], h2: i8) -> u16 {
    unsafe {
        let g = _mm_loadu_si128(ctrl.as_ptr() as *const __m128i);
        _mm_movemask_epi8(_mm_cmpeq_epi8(_mm_set1_epi8(h2), g)) as u16
    }
}

/// Bitmask of lanes that are empty or deleted: both sort below the sentinel.
pub fn mask_empty_or_deleted_sse2(ctrl: &[i8; 16]) -> u16 {
    unsafe {
        let g = _mm_loadu_si128(ctrl.as_ptr() as *const __m128i);
        _mm_movemask_epi8(_mm_cmpgt_epi8(_mm_set1_epi8(SENTINEL), g)) as u16
    }
}

pub fn match_scalar(ctrl: &[i8; 16], h2: i8) -> u16 {
    let mut r = 0u16;
    for i in 0..16 {
        if ctrl[i] == h2 {
            r |= 1 << i;
        }
    }
    r
}

pub fn mask_empty_or_deleted_scalar(ctrl: &[i8; 16]) -> u16 {
    let mut r = 0u16;
    for i in 0..16 {
        if ctrl[i] == EMPTY || ctrl[i] == DELETED {
            r |= 1 << i;
        }
    }
    r
}

/// Four raw slots; a slot holds a live value exactly when its control byte is full (>= 0).
pub struct RawSlots {
    pub ctrl: [i8; 4],
    slots: [MaybeUninit<u64>; 4],
}

impl RawSlots {
    pub fn new() -> Self {
        RawSlots { ctrl: [EMPTY; 4], slots: [MaybeUninit::uninit(); 4] }
    }
    pub fn insert(&mut self, i: usize, h2: i8, v: u64) {
        assert!(i < 4 && h2 >= 0);
        self.slots[i].write(v);
        self.ctrl[i] = h2;
    }
    pub fn erase(&mut self, i: usize) {
        assert!(i < 4 && self.ctrl[i] >= 0);
        self.ctrl[i] = DELETED;
    }
    pub fn get(&self, i: usize) -> Option<u64> {
        if self.ctrl[i] >= 0 { Some(unsafe { self.slots[i].assume_init_read() }) } else { None }
    }
    /// Bug on purpose: ignores the control byte.
    pub fn get_unchecked(&self, i: usize) -> u64 {
        unsafe { self.slots[i].assume_init_read() }
    }
}

#[cfg(kani)]
mod proofs {
    use super::*;

    #[kani::proof]
    #[kani::unwind(17)]
    fn sse2_match_equals_scalar() {
        let ctrl: [i8; 16] = kani::any();
        let h2: i8 = kani::any();
        kani::assume(h2 >= 0);
        assert_eq!(match_sse2(&ctrl, h2), match_scalar(&ctrl, h2));
    }

    /// Only valid control bytes: empty, deleted, sentinel, or a full h2 in 0..=127.
    #[kani::proof]
    #[kani::unwind(17)]
    fn sse2_empty_or_deleted_equals_scalar() {
        let ctrl: [i8; 16] = kani::any();
        for i in 0..16 {
            kani::assume(ctrl[i] >= 0 || ctrl[i] == EMPTY || ctrl[i] == DELETED || ctrl[i] == SENTINEL);
        }
        assert_eq!(mask_empty_or_deleted_sse2(&ctrl), mask_empty_or_deleted_scalar(&ctrl));
    }

    #[kani::proof]
    fn raw_slots_insert_get_erase() {
        let mut s = RawSlots::new();
        let i: usize = kani::any();
        let j: usize = kani::any();
        let h2: i8 = kani::any();
        let v: u64 = kani::any();
        kani::assume(i < 4 && j < 4 && i != j && h2 >= 0);
        s.insert(i, h2, v);
        assert_eq!(s.get(i), Some(v));
        assert_eq!(s.get(j), None);
        s.erase(i);
        assert_eq!(s.get(i), None);
    }

    /// Must FAIL under -Z uninit-checks: reads a slot that was never written.
    #[kani::proof]
    fn raw_slots_uninit_read_mutant() {
        let s = RawSlots::new();
        let i: usize = kani::any();
        kani::assume(i < 4);
        let _ = s.get_unchecked(i);
    }
}
