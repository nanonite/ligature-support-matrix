//! `date::year_month_day_last` — the last day of a month.
//!
//! C++ (include/date/date.h:2739-2754): `day()` returns the Gregorian month
//! length from the fixed table `31,28,31,30,31,30,31,31,30,31,30,31`,
//! substituting 29 for February exactly when `year::is_leap()`; `ok()` is
//! `y_.ok() && m_.ok()`. Constraint YearMonthDayLast.C1.

use crate::day::Day;
use crate::month::Month;
use crate::year::Year;
use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic, requires};
#[cfg(creusot)]
use creusot_std::model::DeepModel;

/// The Gregorian month length in days, as a function of the month number and
/// the year. February is 29 iff the year is a leap year (`y % 4 == 0 &&
/// (y % 100 != 0 || y % 400 == 0)`), else 28; every other month is its fixed
/// table value. Months outside `[1, 12]` have no defined length and map to `0`.
///
/// Takes the year (an `Int`) rather than a leap flag so that the function
/// returns `Int`: Creusot emits `bool`-returning logic functions as opaque
/// *predicates* in dependent modules, while `Int`-returning ones are
/// transparent *functions* — and the contracts below need to compute with
/// the result.
///
/// Spelled with if-then-else rather than a literal `match` because Pearlite
/// does not support literal patterns on `Int`.
///
/// The `#[ensures]` restates the body as a *value* rather than leaving it
/// implicit, for the same reason `ok` and `ok_logic` inline their domain
/// constraints: a `#[logic]` function is only unfolded for the provers in the
/// module that defines it, so a contract in `year_month_day` that has to
/// compute with `month_length` (the day-bound of
/// [`month_day_from_doy_exact`](crate::year_month_day::month_day_from_doy_exact))
/// sees an uninterpreted function without it. Restating the body adds no
/// axiom -- the body is the table of constraint YearMonthDayLast.C1 -- it only
/// makes that table visible across the module boundary.
#[logic]
#[ensures(result == (
    if m == 2 {
        if y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) { 29 } else { 28 }
    } else if m == 4 || m == 6 || m == 9 || m == 11 {
        30
    } else if m == 1 || m == 3 || m == 5 || m == 7 || m == 8 || m == 10 || m == 12 {
        31
    } else {
        0
    }
))]
pub fn month_length(m: Int, y: Int) -> Int {
    if m == 2 {
        if y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) {
            29
        } else {
            28
        }
    } else if m == 4 || m == 6 || m == 9 || m == 11 {
        30
    } else if m == 1 || m == 3 || m == 5 || m == 7 || m == 8 || m == 10 || m == 12 {
        31
    } else {
        0
    }
}

/// The deep model of [`YearMonthDayLast`]: the record of the two components'
/// views.
///
/// A named record rather than the tuple `(Int, Int)`, for the same reason as
/// [`YearMonthDayView`](crate::year_month_day::YearMonthDayView): the
/// generated tuple record's field names are not decomposable by the provers.
///
/// No `Clone`/`Copy`/`Debug` derives: `Int` does not implement `Debug`, and
/// the view is a pure logic type that never appears in a program context.
pub struct YearMonthDayLastView {
    pub year: Int,
    pub month: Int,
}

#[cfg(creusot)]
impl DeepModel for YearMonthDayLastView {
    type DeepModelTy = YearMonthDayLastView;

    #[logic(open, inline)]
    fn deep_model(self) -> YearMonthDayLastView {
        self
    }
}

#[cfg(creusot)]
impl PartialEq for YearMonthDayLastView {
    // Field-wise, so the `refines` goal (this implies record equality) is
    // discharged on the clean field names.
    #[ensures(result == (
        self.year == rhs.year
        && self.month == rhs.month
    ))]
    fn eq(&self, rhs: &Self) -> bool {
        self.year == rhs.year && self.month == rhs.month
    }
}

/// The last day of a given month in a given year.
#[derive(Clone, Copy, Debug)]
pub struct YearMonthDayLast {
    pub year: Year,
    pub month: Month,
}

// Under `cfg(creusot)` the contract speaks about `deep_model` (a `#[logic]`
// item, stripped in ordinary builds), so the impls are gated.
#[cfg(not(creusot))]
impl PartialEq for YearMonthDayLast {
    fn eq(&self, other: &Self) -> bool {
        self.year == other.year && self.month == other.month
    }
}

#[cfg(creusot)]
impl PartialEq for YearMonthDayLast {
    // The derived spelling: against it the `refines` goal is `P -> P`, so it
    // no longer needs the provers to decompose tuple record equality.
    #[ensures(result == (self.deep_model() == other.deep_model()))]
    fn eq(&self, other: &Self) -> bool {
        self.year == other.year && self.month == other.month
    }
}

impl Eq for YearMonthDayLast {}

#[cfg(creusot)]
impl DeepModel for YearMonthDayLast {
    type DeepModelTy = YearMonthDayLastView;

    #[logic(open)]
    fn deep_model(self) -> YearMonthDayLastView {
        pearlite! { YearMonthDayLastView { year: self.year.0@, month: self.month.0@ } }
    }
}

impl YearMonthDayLast {
    /// The constructor is contract-free in C++ (`y_ / m_` stores both
    /// fields), so the port gives it the corresponding ensures: this is what
    /// makes `YearMonthDay::last`'s own contract provable.
    #[ensures(result.year.0@ == year.0@ && result.month.0@ == month.0@)]
    pub const fn new(year: Year, month: Month) -> YearMonthDayLast {
        YearMonthDayLast { year, month }
    }

    /// `year_month_day_last::ok()` — C++ `y_.ok() && m_.ok()`.
    ///
    /// `Year::ok` / `Month::ok` are spelled as associated-function paths
    /// rather than field-access method calls (`self.year.ok()`) purely so
    /// the C_static extractor can resolve the receiving concept. Neither
    /// form can dispatch dynamically: `Year` and `Month` are plain structs
    /// and `ok` is an inherent method, so this is an edit to the spelling
    /// of the call, not to the call graph it describes.
    pub const fn ok(&self) -> bool {
        Year::ok(&self.year) && Month::ok(&self.month)
    }

    /// `year_month_day_last::day()` — the month length.
    ///
    /// Constraint YearMonthDayLast.C1: returns `31,28,31,30,31,30,31,31,30,
    /// 31,30,31` for months 1..12, with February replaced by 29 exactly when
    /// `year::is_leap()` (`y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)`).
    ///
    /// The precondition scopes the contract to the month domain C1 talks
    /// about. The C++ is total: for an out-of-range month `day()` returns
    /// `day{29}` (the array-index branch is guarded by `mdl_.ok()`), and this
    /// port keeps that behavior — the `else` arm below — outside the contract.
    ///
    /// The body is spelled with if-then-else, matching the C++ fixed table
    /// value for value; the array spelling `d[month-1]` would index out of
    /// bounds for month 0 and cannot express the C++ quirk directly.
    ///
    /// `Year::is_leap` is spelled as an associated-function path for the
    /// same C_static-extraction reason as in `ok` above.
    #[requires(1 <= self.month.0@ && self.month.0@ <= 12)]
    #[ensures(result.0@ == month_length(self.month.0@, self.year.0@))]
    pub const fn day(&self) -> Day {
        let m = self.month.0;
        let leap = Year::is_leap(&self.year);
        if m == 2 {
            Day(if leap { 29 } else { 28 })
        } else if m == 4 || m == 6 || m == 9 || m == 11 {
            Day(30)
        } else if m == 1 || m == 3 || m == 5 || m == 7 || m == 8 || m == 10 || m == 12 {
            Day(31)
        } else {
            Day(29)
        }
    }
}
