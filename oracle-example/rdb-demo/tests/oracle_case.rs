#[test]
fn boundary_add_overflow_003() {
    assert_eq!(rdb_divergence_demo::add(i64::MAX, 1), Err("integer_overflow"));
}
