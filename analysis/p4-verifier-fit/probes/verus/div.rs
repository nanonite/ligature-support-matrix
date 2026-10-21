use vstd::prelude::*;
verus! {
// Spec-level int division: which rounding does Verus use for negative dividends?
proof fn spec_div_is_euclidean() {
    assert((-1int) / 400 == -1);
    assert((-1int) % 400 == 399);
    assert((-401int) / 400 == -2);
}
// Exec i32 division: Rust truncates toward zero.
fn exec_div(y: i32) -> (r: i32)
    requires y == -1,
    ensures r == 0,
{
    y / 400
}
// Nonlinear fact with a constant divisor, no hints.
proof fn era_recovery(era: int, doe: int)
    requires 0 <= doe <= 146096,
    ensures (era * 146097 + doe) / 146097 == era,
{
}
fn main() {}
}
