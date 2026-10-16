//! `date::year_month_day` — the proleptic Gregorian date and the era
//! arithmetic (`days_from_civil` / `civil_from_days`).
//!
//! C++ (include/date/date.h:2976-3109): `to_days()` computes
//! `era*146097 + doe - 719468` from a 400-year era decomposition (the
//! algorithm the plan names `days_from_civil`); `from_days()` decomposes an
//! epoch day count back into era, day-of-era, year-of-era, day-of-year and
//! month index (`civil_from_days`). Both are `CONSTCD14` and guarded by
//! `static_assert`s requiring `unsigned` >= 18 and `int` >= 20 digits
//! (evidence E-1, E-2, E-6; constraints YearMonthDay.C1, C2, C5, C6).
//!
//! The port computes in `i32` throughout. Over the valid domain
//! (year in `[-32767, 32767]`, month in `[1, 12]`, day in `[1, 31]`) every
//! intermediate stays far inside `i32` (evidence E-14, E-15), so the `i32`
//! spelling is behaviorally identical to the C++ (which relies on `unsigned`
//! wraparound only for values that never occur in the valid domain).

use crate::days::Days;
use crate::month::Month;
use crate::year::Year;
use crate::year_month_day_last::YearMonthDayLast;
use creusot_std::logic::Int;
use creusot_std::macros::{ensures, logic, requires};
#[cfg(creusot)]
use creusot_std::model::DeepModel;

/// `days_from_civil(y, m, d)` — the forward era arithmetic, as a logic
/// function over mathematical integers.
///
/// Mirrors the C++ spelling exactly (truncating `/` on `Int` is
/// `int.ComputerDivision.div`, matching the C++ `int` division):
/// `y` is decremented for January and February, `era = (y >= 0 ? y : y-399)/400`
/// is the 400-year era, `yoe` the year of era `[0, 399]`, `doy` the day of
/// the era-year `[0, 365]` (March 1 is day 0), `doe` the day of era
/// `[0, 146096]`, and the result `era*146097 + doe - 719468`.
#[logic]
pub fn days_from_civil(y: Int, m: Int, d: Int) -> Int {
    let y = y - if m <= 2 { 1 } else { 0 };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

/// The month/day recovery from a day-of-era-year, as a logic function.
///
/// C++: `mp = (5*doy + 2)/153` in `[0, 11]`, `d = doy - (153*mp+2)/5 + 1` in
/// `[1, 31]`, `m = mp < 10 ? mp+3 : mp-9` in `[1, 12]`.
#[logic]
#[requires(doy >= 0 && doy <= 365)]
#[ensures(result.0 >= 1 && result.0 <= 12 && result.1 >= 1 && result.1 <= 31)]
pub fn month_day_from_doy(doy: Int) -> (Int, Int) {
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (m, d)
}

/// The year-of-era recovery from a day-of-era, as a logic function.
///
/// C++: `yoe = (doe - doe/1460 + doe/36524 - doe/146096)/365` in `[0, 399]`.
#[logic]
#[requires(doe >= 0 && doe <= 146096)]
#[ensures(
    result >= 0 && result <= 399
    && doe - (365 * result + result / 4 - result / 100) >= 0
    && doe - (365 * result + result / 4 - result / 100) <= 365
)]
pub fn year_of_era_from_doe(doe: Int) -> Int {
    (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365
}

/// The first day of era-year `yoe` (March 1 of the March-based year `yoe`),
/// as a day-of-era. The `yoe/4 - yoe/100` term is the accumulated leap-day
/// count: the forward formula's `doe` offset, with `doy == 0`.
#[logic]
pub fn era_year_start(yoe: Int) -> Int {
    365 * yoe + yoe / 4 - yoe / 100
}

/// Whether `doy` is a real day of era-year `yoe`.
///
/// An era-year runs from 1 March of the March-based year `yoe` to the end of
/// February of `yoe + 1`, so it has 365 days, or 366 when the civil year
/// `yoe + 1` is a Gregorian leap year. Spelled over `yoe % 4` and the three
/// century era-years rather than as `doy < era_year_length(yoe)` because that
/// is the shape the proof consumes: `doy == 365` is 29 February, and 29
/// February of year `yoe + 1` exists exactly when `yoe` is a leap era-year,
/// i.e. `yoe % 4 == 3` and `yoe` is not one of the three era-years that end
/// on 28 February of a non-400 century (`99`, `199`, `299`; `399` does end on
/// 29 February 400 and is therefore *not* excluded).
///
/// A `bool` logic function so it can be named in a `#[requires]`. It is only
/// called from this module, which is where `compute_specified` can unfold it --
/// see the note on `ok_logic` in `year_month_day.rs`.
#[logic]
pub fn valid_era_day(yoe: Int, doy: Int) -> bool {
    0 <= doy
        && doy <= 365
        && (doy <= 364 || (yoe % 4 == 3 && yoe != 99 && yoe != 199 && yoe != 299))
}

/// `yoe / 100 == (yoe / 4) / 25` for `yoe` in `[0, 399]`: the century term of
/// [`era_year_start`] can be read off the 25-of-4 decomposition instead.
///
/// The forward `doe` needs this to become the mixed-radix form
/// `36524*h + 1461*u + 365*r + doy` (with `q = yoe/4 = 25*h + u`,
/// `r = yoe % 4`) that the exactness proof reasons about. Both sides are
/// bounded: `0 <= yoe <= 399` gives `q <= 99` and `4*(q % 25) + r <= 99`.
#[logic]
#[requires(yoe >= 0 && yoe <= 399)]
#[ensures(yoe / 100 == (yoe / 4) / 25)]
pub fn century_of_era_year(yoe: Int) {}

/// The three quotient counters of the year-of-era recovery, for a day-of-era
/// written in the era's mixed radix `doe = 36524*h + 1461*u + 365*r + doy`
/// (radices `(4, 25, 4, 366)`; the digits `h` and `u` index the 4-year and
/// 25-of-4 groups, `r` the position inside a 4-year group and `doy` the day).
///
/// `doe/1460` is the 4-year counter, `doe/36524` the 100-year one and
/// `doe/146096` the 400-year one -- exactly the three correction terms
/// `year_of_era_from_doe` subtracts. Each is a *carry indicator plus a base*,
/// and which carries occur is decided by the single value
/// `c = 24*h + u + 365*r + doy`, the offset past the 4-year block
/// `1460*(25*h + u) = 36500*h + 1460*u` that the 100-year counter's 24
/// leftover days per group (and hence the `-1` in `36524 = 1461*25 - 1`) put
/// there. `c` is in `[0, 1556]`, so it is below `1460` or between `1460` and
/// `2*1460 - 1`: at most one carry, never two.
#[logic]
#[requires(0 <= h && h <= 3 && 0 <= u && u <= 24 && 0 <= r && r <= 3 && 0 <= doy && doy <= 365)]
#[ensures({
    let doe = 36524 * h + 1461 * u + 365 * r + doy;
    let c = 24 * h + u + 365 * r + doy;
    if c < 1460 {
        doe / 1460 == 25 * h + u && doe / 36524 == h && doe / 146096 == 0
    } else if !(u == 24 && r == 3 && doy == 365) {
        doe / 1460 == 25 * h + u + 1 && doe / 36524 == h && doe / 146096 == 0
    } else if h == 3 {
        doe / 1460 == 25 * h + u + 1 && doe / 36524 == h + 1 && doe / 146096 == 1
    } else {
        doe / 1460 == 25 * h + u + 1 && doe / 36524 == h + 1 && doe / 146096 == 0
    }
})]
pub fn era_quotients(h: Int, u: Int, r: Int, doy: Int) {
    pearlite! {
        let c = 24 * h + u + 365 * r + doy;
        if c < 1460 {
        } else if !(u == 24 && r == 3 && doy == 365) {
        } else if h == 3 {
        } else {
        }
    }
}

/// `(365 * k + w) / 365 == k + w / 365` for `k >= 0`, `w >= 0`: the digit
/// extraction of a non-negative remainder off a multiple of 365.
///
/// Both sides non-negative is load-bearing: `Int`'s `/` is Why3's
/// `int.ComputerDivision.div`, which truncates *towards zero*, so
/// `div (k*m + w) m == k + div w m` fails as soon as `w < 0` (e.g.
/// `div (4*365 - 1) 365 == 3`, not `4 + div (-1) 365 == 4`). The
/// mixed-radix proof therefore always normalises the trailing quotient to be
/// non-negative before invoking this.
#[logic]
#[requires(k >= 0 && w >= 0)]
#[ensures((365 * k + w) / 365 == k + w / 365)]
pub fn div_365_of_nonneg_digit(k: Int, w: Int) {}

/// `(365 * r + e) / 365 == r` for `e` in `[0, 364]`: a full year plus a day
/// count inside it.
#[logic]
#[requires(r >= 0 && 0 <= e && e <= 364)]
#[ensures((365 * r + e) / 365 == r)]
pub fn div_365_of_year(r: Int, e: Int) {}

/// `(365 * k - 1) / 365 == k - 1` for `k >= 1`: the last day of an era-year
/// divides down one year short, which is what makes the 400-year era's final
/// day (`doe == 146096`, i.e. 29 February 400) come back as `yoe == 399`
/// rather than `400`.
#[logic]
#[requires(k >= 1)]
#[ensures((365 * k - 1) / 365 == k - 1)]
pub fn div_365_of_era_end(k: Int) {}

/// The era recovery, exact version: the `era` that
/// [`civil_from_days`](crate::year_month_day::civil_from_days) reads back out
/// of a day count is the `era` that [`days_from_civil`] put in.
///
/// The C++ spelling is `(z >= 0 ? z : z - 146096) / 146097`. The `- 146096`
/// is not a fixup for the truncation but the standard way of making the
/// quotient correct on negative inputs: subtracting a full era's length less
/// one pushes every negative `z` below `-146097`, so that the C-style
/// truncation towards zero and the mathematical floor coincide. The
/// consequence is that `z == era*146097 + doe` with `0 <= doe <= 146096`
/// inverts exactly, for every era including the negative ones.
#[logic]
#[requires(0 <= doe && doe <= 146096)]
#[ensures({
    let z = era * 146097 + doe;
    (if z >= 0 { z } else { z - 146096 }) / 146097 == era
})]
pub fn era_of_days(era: Int, doe: Int) {}

/// The day-of-era-year `days_from_civil` computes for month `m`, day `d`.
#[logic]
pub fn doy_from_civil(m: Int, d: Int) -> Int {
    (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1
}

/// `m` divides `x - 400 * e` if and only if `m` divides `x`, for each divisor
/// `m` of the 400-year era: subtracting whole eras cannot move a civil year
/// across a 4-, 100- or 400-year boundary.
///
/// Stated as a *divisibility* fact, not as `(x - 400*e) % m == x % m`, and the
/// distinction is not cosmetic. `Int`'s `%` is Why3's
/// `int.ComputerDivision.mod`, which truncates towards zero, so the remainder
/// keeps the sign of the dividend and `(x - 400*e) % 4 == x % 4` is simply
/// false (`x = 7, e = 1`: `-393 % 4 == -1` but `7 % 4 == 3`). "Zero or not"
/// is the part that is invariant, and it is the part the calendar argument
/// needs: `yoe = y - 1 - 400*era` is in `[0, 399]`, and it inherits
/// `(y - 1)`'s 4-year and 100-year *divisibility* -- which is what says
/// "29 February of year `y` sits in a leap era-year".
#[logic]
#[ensures(((x - 400 * e) % 4 == 0) == (x % 4 == 0))]
pub fn div_4_era_shift(x: Int, e: Int) {}

/// The century counterpart of [`div_4_era_shift`].
#[logic]
#[ensures(((x - 400 * e) % 100 == 0) == (x % 100 == 0))]
pub fn div_100_era_shift(x: Int, e: Int) {}

/// The 400-year counterpart of [`div_4_era_shift`].
#[logic]
#[ensures(((x - 400 * e) % 400 == 0) == (x % 400 == 0))]
pub fn div_400_era_shift(x: Int, e: Int) {}

/// `days_from_civil`'s `era`/`yoe` split of the (March-shifted) civil year
/// `y0` puts `yoe` in `[0, 399]`.
///
/// The `y0 - 399` in the C++ spelling is not arbitrary: it pushes every
/// negative `y0` strictly below `-400`, so that C-style truncation towards
/// zero and the mathematical floor pick the same (negative) era, and the
/// remainder `y0 - era*400` is the representative in `[0, 400)`.
#[logic]
#[ensures({
    let era = (if y0 >= 0 { y0 } else { y0 - 399 }) / 400;
    let yoe = y0 - era * 400;
    0 <= yoe && yoe <= 399
})]
pub fn yoe_of_era_year(y0: Int) {}

/// A 29 February lands in a leap era-year.
///
/// `doy == 365` means 29 February (see
/// [`doy_of_civil_bounds_feb`](crate::year_month_day::doy_of_civil_bounds_feb)),
/// and 29 February of civil year `y` exists exactly when `y` is a Gregorian
/// leap year. The era-year that contains it is `yoe = y - 1 - 400*era`, and
/// subtracting whole eras leaves `y`'s 4-, 100- and 400-year divisibility
/// alone ([`div_4_era_shift`] and friends), so the era-year inherits exactly
/// the conditions that make it a leap era-year: its low digit is `3`, and it
/// is none of the three era-years `{99, 199, 299}` that end on 28 February of
/// a non-400 century. `yoe == 399` (which ends on 29 February 400) is
/// *not* excluded, and correspondingly is not excluded here.
#[logic]
#[requires(0 <= yoe && yoe <= 399 && y == yoe + 1 + 400 * era
    && y % 4 == 0 && (y % 100 != 0 || y % 400 == 0))]
#[ensures(yoe % 4 == 3 && yoe != 99 && yoe != 199 && yoe != 299)]
pub fn leap_era_day(y: Int, yoe: Int, era: Int) {
    div_4_era_shift(y - 1, era);
    div_100_era_shift(y, era);
    div_400_era_shift(y, era);
    pearlite! {
        if yoe == 99 {
        } else if yoe == 199 {
        } else if yoe == 299 {
        } else {
        }
    }
}

/// The day-of-era-year of a *valid* civil date is in `[0, 365]`: the
/// March-based year's 366th day is 29 February, and `month_length` admits
/// `d == 29` in February only in a leap year.
#[logic]
#[requires(1 <= m && m <= 12 && 1 <= d
    && d <= crate::year_month_day_last::month_length(m, y))]
#[ensures({
    let doy = doy_from_civil(m, d);
    0 <= doy && doy <= 365 && (doy <= 364 || m == 2)
})]
pub fn doy_of_civil_bounds(y: Int, m: Int, d: Int) {
    pearlite! {
        if m == 1 {
            doy_of_civil_bounds_31(10, d);
        } else if m == 2 {
            doy_of_civil_bounds_feb(y, d);
        } else if m == 3 {
            doy_of_civil_bounds_31(0, d);
        } else if m == 4 {
            doy_of_civil_bounds_30(1, d);
        } else if m == 5 {
            doy_of_civil_bounds_31(2, d);
        } else if m == 6 {
            doy_of_civil_bounds_30(3, d);
        } else if m == 7 {
            doy_of_civil_bounds_31(4, d);
        } else if m == 8 {
            doy_of_civil_bounds_31(5, d);
        } else if m == 9 {
            doy_of_civil_bounds_30(6, d);
        } else if m == 10 {
            doy_of_civil_bounds_31(7, d);
        } else if m == 11 {
            doy_of_civil_bounds_30(8, d);
        } else {
            doy_of_civil_bounds_31(9, d);
        }
    }
}

/// `(153 * mp + 2) / 5 + d - 1` is in `[0, 364]` for a 31-day month index: no
/// 31-day month reaches `doy == 365`, which is reserved for 29 February.
#[logic]
#[requires((mp == 0 || mp == 2 || mp == 4 || mp == 5 || mp == 7 || mp == 9 || mp == 10)
    && 1 <= d && d <= 31)]
#[ensures({
    let doy = (153 * mp + 2) / 5 + d - 1;
    0 <= doy && doy <= 364
})]
pub fn doy_of_civil_bounds_31(mp: Int, d: Int) {}

/// The 30-day months: `(153 * mp + 2) / 5 + d - 1` is in `[0, 364]`.
#[logic]
#[requires((mp == 1 || mp == 3 || mp == 6 || mp == 8) && 1 <= d && d <= 30)]
#[ensures({
    let doy = (153 * mp + 2) / 5 + d - 1;
    0 <= doy && doy <= 364
})]
pub fn doy_of_civil_bounds_30(mp: Int, d: Int) {}

/// February: `(153 * 11 + 2) / 5 + d - 1` is in `[0, 365]`, and reaches `365`
/// only for `d == 29` in a leap year.
#[logic]
#[requires(1 <= d && d <= crate::year_month_day_last::month_length(2, y))]
#[ensures({
    let doy = (153 * 11 + 2) / 5 + d - 1;
    0 <= doy && doy <= 365
        && (doy <= 364 || (d == 29 && y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)))
})]
pub fn doy_of_civil_bounds_feb(y: Int, d: Int) {
    pearlite! {
        if y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) {
        } else {
        }
    }
}

/// The month and day [`month_day_from_doy`] recovers from a day-of-era-year.
///
/// Exact, like [`year_of_era_from_doe_exact`]: the `(5*doy+2)/153` division
/// has to invert `(153*mp+2)/5 + d - 1` exactly, and the two are only inverse
/// on a *day* range that depends on the month -- 29 February is `doy == 365`
/// and no other month reaches it. The precondition is the validity of the
/// civil date, so that the `month_length` table (see
/// `year_month_day_last::month_length`) pins the day range per month.
#[logic]
#[requires(1 <= m && m <= 12 && 1 <= d
    && d <= crate::year_month_day_last::month_length(m, y))]
#[ensures(month_day_from_doy(doy_from_civil(m, d)) == (m, d))]
pub fn month_day_from_doy_exact(y: Int, m: Int, d: Int) {
    // Twelve months is a finite case split the provers will not do on their
    // own; spelling it out turns the `(5*doy+2)/153` inversion into twelve
    // ground computations. The `mp` values are the March-based month index
    // `days_from_civil` uses (`m - 3` for `m > 2`, `m + 9` otherwise), and
    // the grouping is the month-length table of constraint
    // YearMonthDayLast.C1.
    if m == 1 {
        month_day_from_doy_exact_31(10, d);
    } else if m == 2 {
        month_day_from_doy_exact_feb(y, d);
    } else if m == 3 {
        month_day_from_doy_exact_31(0, d);
    } else if m == 4 {
        month_day_from_doy_exact_30(1, d);
    } else if m == 5 {
        month_day_from_doy_exact_31(2, d);
    } else if m == 6 {
        month_day_from_doy_exact_30(3, d);
    } else if m == 7 {
        month_day_from_doy_exact_31(4, d);
    } else if m == 8 {
        month_day_from_doy_exact_31(5, d);
    } else if m == 9 {
        month_day_from_doy_exact_30(6, d);
    } else if m == 10 {
        month_day_from_doy_exact_31(7, d);
    } else if m == 11 {
        month_day_from_doy_exact_30(8, d);
    } else {
        month_day_from_doy_exact_31(9, d);
    }
}

/// `month_day_from_doy` inverts `(153*mp + 2)/5 + d - 1` for the 31-day months
/// (`mp` is the March-based month index: `0` March, `2` May, `4` July, `5`
/// August, `7` October, `9` December, `10` January).
///
/// The `mp` set is the point: the inversion is only valid up to the month's
/// own length, so `(mp, d) = (1, 31)` (31 April) is *not* a case -- it is not
/// a date, and `month_day_from_doy` correctly returns May 2 for its
/// day-of-era-year.
#[logic]
#[requires((mp == 0 || mp == 2 || mp == 4 || mp == 5 || mp == 7 || mp == 9 || mp == 10)
    && 1 <= d && d <= 31)]
#[ensures(month_day_from_doy((153 * mp + 2) / 5 + d - 1) == (if mp < 10 { mp + 3 } else { mp - 9 }, d))]
pub fn month_day_from_doy_exact_31(mp: Int, d: Int) {
    // One leaf per 31-day month: with `mp` ground the two divisions involved
    // (`(153*mp+2)/5` out, `(5*doy+2)/153` back) divide constants, and the
    // provers close them by interval arithmetic on `d` alone.
    pearlite! {
        if mp == 0 {
        } else if mp == 2 {
        } else if mp == 4 {
        } else if mp == 5 {
        } else if mp == 7 {
        } else if mp == 9 {
        } else {
        }
    }
}

/// The 30-day months (`mp` in `{1, 3, 6, 8}` for April, June, September,
/// November).
#[logic]
#[requires((mp == 1 || mp == 3 || mp == 6 || mp == 8) && 1 <= d && d <= 30)]
#[ensures(month_day_from_doy((153 * mp + 2) / 5 + d - 1) == (mp + 3, d))]
pub fn month_day_from_doy_exact_30(mp: Int, d: Int) {
    pearlite! {
        if mp == 1 {
        } else if mp == 3 {
        } else if mp == 6 {
        } else {
        }
    }
}

/// February, whose length depends on whether the year is a leap year, and
/// which is the only month whose recovered `doy` can reach `365`.
#[logic]
#[requires(1 <= d
    && d <= crate::year_month_day_last::month_length(2, y))]
#[ensures(month_day_from_doy((153 * 11 + 2) / 5 + d - 1) == (2, d))]
pub fn month_day_from_doy_exact_feb(y: Int, d: Int) {}

/// The exactness (uniqueness) fact that the range-only contract of
/// [`year_of_era_from_doe`] does not give: on the days a civil date can
/// actually land on, the year-of-era recovery returns **the** `yoe` that
/// produced the day-of-era, not merely some `yoe` in `[0, 399]` consistent
/// with it.
///
/// This is the deep step of Hinnant's algorithm. `doe` is not a linear
/// function of `yoe` (the forward offset is `yoe/4 - yoe/100`), so the
/// forward map and the recovery do not invert each other by construction; the
/// argument is the mixed-radix one of Neri & Schneider, "Euclidean affine
/// functions and their application to calendar algorithms", *Software:
/// Practice and Experience* 51 (2021) -- the paper that treats exactly this
/// construction as its worked example, and the reusable source of the facts
/// that have to be *supplied* here rather than discovered automatically.
///
/// Write the era-year in 25-of-4 digits, `yoe = 4*q + r` with
/// `q = yoe/4 = 25*h + u`, so `0 <= r <= 3`, `0 <= u <= 24`, `0 <= h <= 3`
/// (a 400-year era is 25 groups of 4 years; `h` counts 25-group blocks).
/// [`century_of_era_year`] turns the forward `yoe/100` into `h`, and the
/// offset telescopes to the mixed-radix number
///
/// ```text
/// era_year_start(yoe) + doy = 36524*h + 1461*u + 365*r + doy
/// ```
///
/// i.e. the digits `[h | u | r | doy]` in radices `(4, 25, 4, 366)`. Reading
/// `doe` back in the same radix system is what the recovery does, and
/// [`era_quotients`] supplies its three counters. What is left is the final
/// `/365`, which unwinds the last two digits: the arithmetic identity
///
/// ```text
/// doe - doe/1460 + doe/36524 - doe/146096 == 365 * 4 * q + (365*r + e)
/// ```
///
/// with `e` the day offset inside the era-year, is established by
/// [`div_365_of_nonneg_digit`] and [`div_365_of_year`].
///
/// `valid_era_day(yoe, doy)` is the side condition that rules out the one
/// configuration where the last day of an era-year is numerically
/// indistinguishable from the first day of the next one --
/// `(yoe, doy)` in `{99, 199, 299} x {365}`. Without it the lemma is *false*,
/// not merely hard: `year_of_era_from_doe(era_year_start(99) + 365)` is `100`,
/// not `99`. That is the substantive content of the side condition: the
/// forward map is not injective on the whole `[0,399] x [0,365]` box -- it
/// maps `(yoe, 365)` and `(yoe + 1, 0)` to the same day-of-era whenever
/// `yoe + 1` is not a leap year -- and it is the *validity* of the civil date
/// that picks the right representative.
#[logic]
#[requires(yoe >= 0 && yoe <= 399 && valid_era_day(yoe, doy))]
#[ensures(year_of_era_from_doe(era_year_start(yoe) + doy) == yoe)]
pub fn year_of_era_from_doe_exact(yoe: Int, doy: Int) {
    pearlite! {
        let q = yoe / 4;
        let r = yoe % 4;
        let h = q / 25;
        let u = q % 25;
        let c = 24 * h + u + 365 * r + doy;
        century_of_era_year(yoe);
        era_quotients(h, u, r, doy);
        if c < 1460 {
            div_365_of_nonneg_digit(4 * q, 365 * r + doy);
            div_365_of_year(r, doy);
        } else if !(u == 24 && r == 3 && doy == 365) {
            div_365_of_nonneg_digit(4 * q, 365 * r + doy - 1);
            div_365_of_year(r, doy - 1);
        } else if h == 3 {
            // `doe == 146096`: the last day of the 400-year era. Both
            // counters carry, and the numerator lands one day short of a
            // whole number of era-years.
            div_365_of_era_end(4 * q + 4);
        } else {
            // Vacuous: `u == 24` with `h < 3` and `r == 3` is `yoe` in
            // `{99, 199, 299}`, whose `doy == 365` (29 February of a
            // non-400 century) is excluded by `valid_era_day`.
        }
    }
}

/// The era decomposition of a *valid* civil date, with the pieces the
/// exactness lemma needs: the year-of-era is in `[0, 399]` and
/// `(yoe, doy)` is a real day of that era-year.
///
/// This is the bridge between the civil side (a valid `y, m, d`) and the era
/// side (`yoe, doy`): [`yoe_of_era_year`] and [`doy_of_civil_bounds`] give the
/// ranges, and the `doy == 365` branch is the only place the civil leap rule
/// enters, through [`leap_era_day`].
#[logic]
#[requires(1 <= m && m <= 12 && 1 <= d
    && d <= crate::year_month_day_last::month_length(m, y))]
#[ensures({
    let y0 = y - (if m <= 2 { 1 } else { 0 });
    let era = (if y0 >= 0 { y0 } else { y0 - 399 }) / 400;
    let yoe = y0 - era * 400;
    let doy = doy_from_civil(m, d);
    0 <= yoe && yoe <= 399 && valid_era_day(yoe, doy)
})]
pub fn civil_parts(y: Int, m: Int, d: Int) {
    pearlite! {
        let y0 = y - (if m <= 2 { 1 } else { 0 });
        let era = (if y0 >= 0 { y0 } else { y0 - 399 }) / 400;
        let yoe = y0 - era * 400;
        let doy = doy_from_civil(m, d);
        yoe_of_era_year(y0);
        doy_of_civil_bounds(y, m, d);
        if doy == 365 {
            // 29 February: `m == 2` by `doy_of_civil_bounds`, so `doy == 365`
            // is `336 + d == 365`, i.e. `d == 29`, which `month_length(2, y)`
            // admits only in a leap year. And the era-year that holds it is
            // `yoe = y - 1 - 400*era`.
            leap_era_day(y, yoe, era);
        }
    }
}

/// The whole era arithmetic, composed: `days_from_civil` and
/// `civil_from_days` are exact inverses on every valid civil date.
///
/// Constraint YearMonthDay.C2 as one provable obligation, assembled from the
/// per-step exactness lemmas: [`civil_parts`] (the forward split is well
/// formed), [`era_of_days`] (the era is recovered), [`doe_bounds`] (the
/// day-of-era is in range), [`year_of_era_from_doe_exact`] (the year-of-era
/// and hence the day-of-year are recovered -- the deep step),
/// [`month_day_from_doy_exact`] (the month and day are recovered), and the
/// `y + (m <= 2)` re-shift, which cancels because the recovered `m` is the
/// original one.
#[logic]
#[requires(1 <= m && m <= 12 && 1 <= d
    && d <= crate::year_month_day_last::month_length(m, y))]
#[ensures({
    let c = civil_from_days(days_from_civil(y, m, d));
    c.year == y && c.month == m && c.day == d
})]
pub fn days_civil_round_trip(y: Int, m: Int, d: Int) {
    pearlite! {
        let y0 = y - (if m <= 2 { 1 } else { 0 });
        let era = (if y0 >= 0 { y0 } else { y0 - 399 }) / 400;
        let yoe = y0 - era * 400;
        let doy = doy_from_civil(m, d);
        let z = days_from_civil(y, m, d) + 719468;
        let doe = z - era * 146097;
        civil_parts(y, m, d);
        doe_bounds(yoe, doy);
        era_of_days(era, doe);
        year_of_era_from_doe_exact(yoe, doy);
        month_day_from_doy_exact(y, m, d);
    }
}

/// [`days_civil_round_trip`] restated as a predicate, component-wise.
///
/// Two reasons this exists rather than the contract naming
/// `civil_from_days(days_from_civil(y, m, d)) == (y, m, d)` directly:
///
/// * the provers cannot decompose a *record* equality on the generated tuple
///   type (the same limitation that [`YearMonthDayView`] exists for), so the
///   three components have to be stated as a conjunction of equalities; and
/// * a `#[logic]` function's contract is only emitted into the VCs that
///   mention it, so `round_trip`'s own VC has to name something that mentions
///   [`days_civil_round_trip`] for the composite proof to be visible there at
///   all.
#[logic]
#[requires(1 <= m && m <= 12 && 1 <= d
    && d <= crate::year_month_day_last::month_length(m, y))]
#[ensures(result)]
#[ensures({
    let c = civil_from_days(days_from_civil(y, m, d));
    result == (c.year == y && c.month == m && c.day == d)
})]
pub fn civil_round_trip_holds(y: Int, m: Int, d: Int) -> bool {
    pearlite! {
        let c = civil_from_days(days_from_civil(y, m, d));
        days_civil_round_trip(y, m, d);
        c.year == y && c.month == m && c.day == d
    }
}

/// Bound on the day-of-era `doe = yoe*365 + yoe/4 - yoe/100 + doy`, the
/// intermediate `days_from_civil` sums before the era scaling.
#[logic]
#[requires(yoe >= 0 && yoe <= 399 && doy >= 0 && doy <= 365)]
#[ensures({
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    doe >= 0 && doe <= 146096
})]
pub fn doe_bounds(yoe: Int, doy: Int) {}

/// The year-of-era and day-of-year recovery bounds, as a predicate over the
/// day-of-era. This is the second precondition `round_trip` needs: it lets
/// the provers tie `civil_from_days`'s `year_of_era_from_doe` call back to
/// the `yoe`/`doy` that `days_from_civil` used.
#[logic]
#[requires(doe >= 0 && doe <= 146096)]
#[ensures({
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    yoe >= 0 && yoe <= 399 && doy >= 0 && doy <= 365
})]
pub fn yoe_doy_bounds(doe: Int) -> bool {
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    yoe >= 0 && yoe <= 399 && doy >= 0 && doy <= 365
}

/// The era decomposition of `days_from_civil`: for a valid date,
/// `days_from_civil(y, m, d) + 719468` decomposes as `era*146097 + doe`
/// with `doe` in `[0, 146096]`, which is what makes `civil_from_days`
/// the exact inverse.
///
/// Returns `bool` so it can be named in a `#[requires]` (a contract needs a
/// boolean); the era bounds are its ensures.
#[logic]
#[requires(y >= -32767 && y <= 32767 && m >= 1 && m <= 12 && d >= 1 && d <= 31)]
#[ensures({
    let z = days_from_civil(y, m, d) + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    doe >= 0 && doe <= 146096
})]
pub fn era_decomposition(y: Int, m: Int, d: Int) -> bool {
    let z = days_from_civil(y, m, d) + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    doe >= 0 && doe <= 146096
}

/// The `(year, month, day)` triple [`civil_from_days`] produces.
///
/// A named record rather than a `(Int, Int, Int)` tuple, for the same reason
/// as [`YearMonthDayView`] (which has the full story): the provers cannot
/// decompose a record equality on a generated tuple type, and every contract
/// that relates the day count to a calendar date has to do exactly that.
/// Naming the components makes the relation a conjunction of field
/// equalities, which every prover discharges.
///
/// A pure logic type: it never appears in a program context, so it has no
/// `Clone`/`Copy`/`Debug` derives (`Int` implements none of them).
pub struct CivilView {
    pub year: Int,
    pub month: Int,
    pub day: Int,
}

/// A proleptic Gregorian date.
///
/// The deep model of [`YearMonthDay`]: the record of the three components'
/// views.
///
/// A named record rather than the tuple `(Int, Int, Int)`: Creusot
/// translates Rust tuples to records whose generated field names (`f0'2`,
/// `f1'2`, `f2'2`) the provers cannot decompose — the `refines` goal of
/// `eq` (component-wise implies record equality) and the `eq` verification
/// condition (record equality from component equalities) are both unprovable
/// on those names, while the same goals on named fields are discharged by
/// every prover. This is the shape Creusot's own `DeepModel` derive
/// generates (`{Name}DeepModel { field: T::DeepModelTy, … }`) and the
/// `should_succeed/syntax/derive_macros/mixed.rs` test proves.
///
/// No `Clone`/`Copy`/`Debug` derives: `Int` does not implement `Debug`, and
/// the view is a pure logic type that never appears in a program context.
pub struct YearMonthDayView {
    pub year: Int,
    pub month: Int,
    pub day: Int,
}

#[cfg(creusot)]
impl DeepModel for YearMonthDayView {
    type DeepModelTy = YearMonthDayView;

    #[logic(open, inline)]
    fn deep_model(self) -> YearMonthDayView {
        self
    }
}

#[cfg(creusot)]
impl PartialEq for YearMonthDayView {
    // Field-wise, not `self.deep_model() == other.deep_model()`: the view's
    // deep model is the identity, so the derived spelling would be bare
    // record equality. Spelled over the fields, the `refines` goal (this
    // implies record equality) is discharged on the clean field names.
    #[ensures(result == (
        self.year == rhs.year
        && self.month == rhs.month
        && self.day == rhs.day
    ))]
    fn eq(&self, rhs: &Self) -> bool {
        self.year == rhs.year && self.month == rhs.month && self.day == rhs.day
    }
}

/// A proleptic Gregorian date.
#[derive(Clone, Copy, Debug)]
pub struct YearMonthDay {
    pub year: Year,
    pub month: Month,
    pub day: crate::day::Day,
}

// Under `cfg(creusot)` the contract speaks about `deep_model` (a `#[logic]`
// item, stripped in ordinary builds), so the impls are gated.
#[cfg(not(creusot))]
impl PartialEq for YearMonthDay {
    fn eq(&self, other: &Self) -> bool {
        self.year == other.year && self.month == other.month && self.day == other.day
    }
}

#[cfg(creusot)]
impl PartialEq for YearMonthDay {
    // The derived spelling, not the component-wise one of the pre-view
    // port: against it the `refines` goal is `P -> P` (the standard library's
    // spec is `self.deep_model() == rhs.deep_model()`, and `deep_model_ref`
    // rewrites to `deep_model`), so it no longer needs the provers to
    // decompose tuple record equality.
    #[ensures(result == (self.deep_model() == other.deep_model()))]
    fn eq(&self, other: &Self) -> bool {
        self.year == other.year && self.month == other.month && self.day == other.day
    }
}

impl Eq for YearMonthDay {}

#[cfg(creusot)]
impl DeepModel for YearMonthDay {
    type DeepModelTy = YearMonthDayView;

    #[logic(open)]
    fn deep_model(self) -> YearMonthDayView {
        pearlite! { YearMonthDayView { year: self.year.0@, month: self.month.0@, day: self.day.0@ } }
    }
}

impl YearMonthDay {
    pub const fn new(year: Year, month: Month, day: crate::day::Day) -> YearMonthDay {
        YearMonthDay { year, month, day }
    }

    /// `y_ / m_ / last` — the last day of this date's month.
    ///
    /// The contract is what makes `ok`'s last conjunct provable: `day`'s
    /// contract speaks about the `YearMonthDayLast` value `last` returns,
    /// and without this ensures the VC cannot relate that value back to
    /// `self`'s fields.
    #[ensures(result.year.0@ == self.year.0@ && result.month.0@ == self.month.0@)]
    pub const fn last(&self) -> YearMonthDayLast {
        YearMonthDayLast::new(self.year, self.month)
    }

    /// `year_month_day::ok()` — true exactly when the year and month are ok
    /// and the day lies between 1 and the last day of the month.
    ///
    /// Constraint YearMonthDay.C3.
    ///
    /// The domain constraints are inlined rather than named via the
    /// `ok_logic`/`is_leap_logic` twins or `bool`-returning logic
    /// predicates: both are opaque in this module's VCs, so the
    /// `month_length` transfer from `day`'s contract would not unfold.
    /// `month_length` takes the year and is `Int`-returning, so it is
    /// transparent here.
    ///
    /// The three cross-concept calls are spelled as associated-function paths
    /// (`Year::ok(&self.year)`, not `self.year.ok()`) purely so the
    /// C_static extractor can resolve them. Both spellings are the same
    /// statically dispatched inherent call — see the note on
    /// `YearMonthDayLast::ok`, which is the same edit.
    #[ensures(
        result == (
            self.year.0@ != -32768
            && 1 <= self.month.0@ && self.month.0@ <= 12
            && 1 <= self.day.0@
            && self.day.0@ <= crate::year_month_day_last::month_length(
                self.month.0@, self.year.0@)
        )
    )]
    pub const fn ok(&self) -> bool {
        Year::ok(&self.year)
            && Month::ok(&self.month)
            && crate::day::Day(1).0 <= self.day.0
            && self.day.0 <= YearMonthDayLast::day(&self.last()).0
    }

    /// Logic twin of `ok`, for use in contracts (program functions cannot be
    /// called in a logic context, so contracts name the twin). Spelled over
    /// the logic functions (`month_length`, the `ok`/`is_leap` twins) so it
    /// is total in Pearlite.
    #[logic]
    pub fn ok_logic(self) -> bool {
        // Inlined domain constraints, not the opaque twins (see `ok`).
        pearlite! {
            self.year.0@ != -32768
                && 1 <= self.month.0@ && self.month.0@ <= 12
                && 1 <= self.day.0@
                && self.day.0@ <= crate::year_month_day_last::month_length(
                    self.month.0@, self.year.0@)
        }
    }

    /// `year_month_day::to_days()` — the epoch day count (days from
    /// 1970-01-01), via the era arithmetic.
    ///
    /// Constraint YearMonthDay.C1: the result is exactly
    /// `era*146097 + doe - 719468` with the C++ intermediate definitions.
    ///
    /// The function is deliberately total: C++ `operator sys_days()` is
    /// unguarded and an `ok() == false` date still yields an epoch day count
    /// (the era arithmetic normalizes an out-of-range day into the following
    /// month — constraint YearMonthDay.C4, evidence E-15). A precondition of
    /// `self.ok()` would diverge from that and would additionally make the
    /// call from `to_days_bounded` unprovable: its scope is the interactions'
    /// `minimum_scope` (year in `[-32767, 32767]`, month in `[1, 12]`, day in
    /// `[1, 31]`), and `day.ok()` does not imply the day is valid for its
    /// month (February 30th).
    #[ensures(result.0@ == days_from_civil(self.year.0@, self.month.0@, self.day.0@))]
    pub const fn to_days(&self) -> Days {
        let y = self.year.0 as i32 - if self.month.0 <= 2 { 1 } else { 0 };
        let m = self.month.0 as i32;
        let d = self.day.0 as i32;
        let era = if y >= 0 { y } else { y - 399 } / 400;
        let yoe = y - era * 400;
        let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
        let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        Days(era * 146097 + doe - 719468)
    }

    /// `year_month_day::to_days()` bounded to the representable year domain.
    ///
    /// Constraint YearMonthDay.C5: over year in `[-32767, 32767]` the result
    /// stays within `[-12687428, 11248737]` and never overflows `days::rep`
    /// (a 32-bit `int`).
    ///
    /// The *second* `ensures` -- the identity with `days_from_civil` -- is
    /// inherited from `to_days`, whose contract already states it and whose
    /// body is this function's whole body. It has to be repeated here, not
    /// left implicit: a caller sees only this function's contract, never
    /// `to_days`'s, so without it `round_trip`'s VC knows the day count is
    /// *some* value in `[-12687428, 11248737]` but not that it is the
    /// `days_from_civil` of the very `(y, m, d)` being round-tripped. The
    /// composition obligation is then unprovable in principle, not merely
    /// hard: the postcondition talks about
    /// `civil_from_days(days_from_civil(y,m,d))` while the program computes
    /// `from_days(an unrelated day count)`. The `y`, `m`, `d` the postcondition
    /// mentions and the ones the day count came from are only connected by
    /// this equality.
    #[requires(
        self.year.0@ != -32768
            && 1 <= self.month.0@ && self.month.0@ <= 12
            && 1 <= self.day.0@ && self.day.0@ <= 31
    )]
    #[ensures(result.0@ >= -12687428 && result.0@ <= 11248737)]
    #[ensures(result.0@ == days_from_civil(self.year.0@, self.month.0@, self.day.0@))]
    pub const fn to_days_bounded(&self) -> Days {
        self.to_days()
    }

    /// `year_month_day::from_days(dp)` — the exact inverse of `to_days()`.
    ///
    /// Constraint YearMonthDay.C2: `from_days` returns the civil fields
    /// recovered from its bounded epoch-day input.
    ///
    /// The precondition scopes the day count to the range `to_days` produces
    /// over the valid year domain. Outside it the C++ has signed-overflow UB
    /// (`dp.count() + 719468` and `era * 400` overflow), so there is no defined
    /// C++ behavior to port.
    #[requires(dp.0@ >= -12687428 && dp.0@ <= 11248737)]
    #[ensures({
        let c = civil_from_days(dp.0@);
        result.year.0@ == c.year && result.month.0@ == c.month && result.day.0@ == c.day
    })]
    pub const fn from_days(dp: Days) -> YearMonthDay {
        let z = dp.0 + 719468;
        let era = if z >= 0 { z } else { z - 146096 } / 146097;
        let doe = z - era * 146097;
        let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        let y = yoe + era * 400;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let d = doy - (153 * mp + 2) / 5 + 1;
        let m = if mp < 10 { mp + 3 } else { mp - 9 };
        YearMonthDay {
            year: Year((y + if m <= 2 { 1 } else { 0 }) as i16),
            month: Month(m as u8),
            day: crate::day::Day(d as u8),
        }
    }

    /// The round trip `from_days(to_days(self)) == self`, recorded separately
    /// as constraint YearMonthDay.C007 so C2 remains mapped to `from_days`.
    ///
    /// The postcondition is stated over the logic functions
    /// (`days_from_civil`/`civil_from_days`) rather than the program
    /// `to_days`/`from_days`, because program functions cannot be called in
    /// a logic context; the proof discharges it through the contracts of
    /// `to_days_bounded` and `from_days`.
    ///
    /// The body calls `to_days_bounded`, not `to_days`: `from_days`'s
    /// precondition scopes the day count to the range `to_days_bounded`
    /// proves (constraint YearMonthDay.C5), and only `to_days_bounded`'s
    /// contract carries those bounds — `to_days`'s contract is the bare
    /// `days_from_civil` equality, which leaves the `from_days` call's
    /// precondition unprovable. For the same reason `to_days_bounded`
    /// restates that `days_from_civil` equality in addition to the bounds:
    /// this obligation needs *both* facts about the day count, and a callee
    /// sees only its own contract.
    ///
    /// PROOF STATUS: proved. `vc_round_trip` is discharged in full, from
    /// `days_civil_round_trip` — the composition of the per-step exactness
    /// lemmas `civil_parts`, `era_of_days`, `year_of_era_from_doe_exact` (the
    /// Neri–Schneider year-of-era exactness argument) and
    /// `month_day_from_doy_exact`, with the era bounds from `doe_bounds`.
    /// Every sub-goal is closed by `alt-ergo` in under 20ms; no manual Why3
    /// proof is involved. What it needed was the `days_from_civil` equality in
    /// `to_days_bounded`'s contract: without it the goal is not merely hard
    /// but *unprovable*, because the postcondition and the day count the
    /// program computed are then unconnected. That diagnosis, and the earlier
    /// "5 of 7 / 6 of 10 sub-goals" states of this comment, are recorded in
    /// `findings/limitations.jsonl` (`date-creusot-039` and its resolution
    /// record) and in `FUTURE-WORK-round-trip-proof.md`.
    #[requires(self.ok_logic())]
    #[ensures(civil_round_trip_holds(self.year.0@, self.month.0@, self.day.0@))]
    #[ensures({
        let c = civil_from_days(days_from_civil(
            self.year.0@, self.month.0@, self.day.0@));
        result == (c.year == self.year.0@
            && c.month == self.month.0@
            && c.day == self.day.0@)
    })]
    pub fn round_trip(&self) -> bool {
        let r = YearMonthDay::from_days(self.to_days_bounded());
        // Field-wise rather than `r == *self`, even though the two are the
        // same function (`PartialEq for YearMonthDay` compares exactly these
        // three): routing the comparison through the deep model would put a
        // `YearMonthDayView` *record* equality in the postcondition, and the
        // provers cannot build one from its three components. That is the same
        // limitation that forced the derived spelling of that `PartialEq`,
        // and it is why the port has a named view type at all.
        r.year == self.year && r.month == self.month && r.day == self.day
    }
}

/// `civil_from_days(z)` — the inverse era arithmetic, as a logic function
/// returning a [`CivilView`].
///
/// `z` is the epoch day count (days from 1970-01-01), matching
/// `days_from_civil`'s result and the program `from_days`'s argument. The
/// first step mirrors `from_days`'s `let z = dp.0 + 719468;`: `days_from_civil`
/// subtracts 719468 to convert "days since March 1, year 0" to the 1970
/// epoch, so the inverse must add it back before doing the era/doe
/// decomposition. Without this line the function is not actually the
/// inverse of `days_from_civil` for any input away from a narrow
/// coincidental window — found via brute-force round-trip testing while
/// investigating chainlink #15's two failing proof obligations
/// (`vc_round_trip`, `vc_from_days`).
#[logic]
pub fn civil_from_days(z: Int) -> CivilView {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    let yoe = year_of_era_from_doe(doe);
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let (m, d) = month_day_from_doy(doy);
    let y = y + if m <= 2 { 1 } else { 0 };
    pearlite! { CivilView { year: y, month: m, day: d } }
}
