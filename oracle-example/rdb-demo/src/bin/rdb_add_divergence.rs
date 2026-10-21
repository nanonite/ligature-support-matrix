fn main() {
    let case_id = "boundary-add-overflow-003";
    let a = i64::MAX;
    let b = 1_i64;
    let result = rdb_divergence_demo::add(a, b);
    println!("case_id={case_id} a={a} b={b} expected=Err(\"integer_overflow\") result={result:?}");
}
