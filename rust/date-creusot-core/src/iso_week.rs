//! `iso_week::weekday` — the ISO 8601 weekday (Monday = 1 .. Sunday = 7).
//!
//! C++ (include/date/iso_week.h:422-445): the only representational difference
//! from `date::weekday` is the pair `to_iso_encoding(z) = z != 0 ? z : 7` and
//! `from_iso_encoding(u) = u != 7 ? u : 0`, which are mutual inverses on
//! `[0, 7]`; `weekday_from_days(int z)` is the two-branch spelling
//! `to_iso_encoding((unsigned char)((z >= -4 ? (z+4) % 7 : (z+5) % 7 + 6)))`,
//! which differs from the `date::weekday` spelling in the negative branch yet
//! yields the same ISO weekday for every `z` (evidence E-7, E-8, E-13;
//! constraints IsoWeek.C1, C2).

#[cfg(creusot)]
use crate::euclid_mod7;
use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// `iso_week::weekday::to_iso_encoding(z)` — `z != 0 ? z : 7`.
#[ensures(result@ == (if z@ == 0 { 7 } else { z@ }))]
pub const fn to_iso_encoding(z: u8) -> u8 {
    if z == 0 {
        7
    } else {
        z
    }
}

/// `iso_week::weekday::from_iso_encoding(u)` — `u != 7 ? u : 0`.
#[ensures(result@ == (if u@ == 7 { 0 } else { u@ }))]
pub const fn from_iso_encoding(u: u8) -> u8 {
    if u == 7 {
        0
    } else {
        u
    }
}

/// `iso_week::weekday::weekday_from_days(z)` — the ISO 8601 weekday in
/// `[1, 7]` with Monday = 1 and Sunday = 7.
///
/// Constraint IsoWeek.C1: the result is in `[1, 7]` and equals
/// `to_iso_encoding` of the same base day number `date::weekday` uses.
///
/// The implementation uses the overflow-free spelling
/// `to_iso_encoding(euclid_mod7(z + 4))`. It is behaviorally identical to the
/// C++ two-branch spelling for every `int z`: the C++ computes
/// `to_iso_encoding((z >= -4 ? (z+4) % 7 : (z+5) % 7 + 6))` with signed
/// truncating `%`, and both branches equal the Euclidean `(z + 4) mod 7`
/// (which is in `[0, 6]`), and `to_iso_encoding` maps `0` to `7` — so the
/// result is the ISO weekday `(z + 4) mod 7` with `0` re-encoded as `7`.
#[ensures({
    let m = euclid_mod7(z@ + 4);
    result@ == (if m == 0 { 7 } else { m })
})]
pub const fn weekday_from_days(z: i32) -> u8 {
    let m = ((((z as i64 + 4) % 7) + 7) % 7) as u8;
    to_iso_encoding(m)
}

/// An ISO week weekday. The inner `u8` is in `[1, 7]` (`ok()`), with
/// Monday = 1 .. Sunday = 7.
///
/// `PartialEq`/`Eq` are hand-written rather than derived: the built-in
/// derives under `cfg(creusot)` require `DeepModel`, which this type does
/// not need (no contract takes its view).
#[derive(Clone, Copy, Debug)]
pub struct IsoWeekday(pub u8);

impl PartialEq for IsoWeekday {
    #[ensures(result == (self.deep_model() == other.deep_model()))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for IsoWeekday {}

impl DeepModel for IsoWeekday {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}

impl IsoWeekday {
    /// `iso_week::weekday::weekday(unsigned wd)` — identity (0 is not a
    /// representable ISO weekday; `ok()` is `1 <= wd_ && wd_ <= 7`).
    #[ensures(result.0@ == wd@)]
    pub const fn new(wd: u8) -> IsoWeekday {
        IsoWeekday(wd)
    }

    /// `iso_week::weekday::ok()` — true exactly for `1 <= wd_ <= 7`.
    #[ensures(result == (1 <= self.0@ && self.0@ <= 7))]
    pub const fn ok(&self) -> bool {
        1 <= self.0 && self.0 <= 7
    }

    /// The converting constructor `iso_week::weekday(date::weekday)` —
    /// `date::weekday::iso_encoding()`.
    #[ensures(result.0@ == (if wd.0@ == 0 { 7 } else { wd.0@ }))]
    pub const fn from_weekday(wd: crate::weekday::Weekday) -> IsoWeekday {
        IsoWeekday(to_iso_encoding(wd.0))
    }

    /// `operator date::weekday()` — `from_iso_encoding`.
    #[ensures(result.0@ == (if self.0@ == 7 { 0 } else { self.0@ }))]
    pub const fn to_weekday(&self) -> crate::weekday::Weekday {
        crate::weekday::Weekday(from_iso_encoding(self.0))
    }
}
