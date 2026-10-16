#!/usr/bin/env python3
"""Rust test generator for the date-creusot differential oracle.

Reads oracle/cases.jsonl and oracle/golden/results.jsonl, validates that
their case IDs agree (protocol section 6), and writes one `#[test]` per
case to oracle/rust-check/tests/generated_cases.rs. Each generated test
loads both fixtures at runtime, selects its case by case_id, recomputes
the operation through the Rust port, and compares the complete result
object against the golden result. The C++ driver is never invoked from
cargo nextest.

The generated test name is the case_id with every non-alphanumeric
character replaced by '_' (and a 'case_' prefix if it would start with a
digit); oracle/test-map.csv records the exact generated names.
"""

import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
cases_path = root / "cases.jsonl"
golden_path = root / "golden" / "results.jsonl"
output_path = root / "rust-check" / "tests" / "generated_cases.rs"

OP_INPUT_FIELDS = {
    "days_from_civil": {"y", "m", "d"},
    "civil_from_days": {"z"},
    "weekday_from_days": {"z"},
    "ymd_ok": {"y", "m", "d"},
    "iso_weekday_from_days": {"z"},
}
ALLOWED_CASE_FIELDS = {"case_id", "op", "inputs", "oracle_scope", "exclusion_reason"}


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


def validate_cases(cases):
    for case in cases:
        for key in case:
            if key not in ALLOWED_CASE_FIELDS:
                raise ValueError(f"unknown case field {key!r} in {case.get('case_id')}")
        op = case["op"]
        if op not in OP_INPUT_FIELDS:
            raise ValueError(f"unknown op {op!r} in {case['case_id']}")
        inputs = case["inputs"]
        if not isinstance(inputs, dict):
            raise ValueError(f"inputs must be an object in {case['case_id']}")
        expected = OP_INPUT_FIELDS[op]
        actual = set(inputs)
        if actual != expected:
            raise ValueError(
                f"inputs for {op} in {case['case_id']} must be exactly "
                f"{sorted(expected)}, got {sorted(actual)}"
            )
        for key, value in inputs.items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(
                    f"input {key} in {case['case_id']} must be a JSON integer"
                )
        scope = case.get("oracle_scope", "compare")
        if scope == "excluded" and not case.get("exclusion_reason"):
            raise ValueError(f"excluded case lacks exclusion_reason: {case['case_id']}")
        if scope == "compare" and case.get("exclusion_reason"):
            raise ValueError(f"compare case cannot have exclusion_reason: {case['case_id']}")


cases = load_jsonl(cases_path)
golden = load_jsonl(golden_path)
validate_cases(cases)

case_ids = [case["case_id"] for case in cases]
golden_ids = [result["case_id"] for result in golden]
if len(case_ids) != len(set(case_ids)):
    raise ValueError("duplicate case_id in cases.jsonl")
if set(case_ids) != set(golden_ids):
    missing = set(case_ids) - set(golden_ids)
    extra = set(golden_ids) - set(case_ids)
    raise ValueError(f"cases and golden case IDs differ (missing={missing}, extra={extra})")
if golden_ids != sorted(golden_ids):
    raise ValueError("golden results are not in bytewise case_id order")

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
    let op = case.get("op").and_then(Value::as_str).expect("op");

    let actual = match op {
        "days_from_civil" => {
            let y = inputs.get("y").and_then(Value::as_i64).expect("y") as i16;
            let m = inputs.get("m").and_then(Value::as_i64).expect("m") as u8;
            let d = inputs.get("d").and_then(Value::as_i64).expect("d") as u8;
            let days = date_creusot_core::YearMonthDay::new(
                date_creusot_core::Year(y),
                date_creusot_core::Month(m),
                date_creusot_core::Day(d),
            ).to_days();
            json!({"case_id": case_id, "status": "ok", "value": days.0})
        }
        "civil_from_days" => {
            let z = inputs.get("z").and_then(Value::as_i64).expect("z") as i32;
            let ymd = date_creusot_core::YearMonthDay::from_days(date_creusot_core::Days(z));
            json!({"case_id": case_id, "status": "ok", "value": {
                "y": ymd.year.0,
                "m": ymd.month.0,
                "d": ymd.day.0
            }})
        }
        "weekday_from_days" => {
            let z = inputs.get("z").and_then(Value::as_i64).expect("z") as i32;
            let wd = date_creusot_core::weekday_from_days(z);
            json!({"case_id": case_id, "status": "ok", "value": wd})
        }
        "ymd_ok" => {
            let y = inputs.get("y").and_then(Value::as_i64).expect("y") as i16;
            let m = inputs.get("m").and_then(Value::as_i64).expect("m") as u8;
            let d = inputs.get("d").and_then(Value::as_i64).expect("d") as u8;
            let ok = date_creusot_core::YearMonthDay::new(
                date_creusot_core::Year(y),
                date_creusot_core::Month(m),
                date_creusot_core::Day(d),
            ).ok();
            json!({"case_id": case_id, "status": "ok", "value": ok})
        }
        "iso_weekday_from_days" => {
            let z = inputs.get("z").and_then(Value::as_i64).expect("z") as i32;
            let wd = date_creusot_core::iso_week::weekday_from_days(z);
            json!({"case_id": case_id, "status": "ok", "value": wd})
        }
        _ => panic!("unknown op: {op}"),
    };
    assert_eq!(actual, *expected, "oracle mismatch for {case_id}");
}
'''

tests = [support]
for case_id in case_ids:
    tests.append(f'#[test]\nfn {rust_test_name(case_id)}() {{\n    assert_case("{case_id}");\n}}\n')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text("\n".join(tests), encoding="utf-8")
print(f"generated {len(case_ids)} tests in {output_path}")
