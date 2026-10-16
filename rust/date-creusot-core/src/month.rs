//! `date::month` — a month held in a C++ `unsigned char` (u8).
//!
//! C++ (include/date/date.h:1545-1570): `month` holds `unsigned char m_`;
//! `ok()` is `1 <= m_ && m_ <= 12`. The valid domain is `[1, 12]`
//! (evidence E-12).

use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// A month. The inner `u8` is the C++ `unsigned char` representation; the
/// valid domain is `[1, 12]` (`ok()`).
///
/// `PartialEq`/`Eq` and `DeepModel` are hand-written rather than derived:
/// the built-in derives under `cfg(creusot)` require the deep-model type to
/// implement `PartialEq`/`OrdLogic`, which a generated wrapper struct does
/// not.
#[derive(Clone, Copy, Debug)]
pub struct Month(pub u8);

impl PartialEq for Month {
    // Field-view spelling, not `self.deep_model() == other.deep_model()`:
    // the two are equal (`DeepModel for Month` is `self.0@`), but the
    // view spelling is what downstream modules can connect to the tuple
    // view when proving `PartialEq::eq` refinement for tuple-typed
    // newtypes (`YearMonthDay`, `YearMonthDayLast`).
    #[ensures(result == (self.0@ == other.0@))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for Month {}

#[allow(non_upper_case_globals)]
impl Month {
    pub const January: Month = Month(1);
    pub const February: Month = Month(2);
    pub const March: Month = Month(3);
    pub const April: Month = Month(4);
    pub const May: Month = Month(5);
    pub const June: Month = Month(6);
    pub const July: Month = Month(7);
    pub const August: Month = Month(8);
    pub const September: Month = Month(9);
    pub const October: Month = Month(10);
    pub const November: Month = Month(11);
    pub const December: Month = Month(12);

    /// `month::ok()` — true exactly for months 1..=12.
    #[ensures(result == (1 <= self.0@ && self.0@ <= 12))]
    pub const fn ok(&self) -> bool {
        1 <= self.0 && self.0 <= 12
    }

    /// Logic twin of `ok`, for use in contracts (program functions cannot be
    /// called in a logic context, so contracts name the twin).
    #[logic]
    pub fn ok_logic(self) -> bool {
        pearlite! { 1 <= self.0@ && self.0@ <= 12 }
    }
}

impl DeepModel for Month {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}
