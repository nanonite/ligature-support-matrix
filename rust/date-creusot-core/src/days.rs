//! `date::days` — an epoch day count held in a C++ `int` (i32).
//!
//! C++ (include/date/date.h:182-183): `days` is
//! `std::chrono::duration<int, ratio_multiply<ratio<24>, hours::period>>`,
//! so `days::rep` is a 32-bit `int` and `count()` returns it. Over the
//! representable year domain `[-32767, 32767]` the value stays within
//! `[-12687428, 11248737]` and never overflows (evidence E-6, E-12, E-14;
//! constraint YearMonthDay.C5).
//!
//! `PartialEq`/`Eq` and `DeepModel` are hand-written rather than derived:
//! the built-in derives under `cfg(creusot)` require the deep-model type to
//! implement `PartialEq`/`OrdLogic`, which a generated wrapper struct does
//! not.

use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic};
use creusot_std::model::DeepModel;

/// An epoch day count (days since 1970-01-01). The inner `i32` is the C++
/// `days::rep`.
#[derive(Clone, Copy, Debug)]
pub struct Days(pub i32);

impl PartialEq for Days {
    #[ensures(result == (self.deep_model() == other.deep_model()))]
    fn eq(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}

impl Eq for Days {}

impl DeepModel for Days {
    type DeepModelTy = Int;

    #[logic]
    fn deep_model(self) -> Self::DeepModelTy {
        pearlite! { self.0@ }
    }
}
