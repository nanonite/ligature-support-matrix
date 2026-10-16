//! `date::weekday` — day of week held in a C++ `unsigned char` (u8).
//!
//! C++ (include/date/date.h:1826-1890): `weekday` holds `unsigned char wd_`;
//! the constructor `weekday(unsigned wd)` maps `7` to `0`; `ok()` is
//! `wd_ <= 6`; `c_encoding()` returns `wd_` (Sunday = 0); `iso_encoding()`
//! returns `wd_ == 0 ? 7 : wd_` (ISO 8601, Monday = 1 .. Sunday = 7);
//! `weekday_from_days(int z)` is the two-branch spelling
//! `z >= -4 ? (u+4) % 7 : u % 7` over `u = (unsigned)z`, which works around
//! C++ truncating division and equals `(z + 4) mod 7` under mathematical
//! modulo for every `int z` (evidence E-3, E-13; constraints Weekday.C1-C3).

use crate::days::Days;
#[cfg(creusot)]
use crate::euclid_mod7;
use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// `date::weekday::weekday_from_days(z)` — the day of week in `[0, 6]` with
/// 0 = Sunday, as a function of the epoch day count `z`.
///
/// Constraint Weekday.C1: the result is in `[0, 6]` and equals `(z + 4) mod 7`
/// under mathematical (Euclidean) modulo, for every `int z`.
///
/// The implementation uses the overflow-free spelling `((z + 4) % 7 + 7) % 7`
/// computed in `i64`. It is behaviorally identical to the C++ two-branch
/// unsigned-reinterpretation spelling for every `int z`:
///
/// * `z >= -4`: the C++ computes `((z as u32) + 4) mod 2^32 mod 7`. For
///   `z >= 0` the `u32` sum never wraps (`z + 4 <= i32::MAX + 4 < 2^32`), so
///   the result is `(z + 4) mod 7`. For `z` in `[-4, -1]` the `u32` sum wraps
///   to exactly `z + 4` (in `[0, 3]`), so the result is again `(z + 4) mod 7`.
///   The `i64` spelling gives `(z + 4) % 7` directly (non-negative operand).
/// * `z < -4`: the C++ computes `(z as u32) mod 7 = (z + 2^32) mod 7 =
///   (z + 4) mod 7` because `2^32 ≡ 4 (mod 7)`. The `i64` spelling computes
///   `((z + 4) % 7 + 7) % 7`, which is the Euclidean `(z + 4) mod 7`.
///
/// Both spellings therefore return the Euclidean `(z + 4) mod 7` for all `z`.
#[ensures(result@ == euclid_mod7(z@ + 4))]
pub const fn weekday_from_days(z: i32) -> u8 {
    ((((z as i64 + 4) % 7) + 7) % 7) as u8
}

/// A weekday. The inner `u8` is the C++ `unsigned char wd_`; the valid
/// domain is `[0, 6]` (`ok()`), with 0 = Sunday.
///
/// `PartialEq`/`Eq` are hand-written rather than derived: the built-in
/// derives under `cfg(creusot)` require `DeepModel`, which this type does
/// not need (no contract takes its view).
#[derive(Clone, Copy, Debug)]
pub struct Weekday(pub u8);

impl PartialEq for Weekday {
    #[ensures(result == (self.deep_model() == other.deep_model()))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for Weekday {}

impl DeepModel for Weekday {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}

impl Weekday {
    /// `weekday::weekday(unsigned wd)` — maps `7` to `0`, else the identity.
    #[ensures(result.0@ == (if wd@ == 7 { 0 } else { wd@ }))]
    pub const fn new(wd: u8) -> Weekday {
        Weekday(if wd == 7 { 0 } else { wd })
    }

    /// `weekday::weekday(sys_days)` — `weekday_from_days` of the day count.
    #[ensures(result.0@ == euclid_mod7(days.0@ + 4))]
    pub const fn from_days(days: Days) -> Weekday {
        Weekday(weekday_from_days(days.0))
    }

    /// `weekday::ok()` — true exactly for `wd_ <= 6`.
    #[ensures(result == (self.0@ <= 6))]
    pub const fn ok(&self) -> bool {
        self.0 <= 6
    }

    /// `weekday::c_encoding()` — the raw encoding, Sunday = 0 .. Saturday = 6.
    ///
    /// Constraint Weekday.C2: `date::weekday` encodes Sunday as 0 and the
    /// weekdays as 1..6; the epoch instant 1970-01-01 encodes as 4
    /// (Thursday), which follows from `weekday_from_days(0) = 4`.
    #[ensures(result@ == self.0@)]
    pub const fn c_encoding(&self) -> u8 {
        self.0
    }

    /// `weekday::iso_encoding()` — the ISO 8601 encoding, Monday = 1 ..
    /// Sunday = 7; `c_encoding()` with 0 mapped to 7.
    ///
    /// Constraint Weekday.C3.
    #[ensures(result@ == (if self.0@ == 0 { 7 } else { self.0@ }))]
    pub const fn iso_encoding(&self) -> u8 {
        if self.0 == 0 {
            7
        } else {
            self.0
        }
    }
}
