use vstd::prelude::*;
verus! {
// Spec division is Euclidean (floor for a positive divisor), so the C++
// `(y >= 0 ? y : y - 399) / 400` truncation trick is stated as `y / 400`.
spec fn days_from_civil(y: int, m: int, d: int) -> int {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y / 400;
    let yoe = y - era * 400;
    let mp = if m > 2 { m - 3 } else { m + 9 };
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}
spec fn civil_from_days(z0: int) -> (int, int, int) {
    let z = z0 + 719468;
    let era = z / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }, m, d)
}
spec fn is_leap(y: int) -> bool { y % 4 == 0 && (y % 100 != 0 || y % 400 == 0) }
spec fn month_length(m: int, y: int) -> int {
    if m == 2 { if is_leap(y) { 29 } else { 28 } }
    else if m == 4 || m == 6 || m == 9 || m == 11 { 30 } else { 31 }
}
spec fn valid(y: int, m: int, d: int) -> bool {
    -32767 <= y <= 32767 && 1 <= m <= 12 && 1 <= d <= month_length(m, y)
}

fn to_days(y: i16, m: u8, d: u8) -> (r: i32)
    requires -32767 <= y <= 32767, 1 <= m <= 12, 1 <= d <= 31,
    ensures r == days_from_civil(y as int, m as int, d as int),
            -12687428 <= r <= 11248737,
{
    let y: i32 = y as i32 - if m <= 2 { 1 } else { 0 };
    let m: i32 = m as i32;
    let d: i32 = d as i32;
    let era: i32 = (if y >= 0 { y } else { y - 399 }) / 400;
    let yoe: i32 = y - era * 400;
    let doy: i32 = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + d - 1;
    let doe: i32 = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

fn from_days(dp: i32) -> (r: (i16, u8, u8))
    requires -12687428 <= dp <= 11248737,
    ensures (r.0 as int, r.1 as int, r.2 as int) == civil_from_days(dp as int),
{
    let z: i32 = dp + 719468;
    let era: i32 = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe: i32 = z - era * 146097;
    let yoe: i32 = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y: i32 = yoe + era * 400;
    let doy: i32 = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp: i32 = (5 * doy + 2) / 153;
    let d: i32 = doy - (153 * mp + 2) / 5 + 1;
    let m: i32 = if mp < 10 { mp + 3 } else { mp - 9 };
    ((y + if m <= 2 { 1 } else { 0 }) as i16, m as u8, d as u8)
}

fn round_trip(y: i16, m: u8, d: u8) -> (b: bool)
    requires valid(y as int, m as int, d as int),
    ensures b,
{
    let r = from_days(to_days(y, m, d));
    r.0 == y && r.1 == m && r.2 == d
}
fn main() {}
}
