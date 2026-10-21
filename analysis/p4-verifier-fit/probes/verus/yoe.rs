use vstd::prelude::*;
verus! {
spec fn era_year_start(yoe: int) -> int { 365 * yoe + yoe / 4 - yoe / 100 }
spec fn year_of_era_from_doe(doe: int) -> int { (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365 }
spec fn valid_era_day(yoe: int, doy: int) -> bool {
    0 <= doy <= 365 && (doy <= 364 || (yoe % 4 == 3 && yoe != 99 && yoe != 199 && yoe != 299))
}
// Creusot needed a 7-helper case analysis for this (P1 year_of_era_from_doe_exact).
proof fn year_of_era_exact(yoe: int, doy: int)
    requires 0 <= yoe <= 399, valid_era_day(yoe, doy),
    ensures year_of_era_from_doe(era_year_start(yoe) + doy) == yoe,
{
}
fn main() {}
}
