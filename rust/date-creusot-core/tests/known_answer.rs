//! Known-answer tests for the Rust port, with every vector independently
//! verified against the pinned C++ (commit `179a6b921ccd6179b5b04dce812a89f71a51b4df`)
//! or against Python's proleptic Gregorian `datetime` (which implements the
//! same calendar). Sources are cited per test.
//!
//! Vectors come from the pilot's evidence records:
//! * E-13: weekday encodings at the `z = -4` branch boundary.
//! * E-14: era arithmetic over an 18-case sample, including both 400-year
//!   era boundaries and both ends of the representable year domain.
//! * E-15: the bug-compat behavior of the total `to_days` (out-of-range
//!   days normalize into the following month).

use date_creusot_core::iso_week::{self, IsoWeekday};
use date_creusot_core::weekday::weekday_from_days;
use date_creusot_core::{Day, Days, Month, Weekday, Year, YearMonthDay, YearMonthDayLast};

fn ymd(y: i16, m: u8, d: u8) -> YearMonthDay {
    YearMonthDay::new(Year(y), Month(m), Day(d))
}

/// E-13: `date::weekday::weekday_from_days` at and around the `z = -4`
/// branch boundary. 1970-01-01 (z = 0) is a Thursday (c_encoding 4).
#[test]
fn weekday_from_days_encodings() {
    let cases: &[(i32, u8)] = &[(0, 4), (-1, 3), (-4, 0), (-5, 6), (3, 0), (4, 1)];
    for &(z, expected) in cases {
        assert_eq!(
            weekday_from_days(z),
            expected,
            "weekday_from_days({z}) c_encoding"
        );
        assert_eq!(
            Weekday::from_days(Days(z)).c_encoding(),
            expected,
            "Weekday::from_days({z}) c_encoding"
        );
        let iso = if expected == 0 { 7 } else { expected };
        assert_eq!(
            Weekday::from_days(Days(z)).iso_encoding(),
            iso,
            "Weekday::from_days({z}) iso_encoding"
        );
    }
}

/// E-13: `iso_week::weekday::weekday_from_days` — the ISO 8601 encoding
/// (Monday = 1 .. Sunday = 7) at the same boundary points.
#[test]
fn iso_weekday_from_days_encodings() {
    let cases: &[(i32, u8)] = &[(0, 4), (-1, 3), (-4, 7), (-5, 6), (3, 7), (4, 1)];
    for &(z, expected) in cases {
        assert_eq!(
            iso_week::weekday_from_days(z),
            expected,
            "iso_week::weekday_from_days({z})"
        );
    }
}

/// E-14: `year_month_day::to_days` over the era arithmetic sample, including
/// both 400-year era boundaries (1600-01-01 and 1599-12-31) and ordinary
/// leap-century cases.
#[test]
fn to_days_known_answers() {
    let cases: &[(i16, u8, u8, i32)] = &[
        (1, 1, 1, -719162),
        (1600, 1, 1, -135140),
        (1599, 12, 31, -135141),
        (1900, 2, 28, -25509),
        (1900, 3, 1, -25508),
        (2000, 1, 1, 10957),
        (2000, 2, 29, 11016),
        (2023, 3, 1, 19417),
        (2024, 2, 29, 19782),
        (-32767, 1, 1, -12687428),
        (32767, 12, 31, 11248737),
    ];
    for &(y, m, d, expected) in cases {
        assert_eq!(
            ymd(y, m, d).to_days(),
            Days(expected),
            "to_days({y}-{m:02}-{d:02})"
        );
    }
}

/// E-15 (bug-compat): `to_days` is total and unguarded — an out-of-range
/// day normalizes into the following month rather than being rejected.
/// 1900-02-29 and 2023-02-29 (both `ok() == false`) map to the same epoch
/// day counts as the following March 1st.
#[test]
fn to_days_normalizes_out_of_range_days() {
    assert_eq!(ymd(1900, 2, 29).to_days(), ymd(1900, 3, 1).to_days());
    assert_eq!(ymd(2023, 2, 29).to_days(), ymd(2023, 3, 1).to_days());
    assert_eq!(ymd(1900, 2, 29).to_days(), Days(-25508));
    assert_eq!(ymd(2023, 2, 29).to_days(), Days(19417));
}

/// E-14: `from_days` is the exact inverse of `to_days` on every `ok()`
/// input (16 of the 18 E-14 samples satisfy `ok()`; the other two are the
/// E-15 invalid dates, covered above).
#[test]
fn round_trip_valid_dates() {
    let valid: &[(i16, u8, u8)] = &[
        (1, 1, 1),
        (1600, 1, 1),
        (1599, 12, 31),
        (1900, 2, 28),
        (1900, 3, 1),
        (2000, 1, 1),
        (2000, 2, 29),
        (2023, 3, 1),
        (2024, 2, 29),
        (-32767, 1, 1),
        (32767, 12, 31),
    ];
    for &(y, m, d) in valid {
        let date = ymd(y, m, d);
        assert!(date.ok(), "{y}-{m:02}-{d:02} should be ok");
        assert_eq!(
            YearMonthDay::from_days(date.to_days()),
            date,
            "round trip {y}-{m:02}-{d:02}"
        );
    }
}

/// `year_month_day_last::day` — the Gregorian month length (C1), including
/// the leap-century cases.
#[test]
fn month_length_known_answers() {
    let cases: &[(i16, u8, u8)] = &[
        (2023, 1, 31),
        (2023, 2, 28),
        (2024, 2, 29),
        (1900, 2, 28),
        (2000, 2, 29),
        (2023, 4, 30),
        (2023, 12, 31),
    ];
    for &(y, m, expected) in cases {
        let last = YearMonthDayLast::new(Year(y), Month(m));
        assert_eq!(last.day(), Day(expected), "month length {y}-{m:02}");
    }
}

/// `year_month_day::ok` (C3) — true exactly when the year and month are ok
/// and the day lies between 1 and the last day of the month.
#[test]
fn ok_known_answers() {
    assert!(ymd(2023, 2, 28).ok());
    assert!(!ymd(2023, 2, 29).ok(), "2023-02-29 is not a valid date");
    assert!(ymd(2024, 2, 29).ok(), "2024-02-29 is a valid date");
    assert!(!ymd(1900, 2, 29).ok(), "1900-02-29 is not a valid date");
    assert!(ymd(2000, 2, 29).ok(), "2000-02-29 is a valid date");
    assert!(!ymd(2023, 4, 31).ok(), "April has 30 days");
    assert!(!ymd(2023, 0, 1).ok(), "month 0 is not ok");
    assert!(!ymd(2023, 13, 1).ok(), "month 13 is not ok");
    assert!(!ymd(2023, 1, 0).ok(), "day 0 is not ok");
    assert!(!ymd(-32768, 1, 1).ok(), "year -32768 is not ok");
    assert!(ymd(-32767, 1, 1).ok());
    assert!(ymd(32767, 12, 31).ok());
}

/// `year::is_leap` — the Gregorian leap rule.
#[test]
fn is_leap_known_answers() {
    assert!(!Year(2023).is_leap());
    assert!(Year(2024).is_leap());
    assert!(!Year(1900).is_leap(), "1900 is not a leap year");
    assert!(Year(2000).is_leap(), "2000 is a leap year");
    assert!(!Year(2100).is_leap(), "2100 is not a leap year");
}

/// `iso_week::weekday` conversions are mutual inverses on `[0, 7]` (C2).
#[test]
fn iso_weekday_conversions() {
    for wd in 0..=6u8 {
        let w = Weekday::new(wd);
        let iso = IsoWeekday::from_weekday(w);
        assert_eq!(iso.to_weekday(), w, "round trip c_encoding {wd}");
    }
    assert_eq!(IsoWeekday::new(7).to_weekday(), Weekday::new(0));
    assert_eq!(
        IsoWeekday::from_weekday(Weekday::new(0)),
        IsoWeekday::new(7)
    );
}
