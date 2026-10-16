//! `date::day` — a day-of-month held in a C++ `unsigned char` (u8).
//!
//! C++ (include/date/date.h:1424-1432): `day` holds `unsigned char d_`;
//! `ok()` is `1 <= d_ && d_ <= 31`. The valid domain is `[1, 31]`
//! (evidence E-12).

use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// A day of month. The inner `u8` is the C++ `unsigned char` representation;
/// the valid domain is `[1, 31]` (`ok()`).
///
/// `PartialEq`/`Eq` and `DeepModel` are hand-written rather than derived:
/// the built-in derives under `cfg(creusot)` require the deep-model type to
/// implement `PartialEq`/`OrdLogic`, which a generated wrapper struct does
/// not.
#[derive(Clone, Copy, Debug)]
pub struct Day(pub u8);

impl PartialEq for Day {
    // Field-view spelling, not `self.deep_model() == other.deep_model()`:
    // the two are equal (`DeepModel for Day` is `self.0@`), but the
    // view spelling is what downstream modules can connect to the tuple
    // view when proving `PartialEq::eq` refinement for tuple-typed
    // newtypes (`YearMonthDay`).
    #[ensures(result == (self.0@ == other.0@))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for Day {}

impl Day {
    /// `day::ok()` — true exactly for days 1..=31.
    #[ensures(result == (1 <= self.0@ && self.0@ <= 31))]
    pub const fn ok(&self) -> bool {
        1 <= self.0 && self.0 <= 31
    }

    /// Logic twin of `ok`, for use in contracts (program functions cannot be
    /// called in a logic context, so contracts name the twin).
    #[logic]
    pub fn ok_logic(self) -> bool {
        pearlite! { 1 <= self.0@ && self.0@ <= 31 }
    }
}

impl DeepModel for Day {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}
