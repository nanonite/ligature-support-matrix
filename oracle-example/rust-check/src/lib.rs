pub fn add(a: i64, b: i64) -> Result<i64, &'static str> {
    a.checked_add(b).ok_or("integer_overflow")
}
