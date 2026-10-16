//! Rust port of the HowardHinnant/date calendar subset, with Creusot annotations.
//!
//! Subset (per the pilot's concept analysis): `days_from_civil`, `civil_from_days`
//! (the era arithmetic behind `year_month_day::{to_days, from_days}`),
//! `date::weekday` (`weekday_from_days`, `c_encoding`, `iso_encoding`),
//! `year_month_day::ok`, `year_month_day_last::day`, and `iso_week::weekday`.
//!
//! The port is behaviorally compatible with the pinned C++ (commit
//! `179a6b921ccd6179b5b04dce812a89f71a51b4df`), including the bug-compat
//! behaviors recorded in the evidence (E-15: `to_days` is total and normalizes
//! out-of-range days; the C++ truncating-division spellings).
//!
//! Module order is suppliers-first: the newtypes (`Year`, `Month`, `Day`,
//! `Days`) come before `Weekday`, which comes before `YearMonthDayLast`,
//! which comes before `YearMonthDay`, which comes before `IsoWeek`.
//!
//! All functions are `const fn`, mirroring the C++ `CONSTCD14`/`CONSTCD11`
//! annotations (E-11).

pub mod day;
pub mod days;
pub mod iso_week;
pub mod month;
pub mod weekday;
pub mod year;
pub mod year_month_day;
pub mod year_month_day_last;

pub use day::Day;
pub use days::Days;
pub use month::Month;
pub use weekday::{weekday_from_days, Weekday};
pub use year::Year;
pub use year_month_day::YearMonthDay;
pub use year_month_day_last::YearMonthDayLast;

// `#[logic]` items are stripped in non-Creusot builds, so the imports they
// need are gated on `cfg(creusot)` to keep plain `cargo build` warning-free.
#[cfg(creusot)]
use creusot_std::logic::Int;
#[cfg(creusot)]
use creusot_std::macros::{ensures, logic};

/// Euclidean (always non-negative) remainder mod 7, as a `Int` logic function.
///
/// `date::weekday::weekday_from_days` is specified (Weekday.C1) as
/// `(z + 4) mod 7` under mathematical modulo; the C++ two-branch spelling with
/// an unsigned reinterpretation computes exactly this for every `int z`
/// (verified against the pinned header, evidence E-13).
#[cfg(creusot)]
#[logic]
#[ensures(result >= 0 && result < 7)]
pub fn euclid_mod7(a: Int) -> Int {
    a.rem_euclid(7)
}
