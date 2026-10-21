use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};

fn data_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join(name)
}

fn load_jsonl(path: &Path) -> Vec<Value> {
    fs::read_to_string(path)
        .expect("read JSONL fixture")
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).expect("parse JSONL fixture"))
        .collect()
}

fn assert_case(case_id: &str) {
    let cases = load_jsonl(&data_path("cases.jsonl"));
    let golden = load_jsonl(&data_path("golden/results.jsonl"));
    let case = cases
        .iter()
        .find(|value| value.get("case_id").and_then(Value::as_str) == Some(case_id))
        .expect("case exists");
    let expected = golden
        .iter()
        .find(|value| value.get("case_id").and_then(Value::as_str) == Some(case_id))
        .expect("golden result exists");
    if case.get("oracle_scope").and_then(Value::as_str) == Some("excluded") {
        assert!(!case
            .get("exclusion_reason")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .is_empty());
        assert_eq!(expected.get("status").and_then(Value::as_str), Some("ok"));
        assert!(expected.get("value").is_some_and(Value::is_null));
        return;
    }
    let inputs = case.get("inputs").and_then(Value::as_object).expect("inputs object");
    let a = inputs.get("a").and_then(Value::as_i64).expect("signed a");
    let b = inputs.get("b").and_then(Value::as_i64).expect("signed b");
    let actual = match oracle_example_check::add(a, b) {
        Ok(value) => json!({"case_id": case_id, "status": "ok", "value": value}),
        Err(err_kind) => json!({"case_id": case_id, "status": "err", "err_kind": err_kind}),
    };
    assert_eq!(actual, *expected, "oracle mismatch for {case_id}");
}

#[test]
fn boundary_add_normal_001() {
    assert_case("boundary-add-normal-001");
}

#[test]
fn boundary_add_overflow_003() {
    assert_case("boundary-add-overflow-003");
}

#[test]
fn boundary_add_negative_002() {
    assert_case("boundary-add-negative-002");
}

#[test]
fn boundary_iteration_order_004() {
    assert_case("boundary-iteration-order-004");
}
