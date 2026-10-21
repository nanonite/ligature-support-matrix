from pathlib import Path
import json
import re

root = Path(__file__).resolve().parent
cases_path = root / "cases.jsonl"
golden_path = root / "golden" / "results.jsonl"
output_path = root / "rust-check" / "tests" / "generated_cases.rs"


def load_jsonl(path):
    values = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank line in {path}:{line_number}")
        values.append(json.loads(line))
    return values


def rust_test_name(case_id):
    name = re.sub(r"[^A-Za-z0-9_]", "_", case_id)
    if not name or name[0].isdigit():
        name = "case_" + name
    return name


cases = load_jsonl(cases_path)
golden = load_jsonl(golden_path)
case_ids = [case["case_id"] for case in cases]
golden_ids = [result["case_id"] for result in golden]
if len(case_ids) != len(set(case_ids)):
    raise ValueError("duplicate case_id in cases.jsonl")
if set(case_ids) != set(golden_ids):
    raise ValueError("cases and golden case IDs differ")
if golden_ids != sorted(case_ids):
    raise ValueError("golden results are not in bytewise case_id order")
for case in cases:
    if case.get("oracle_scope", "compare") == "excluded" and not case.get("exclusion_reason"):
        raise ValueError(f"excluded case lacks exclusion_reason: {case['case_id']}")

support = r'''use serde_json::{json, Value};
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
'''

tests = [support]
for case_id in case_ids:
    tests.append(f'#[test]\nfn {rust_test_name(case_id)}() {{\n    assert_case("{case_id}");\n}}\n')
output_path.write_text("\n".join(tests), encoding="utf-8")
print(f"generated {len(case_ids)} tests in {output_path}")
