#!/usr/bin/env python3
"""Validate oracle fixtures and generate deterministic one-test-per-case checks."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM_COMMIT = "2065f4ded0558c6f89fee67c8e5228feb4eb960e"
CASE_FILES = (
    ("cases.jsonl", "golden/results.jsonl"),
    ("random-cases.jsonl", "golden/random-results.jsonl"),
)
UPSTREAM_ROOT = ROOT.parent / "upstream/abseil-cpp"
UPSTREAM_SOURCES = (
    "absl/container/internal/raw_hash_set_test.cc",
    "absl/container/internal/raw_hash_set_allocator_test.cc",
    "absl/container/internal/raw_hash_set_resize_impl_test.cc",
    "absl/container/flat_hash_set_test.cc",
    "absl/container/flat_hash_map_test.cc",
    "absl/container/node_hash_set_test.cc",
    "absl/container/node_hash_map_test.cc",
    "absl/container/internal/hashtable_control_bytes_test.cc",
    "absl/container/internal/hashtablez_sampler_test.cc",
    "absl/container/inlined_vector_test.cc",
    "absl/container/inlined_vector_exception_safety_test.cc",
)
GENERATED = ROOT.parent / "rust/swisstable-verus-core/tests/generated_cases.rs"
TEST_MAP = ROOT / "test-map.csv"
ACTION = re.compile(r"^(insert|erase|contains|reserve|clear|erase_if_all|erase_if_none|erase_if_odd)\((.*)\)$")
CASE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAPPED = {
    "absl/container/flat_hash_map_test.cc::FlatHashMap.EraseIf":
        ["upstream-test-flat-hash-map-erase-if-0001"],
    "absl/container/flat_hash_map_test.cc::FlatHashMap.Reserve":
        ["upstream-test-flat-hash-map-reserve-0001"],
}


def read_jsonl(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or any(not line for line in lines):
        raise ValueError(f"{path}: JSONL must be nonempty and have no blank lines")

    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"{path}: duplicate JSON field {key!r}")
            value[key] = item
        return value

    return [json.loads(line, object_pairs_hook=unique_object) for line in lines]


def validate_case(case, where):
    allowed = {"case_id", "op", "inputs", "oracle_scope", "exclusion_reason"}
    if set(case) - allowed or not {"case_id", "op", "inputs"} <= set(case):
        raise ValueError(f"{where}: invalid top-level fields")
    case_id = case["case_id"]
    if not isinstance(case_id, str) or not CASE_ID.fullmatch(case_id):
        raise ValueError(f"{where}: invalid case_id {case_id!r}")
    if case["op"] != "map_sequence":
        raise ValueError(f"{where}: unsupported op {case['op']!r}")
    if not isinstance(case["inputs"], dict) or set(case["inputs"]) != {"actions"}:
        raise ValueError(f"{where}: inputs must contain exactly actions")
    actions = case["inputs"]["actions"]
    if not isinstance(actions, str) or not actions:
        raise ValueError(f"{where}: actions must be a nonempty string")
    scope = case.get("oracle_scope", "compare")
    if scope not in ("compare", "excluded"):
        raise ValueError(f"{where}: invalid oracle_scope")
    if scope == "excluded":
        if not isinstance(case.get("exclusion_reason"), str) or not case["exclusion_reason"].strip():
            raise ValueError(f"{where}: excluded case requires exclusion_reason")
    elif "exclusion_reason" in case:
        raise ValueError(f"{where}: comparable case cannot have exclusion_reason")
    for text in actions.split(";"):
        match = ACTION.fullmatch(text)
        if not match:
            raise ValueError(f"{where}: malformed action {text!r}")
        kind, args = match.groups()
        if kind == "insert":
            parts = args.split(",")
            if len(parts) != 2:
                raise ValueError(f"{where}: insert requires key and value")
            if any(not part.isdecimal() or str(int(part)) != part for part in parts):
                raise ValueError(f"{where}: arguments must be canonical unsigned integers")
            numbers = [int(part) for part in parts]
        elif kind in ("erase", "contains", "reserve"):
            if not args.isdecimal() or str(int(args)) != args:
                raise ValueError(f"{where}: argument must be a canonical unsigned integer")
            numbers = [int(args)]
        else:
            if args:
                raise ValueError(f"{where}: {kind} takes no arguments")
            numbers = []
        if any(number < 0 or number > 0xffffffffffffffff for number in numbers):
            raise ValueError(f"{where}: action argument is outside u64")
        if kind in ("insert", "erase", "contains") and numbers[0] == 0 and scope == "compare":
            raise ValueError(f"{where}: key zero must be excluded")
        if kind == "reserve" and numbers[0] > 0x7fffffff:
            raise ValueError(f"{where}: reserve exceeds the Rust port bound")
    return case_id


def validate_result(case, result, where):
    case_id = case["case_id"]
    scope = case.get("oracle_scope", "compare")
    if result.get("case_id") != case_id or result.get("status") != "ok":
        raise ValueError(f"{where}: result identity/status mismatch")
    if scope == "excluded":
        if set(result) != {"case_id", "status", "value"} or result["value"] is not None:
            raise ValueError(f"{where}: excluded case must use the null placeholder")
    else:
        if set(result) != {"case_id", "status", "value"}:
            raise ValueError(f"{where}: comparable result must have case_id/status/value")
        value = result["value"]
        if not isinstance(value, dict) or set(value) != {"observations", "final_entries"}:
            raise ValueError(f"{where}: invalid map_sequence result")


def rust_test(case_id, case_file, result_file):
    test_name = "oracle_" + case_id.replace("-", "_")
    return (f'#[test]\nfn {test_name}() {{\n'
            f'    assert_case("{case_file}", "{result_file}", "{case_id}");\n'
            f'}}\n')


def generate():
    all_cases = []
    names = set()
    for case_file, result_file in CASE_FILES:
        cases = read_jsonl(ROOT / case_file)
        results = read_jsonl(ROOT / result_file)
        case_ids = [validate_case(case, f"{case_file}:{index}")
                    for index, case in enumerate(cases, 1)]
        result_ids = [result.get("case_id") for result in results]
        if len(set(case_ids)) != len(case_ids):
            raise ValueError(f"{case_file}: duplicate case_id")
        if result_ids != sorted(result_ids) or len(set(result_ids)) != len(result_ids):
            raise ValueError(f"{result_file}: IDs must be unique and sorted")
        if set(case_ids) != set(result_ids):
            raise ValueError(f"{case_file} and {result_file} have different IDs")
        result_by_id = {result["case_id"]: result for result in results}
        case_by_id = {case["case_id"]: case for case in cases}
        for case_id, case in case_by_id.items():
            validate_result(case, result_by_id[case_id], f"{result_file}:{case_id}")
            names.add(case_id)
            all_cases.append((case_id, case_file, result_file))

    manifest_path = ROOT / "random-cases.jsonl.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = {
        "case_file": "random-cases.jsonl",
        "source": "random",
        "generator": "splitmix64-v1",
        "upstream_commit": UPSTREAM_COMMIT,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            raise ValueError(f"{manifest_path}: {key} must be {expected!r}")
    if not isinstance(manifest.get("seed"), int) or not manifest.get("command"):
        raise ValueError(f"{manifest_path}: seed and command are required")
    expected_command = (
        "python3 oracle/generate_random_cases.py "
        f"--seed {manifest['seed']} --count {len(read_jsonl(ROOT / 'random-cases.jsonl'))}"
    )
    if manifest["command"] != expected_command:
        raise ValueError(f"{manifest_path}: command does not reproduce the random case file")

    rows = ["// Generated by oracle/generate_oracle_tests.py; do not edit.\n",
            "use std::path::Path;\n",
            "use swisstable_verus_core::swiss_table::SwissTable;\n\n",
            RUST_SUPPORT]
    rows.extend(rust_test(*entry) for entry in sorted(all_cases))
    GENERATED.parent.mkdir(parents=True, exist_ok=True)
    GENERATED.write_text("".join(rows), encoding="utf-8")

    upstream_names = []
    declaration_pattern = re.compile(
        r"\b(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P)\s*"
        r"\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*\)")
    for source_name in UPSTREAM_SOURCES:
        source = (UPSTREAM_ROOT / source_name).read_text(encoding="utf-8")
        upstream_names.extend(
            f"{source_name}::{suite}.{test}"
            for _, suite, test in declaration_pattern.findall(source)
        )
    if len(set(upstream_names)) != len(upstream_names):
        raise ValueError("upstream flat_hash_map_test.cc has duplicate test names")
    map_rows = [["upstream_test_name", "case_ids", "nextest_test_name", "coverage_status"]]
    for upstream_name in sorted(upstream_names):
        mapped_ids = MAPPED.get(upstream_name)
        if not mapped_ids:
            map_rows.append([upstream_name, "", "", "unmapped"])
            continue
        for case_id in mapped_ids:
            if case_id not in names:
                raise ValueError(f"{upstream_name}: mapped case {case_id} is missing")
            test_name = "generated_cases::oracle_" + case_id.replace("-", "_")
            map_rows.append([upstream_name, case_id, test_name, "mapped"])
    with TEST_MAP.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(map_rows)
    print(f"generated {len(all_cases)} nextest cases; mapped {len(MAPPED)} of "
          f"{len(upstream_names)} upstream tests")


RUST_SUPPORT = r'''const ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../oracle/");

fn field_string(line: &str, name: &str) -> Option<String> {
    let marker = format!("\"{}\"", name);
    let mut cursor = line.find(&marker)? + marker.len();
    let bytes = line.as_bytes();
    while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() { cursor += 1; }
    if *bytes.get(cursor)? != b':' { return None; }
    cursor += 1;
    while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() { cursor += 1; }
    if *bytes.get(cursor)? != b'"' { return None; }
    cursor += 1;
    let mut output = String::new();
    while cursor < bytes.len() {
        let byte = bytes[cursor];
        cursor += 1;
        match byte {
            b'"' => return Some(output),
            b'\\' => {
                let escaped = *bytes.get(cursor)?;
                cursor += 1;
                match escaped {
                    b'"' => output.push('"'),
                    b'\\' => output.push('\\'),
                    b'/' => output.push('/'),
                    b'b' => output.push('\u{0008}'),
                    b'f' => output.push('\u{000c}'),
                    b'n' => output.push('\n'),
                    b'r' => output.push('\r'),
                    b't' => output.push('\t'),
                    _ => return None,
                }
            }
            0..=31 => return None,
            _ => {
                let tail = std::str::from_utf8(&bytes[cursor - 1..]).ok()?;
                let ch = tail.chars().next()?;
                output.push(ch);
                cursor = cursor - 1 + ch.len_utf8();
            }
        }
    }
    None
}

fn line_for_case(path: &Path, case_id: &str) -> String {
    let content = std::fs::read_to_string(path)
        .unwrap_or_else(|error| panic!("cannot read {}: {error}", path.display()));
    let mut found = None;
    for line in content.lines() {
        assert!(!line.is_empty(), "{} contains a blank line", path.display());
        if field_string(line, "case_id").as_deref() == Some(case_id) {
            assert!(found.replace(line.to_owned()).is_none(),
                    "{} has duplicate case_id {case_id}", path.display());
        }
    }
    found.unwrap_or_else(|| panic!("{} has no case_id {case_id}", path.display()))
}

fn parse_action(text: &str) -> (&str, Vec<u64>) {
    let open = text.find('(').expect("action has opening paren");
    assert!(text.ends_with(')'), "action has closing paren: {text}");
    let kind = &text[..open];
    let args = &text[open + 1..text.len() - 1];
    let numbers = if args.is_empty() {
        Vec::new()
    } else {
        args.split(',').map(|n| n.parse::<u64>().expect("u64 action argument"))
            .collect()
    };
    match kind {
        "insert" => assert_eq!(numbers.len(), 2, "insert arity"),
        "erase" | "contains" | "reserve" => assert_eq!(numbers.len(), 1, "action arity"),
        "clear" | "erase_if_all" | "erase_if_none" | "erase_if_odd" =>
            assert!(numbers.is_empty(), "zero-argument action"),
        _ => panic!("unknown action {kind}"),
    }
    (kind, numbers)
}

fn json_string(value: &str) -> String {
    let mut output = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            ch if (ch as u32) < 0x20 =>
                output.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => output.push(ch),
        }
    }
    output.push('"');
    output
}

fn entries_json(table: &SwissTable) -> String {
    let capacity = table.table.capacity();
    let mut entries = Vec::new();
    for slot in 0..capacity {
        if table.table.ctrl_ref().is_full(slot) {
            entries.push((table.table.hash_at(slot), table.values[slot]));
        }
    }
    entries.sort_unstable();
    let values = entries.iter()
        .map(|(key, value)| format!("[{key},{value}]"))
        .collect::<Vec<_>>().join(",");
    format!("[{values}]")
}

fn assert_case(case_file: &str, result_file: &str, case_id: &str) {
    let case_path = Path::new(ROOT).join(case_file);
    let result_path = Path::new(ROOT).join(result_file);
    let case = line_for_case(&case_path, case_id);
    let golden = line_for_case(&result_path, case_id);
    assert_eq!(field_string(&case, "op").as_deref(), Some("map_sequence"));
    let scope = field_string(&case, "oracle_scope").unwrap_or_else(|| "compare".into());
    assert_eq!(field_string(&case, "case_id").as_deref(), Some(case_id));

    if scope == "excluded" {
        assert!(field_string(&case, "exclusion_reason").is_some_and(|s| !s.trim().is_empty()),
                "excluded case requires a reason");
        let placeholder = format!(
            "{{\"case_id\":{},\"status\":\"ok\",\"value\":null}}", json_string(case_id));
        assert_eq!(golden, placeholder, "excluded golden placeholder");
        return;
    }
    assert_eq!(scope, "compare");
    let actions = field_string(&case, "actions").expect("inputs.actions string");
    let mut table = SwissTable::new(5);
    let mut observations = Vec::new();
    for text in actions.split(';') {
        let (kind, numbers) = parse_action(text);
        let result = match kind {
            "insert" => {
                assert_ne!(numbers[0], 0, "key zero is outside the port domain");
                table.insert(numbers[0], numbers[1]).to_string()
            }
            "erase" => {
                assert_ne!(numbers[0], 0, "key zero is outside the port domain");
                table.erase(&numbers[0]).to_string()
            }
            "contains" => {
                assert_ne!(numbers[0], 0, "key zero is outside the port domain");
                table.contains(&numbers[0]).to_string()
            }
            "reserve" => {
                table.reserve(numbers[0] as usize);
                "null".to_owned()
            }
            "clear" => {
                table.clear();
                "null".to_owned()
            }
            "erase_if_all" | "erase_if_none" | "erase_if_odd" => {
                let capacity = table.table.capacity();
                let mut keys = Vec::new();
                for slot in 0..capacity {
                    if table.table.ctrl_ref().is_full(slot) {
                        keys.push(table.table.hash_at(slot));
                    }
                }
                let mut removed = 0usize;
                for key in keys {
                    let matches = kind == "erase_if_all"
                        || (kind == "erase_if_odd" && key & 1 == 1);
                    if matches && table.erase(&key) { removed += 1; }
                }
                removed.to_string()
            }
            _ => unreachable!(),
        };
        observations.push(format!(
            "{{\"action\":{},\"result\":{},\"size\":{},\"entries\":{}}}",
            json_string(text), result, table.len(), entries_json(&table)));
    }
    let value = format!(
        "{{\"observations\":[{}],\"final_entries\":{}}}",
        observations.join(","), entries_json(&table));
    let actual = format!(
        "{{\"case_id\":{},\"status\":\"ok\",\"value\":{}}}",
        json_string(case_id), value);
    assert_eq!(actual, golden, "complete oracle result mismatch for {case_id}");
}
'''


if __name__ == "__main__":
    generate()
