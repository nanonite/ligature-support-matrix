// #156 feasibility probe (scratch copy only): YearMonthDay.C007 over the whole valid domain.
use crate::{Day, Month, Year, YearMonthDay};

#[kani::proof]
fn round_trip_full_domain() {
    let y: i16 = kani::any();
    let m: u8 = kani::any();
    let d: u8 = kani::any();
    let ymd = YearMonthDay::new(Year(y), Month(m), Day(d));
    kani::assume(ymd.ok());
    assert!(ymd.round_trip());
}

// Non-vacuity: a valid date is reachable under the assumption.
#[kani::proof]
fn round_trip_reachable() {
    let y: i16 = kani::any();
    let m: u8 = kani::any();
    let d: u8 = kani::any();
    let ymd = YearMonthDay::new(Year(y), Month(m), Day(d));
    kani::assume(ymd.ok());
    kani::cover!(y == 2000 && m == 2 && d == 29);
}

// Mutant: claiming the round trip fails must be refuted.
#[kani::proof]
fn round_trip_mutant() {
    let y: i16 = kani::any();
    let m: u8 = kani::any();
    let d: u8 = kani::any();
    let ymd = YearMonthDay::new(Year(y), Month(m), Day(d));
    kani::assume(ymd.ok());
    assert!(!ymd.round_trip());
}
