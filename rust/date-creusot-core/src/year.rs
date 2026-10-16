//! `date::year` — a proleptic Gregorian year held in a C++ `short` (i16).
//!
//! C++ (include/date/date.h:401-427): `year` holds a `short y_`; the
//! constructor `year(int y)` static-casts to `short`; `ok()` rejects exactly
//! one value, `-32768` (`std::numeric_limits<short>::min()`); `is_leap()` is
//! `y_ % 4 == 0 && (y_ % 100 != 0 || y_ % 400 == 0)`. The representable year
//! domain for every calendar function in the subset is therefore
//! `[-32767, 32767]` (evidence E-12, constraint YearMonthDayLast.C2).

use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// A year. The inner `i16` is the C++ `short` representation; the valid
/// domain is `[-32767, 32767]` (`ok()`).
///
/// `PartialEq`/`Eq` and `DeepModel` are hand-written rather than derived:
/// the built-in derives under `cfg(creusot)` require the deep-model type to
/// implement `PartialEq`/`OrdLogic`, which a generated wrapper struct does
/// not.
#[derive(Clone, Copy, Debug)]
pub struct Year(pub i16);

impl PartialEq for Year {
    // Field-view spelling, not `self.deep_model() == other.deep_model()`:
    // the two are equal (`DeepModel for Year` is `self.0@`), but the
    // view spelling is what downstream modules can connect to the tuple
    // view when proving `PartialEq::eq` refinement for tuple-typed
    // newtypes (`YearMonthDay`, `YearMonthDayLast`).
    #[ensures(result == (self.0@ == other.0@))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for Year {}

impl Year {
    /// `year::min()` — C++ `year{-32767}`.
    pub const MIN: Year = Year(-32767);
    /// `year::max()` — C++ `year{32767}`.
    pub const MAX: Year = Year(32767);

    /// `year::ok()` — true except for the single value `-32768`.
    ///
    /// Constraint YearMonthDayLast.C2: the representable year domain is
    /// `[-32767, 32767]` and `ok()` rejects exactly `-32768`.
    #[ensures(result == (self.0@ != -32768))]
    pub const fn ok(&self) -> bool {
        self.0 != i16::MIN
    }

    /// Logic twin of `ok`, for use in contracts (program functions cannot be
    /// called in a logic context, so contracts name the twin).
    #[logic]
    pub fn ok_logic(self) -> bool {
        pearlite! { self.0@ != -32768 }
    }

    /// `year::is_leap()` — the Gregorian leap rule.
    ///
    /// C++ uses truncating `%` on the promoted `short`; Rust's `%` on `i16`
    /// is also truncating, so the spelling is identical and the result agrees
    /// for every year in the domain (e.g. 2000 is leap, 1900 and 2100 are
    /// not — evidence E-5/E-9).
    #[ensures(
        result == (self.0@ % 4 == 0 && (self.0@ % 100 != 0 || self.0@ % 400 == 0))
    )]
    pub const fn is_leap(&self) -> bool {
        self.0 % 4 == 0 && (self.0 % 100 != 0 || self.0 % 400 == 0)
    }

    /// Logic twin of `is_leap`, for use in contracts.
    #[logic]
    pub fn is_leap_logic(self) -> bool {
        pearlite! { self.0@ % 4 == 0 && (self.0@ % 100 != 0 || self.0@ % 400 == 0) }
    }
}

impl DeepModel for Year {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}
