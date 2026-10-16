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

#[test]
fn boundary_civil_from_days_era_0001() {
    assert_case("boundary-civil-from-days-era-0001");
}

#[test]
fn boundary_civil_from_days_era_0002() {
    assert_case("boundary-civil-from-days-era-0002");
}

#[test]
fn boundary_civil_from_days_era_0003() {
    assert_case("boundary-civil-from-days-era-0003");
}

#[test]
fn boundary_civil_from_days_era_0004() {
    assert_case("boundary-civil-from-days-era-0004");
}

#[test]
fn boundary_civil_from_days_era_0005() {
    assert_case("boundary-civil-from-days-era-0005");
}

#[test]
fn boundary_days_from_civil_era_0001() {
    assert_case("boundary-days-from-civil-era-0001");
}

#[test]
fn boundary_days_from_civil_era_0002() {
    assert_case("boundary-days-from-civil-era-0002");
}

#[test]
fn boundary_days_from_civil_era_0003() {
    assert_case("boundary-days-from-civil-era-0003");
}

#[test]
fn boundary_days_from_civil_era_0004() {
    assert_case("boundary-days-from-civil-era-0004");
}

#[test]
fn boundary_days_from_civil_era_0005() {
    assert_case("boundary-days-from-civil-era-0005");
}

#[test]
fn boundary_days_from_civil_era_0006() {
    assert_case("boundary-days-from-civil-era-0006");
}

#[test]
fn boundary_days_from_civil_era_0007() {
    assert_case("boundary-days-from-civil-era-0007");
}

#[test]
fn boundary_days_from_civil_leap_0001() {
    assert_case("boundary-days-from-civil-leap-0001");
}

#[test]
fn boundary_days_from_civil_leap_0002() {
    assert_case("boundary-days-from-civil-leap-0002");
}

#[test]
fn boundary_days_from_civil_leap_0003() {
    assert_case("boundary-days-from-civil-leap-0003");
}

#[test]
fn boundary_days_from_civil_leap_0004() {
    assert_case("boundary-days-from-civil-leap-0004");
}

#[test]
fn boundary_days_from_civil_leap_0005() {
    assert_case("boundary-days-from-civil-leap-0005");
}

#[test]
fn boundary_days_from_civil_normalize_0001() {
    assert_case("boundary-days-from-civil-normalize-0001");
}

#[test]
fn boundary_days_from_civil_normalize_0002() {
    assert_case("boundary-days-from-civil-normalize-0002");
}

#[test]
fn boundary_days_from_civil_normalize_0003() {
    assert_case("boundary-days-from-civil-normalize-0003");
}

#[test]
fn boundary_days_from_civil_normalize_0004() {
    assert_case("boundary-days-from-civil-normalize-0004");
}

#[test]
fn boundary_days_from_civil_normalize_0005() {
    assert_case("boundary-days-from-civil-normalize-0005");
}

#[test]
fn boundary_days_from_civil_normalize_0006() {
    assert_case("boundary-days-from-civil-normalize-0006");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0001() {
    assert_case("boundary-iso-weekday-from-days-negative-0001");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0002() {
    assert_case("boundary-iso-weekday-from-days-negative-0002");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0003() {
    assert_case("boundary-iso-weekday-from-days-negative-0003");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0004() {
    assert_case("boundary-iso-weekday-from-days-negative-0004");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0005() {
    assert_case("boundary-iso-weekday-from-days-negative-0005");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0006() {
    assert_case("boundary-iso-weekday-from-days-negative-0006");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0007() {
    assert_case("boundary-iso-weekday-from-days-negative-0007");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0008() {
    assert_case("boundary-iso-weekday-from-days-negative-0008");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0009() {
    assert_case("boundary-iso-weekday-from-days-negative-0009");
}

#[test]
fn boundary_iso_weekday_from_days_negative_0010() {
    assert_case("boundary-iso-weekday-from-days-negative-0010");
}

#[test]
fn boundary_weekday_from_days_negative_0001() {
    assert_case("boundary-weekday-from-days-negative-0001");
}

#[test]
fn boundary_weekday_from_days_negative_0002() {
    assert_case("boundary-weekday-from-days-negative-0002");
}

#[test]
fn boundary_weekday_from_days_negative_0003() {
    assert_case("boundary-weekday-from-days-negative-0003");
}

#[test]
fn boundary_weekday_from_days_negative_0004() {
    assert_case("boundary-weekday-from-days-negative-0004");
}

#[test]
fn boundary_weekday_from_days_negative_0005() {
    assert_case("boundary-weekday-from-days-negative-0005");
}

#[test]
fn boundary_weekday_from_days_negative_0006() {
    assert_case("boundary-weekday-from-days-negative-0006");
}

#[test]
fn boundary_weekday_from_days_negative_0007() {
    assert_case("boundary-weekday-from-days-negative-0007");
}

#[test]
fn boundary_weekday_from_days_negative_0008() {
    assert_case("boundary-weekday-from-days-negative-0008");
}

#[test]
fn boundary_weekday_from_days_negative_0009() {
    assert_case("boundary-weekday-from-days-negative-0009");
}

#[test]
fn boundary_weekday_from_days_negative_0010() {
    assert_case("boundary-weekday-from-days-negative-0010");
}

#[test]
fn boundary_ymd_ok_boundary_0001() {
    assert_case("boundary-ymd-ok-boundary-0001");
}

#[test]
fn boundary_ymd_ok_boundary_0002() {
    assert_case("boundary-ymd-ok-boundary-0002");
}

#[test]
fn boundary_ymd_ok_boundary_0003() {
    assert_case("boundary-ymd-ok-boundary-0003");
}

#[test]
fn boundary_ymd_ok_boundary_0004() {
    assert_case("boundary-ymd-ok-boundary-0004");
}

#[test]
fn boundary_ymd_ok_boundary_0005() {
    assert_case("boundary-ymd-ok-boundary-0005");
}

#[test]
fn boundary_ymd_ok_boundary_0006() {
    assert_case("boundary-ymd-ok-boundary-0006");
}

#[test]
fn boundary_ymd_ok_boundary_0007() {
    assert_case("boundary-ymd-ok-boundary-0007");
}

#[test]
fn boundary_ymd_ok_boundary_0008() {
    assert_case("boundary-ymd-ok-boundary-0008");
}

#[test]
fn boundary_ymd_ok_boundary_0009() {
    assert_case("boundary-ymd-ok-boundary-0009");
}

#[test]
fn boundary_ymd_ok_boundary_0010() {
    assert_case("boundary-ymd-ok-boundary-0010");
}

#[test]
fn boundary_ymd_ok_boundary_0011() {
    assert_case("boundary-ymd-ok-boundary-0011");
}

#[test]
fn boundary_ymd_ok_boundary_0012() {
    assert_case("boundary-ymd-ok-boundary-0012");
}

#[test]
fn boundary_ymd_ok_boundary_0013() {
    assert_case("boundary-ymd-ok-boundary-0013");
}

#[test]
fn boundary_ymd_ok_boundary_0014() {
    assert_case("boundary-ymd-ok-boundary-0014");
}

#[test]
fn boundary_ymd_ok_boundary_0015() {
    assert_case("boundary-ymd-ok-boundary-0015");
}

#[test]
fn boundary_ymd_ok_invalid_0001() {
    assert_case("boundary-ymd-ok-invalid-0001");
}

#[test]
fn boundary_ymd_ok_invalid_0002() {
    assert_case("boundary-ymd-ok-invalid-0002");
}

#[test]
fn boundary_ymd_ok_invalid_0003() {
    assert_case("boundary-ymd-ok-invalid-0003");
}

#[test]
fn boundary_ymd_ok_invalid_0004() {
    assert_case("boundary-ymd-ok-invalid-0004");
}

#[test]
fn boundary_ymd_ok_invalid_0005() {
    assert_case("boundary-ymd-ok-invalid-0005");
}

#[test]
fn random_civil_from_days_0001() {
    assert_case("random-civil-from-days-0001");
}

#[test]
fn random_civil_from_days_0002() {
    assert_case("random-civil-from-days-0002");
}

#[test]
fn random_civil_from_days_0003() {
    assert_case("random-civil-from-days-0003");
}

#[test]
fn random_civil_from_days_0004() {
    assert_case("random-civil-from-days-0004");
}

#[test]
fn random_civil_from_days_0005() {
    assert_case("random-civil-from-days-0005");
}

#[test]
fn random_civil_from_days_0006() {
    assert_case("random-civil-from-days-0006");
}

#[test]
fn random_civil_from_days_0007() {
    assert_case("random-civil-from-days-0007");
}

#[test]
fn random_civil_from_days_0008() {
    assert_case("random-civil-from-days-0008");
}

#[test]
fn random_civil_from_days_0009() {
    assert_case("random-civil-from-days-0009");
}

#[test]
fn random_civil_from_days_0010() {
    assert_case("random-civil-from-days-0010");
}

#[test]
fn random_civil_from_days_0011() {
    assert_case("random-civil-from-days-0011");
}

#[test]
fn random_civil_from_days_0012() {
    assert_case("random-civil-from-days-0012");
}

#[test]
fn random_days_from_civil_0001() {
    assert_case("random-days-from-civil-0001");
}

#[test]
fn random_days_from_civil_0002() {
    assert_case("random-days-from-civil-0002");
}

#[test]
fn random_days_from_civil_0003() {
    assert_case("random-days-from-civil-0003");
}

#[test]
fn random_days_from_civil_0004() {
    assert_case("random-days-from-civil-0004");
}

#[test]
fn random_days_from_civil_0005() {
    assert_case("random-days-from-civil-0005");
}

#[test]
fn random_days_from_civil_0006() {
    assert_case("random-days-from-civil-0006");
}

#[test]
fn random_days_from_civil_0007() {
    assert_case("random-days-from-civil-0007");
}

#[test]
fn random_days_from_civil_0008() {
    assert_case("random-days-from-civil-0008");
}

#[test]
fn random_days_from_civil_0009() {
    assert_case("random-days-from-civil-0009");
}

#[test]
fn random_days_from_civil_0010() {
    assert_case("random-days-from-civil-0010");
}

#[test]
fn random_days_from_civil_0011() {
    assert_case("random-days-from-civil-0011");
}

#[test]
fn random_days_from_civil_0012() {
    assert_case("random-days-from-civil-0012");
}

#[test]
fn random_days_from_civil_0013() {
    assert_case("random-days-from-civil-0013");
}

#[test]
fn random_days_from_civil_0014() {
    assert_case("random-days-from-civil-0014");
}

#[test]
fn random_days_from_civil_0015() {
    assert_case("random-days-from-civil-0015");
}

#[test]
fn random_days_from_civil_0016() {
    assert_case("random-days-from-civil-0016");
}

#[test]
fn random_iso_weekday_from_days_0001() {
    assert_case("random-iso-weekday-from-days-0001");
}

#[test]
fn random_iso_weekday_from_days_0002() {
    assert_case("random-iso-weekday-from-days-0002");
}

#[test]
fn random_iso_weekday_from_days_0003() {
    assert_case("random-iso-weekday-from-days-0003");
}

#[test]
fn random_iso_weekday_from_days_0004() {
    assert_case("random-iso-weekday-from-days-0004");
}

#[test]
fn random_iso_weekday_from_days_0005() {
    assert_case("random-iso-weekday-from-days-0005");
}

#[test]
fn random_iso_weekday_from_days_0006() {
    assert_case("random-iso-weekday-from-days-0006");
}

#[test]
fn random_iso_weekday_from_days_0007() {
    assert_case("random-iso-weekday-from-days-0007");
}

#[test]
fn random_iso_weekday_from_days_0008() {
    assert_case("random-iso-weekday-from-days-0008");
}

#[test]
fn random_iso_weekday_from_days_0009() {
    assert_case("random-iso-weekday-from-days-0009");
}

#[test]
fn random_iso_weekday_from_days_0010() {
    assert_case("random-iso-weekday-from-days-0010");
}

#[test]
fn random_weekday_from_days_0001() {
    assert_case("random-weekday-from-days-0001");
}

#[test]
fn random_weekday_from_days_0002() {
    assert_case("random-weekday-from-days-0002");
}

#[test]
fn random_weekday_from_days_0003() {
    assert_case("random-weekday-from-days-0003");
}

#[test]
fn random_weekday_from_days_0004() {
    assert_case("random-weekday-from-days-0004");
}

#[test]
fn random_weekday_from_days_0005() {
    assert_case("random-weekday-from-days-0005");
}

#[test]
fn random_weekday_from_days_0006() {
    assert_case("random-weekday-from-days-0006");
}

#[test]
fn random_weekday_from_days_0007() {
    assert_case("random-weekday-from-days-0007");
}

#[test]
fn random_weekday_from_days_0008() {
    assert_case("random-weekday-from-days-0008");
}

#[test]
fn random_weekday_from_days_0009() {
    assert_case("random-weekday-from-days-0009");
}

#[test]
fn random_weekday_from_days_0010() {
    assert_case("random-weekday-from-days-0010");
}

#[test]
fn random_ymd_ok_0001() {
    assert_case("random-ymd-ok-0001");
}

#[test]
fn random_ymd_ok_0002() {
    assert_case("random-ymd-ok-0002");
}

#[test]
fn random_ymd_ok_0003() {
    assert_case("random-ymd-ok-0003");
}

#[test]
fn random_ymd_ok_0004() {
    assert_case("random-ymd-ok-0004");
}

#[test]
fn random_ymd_ok_0005() {
    assert_case("random-ymd-ok-0005");
}

#[test]
fn random_ymd_ok_0006() {
    assert_case("random-ymd-ok-0006");
}

#[test]
fn random_ymd_ok_0007() {
    assert_case("random-ymd-ok-0007");
}

#[test]
fn random_ymd_ok_0008() {
    assert_case("random-ymd-ok-0008");
}

#[test]
fn random_ymd_ok_0009() {
    assert_case("random-ymd-ok-0009");
}

#[test]
fn random_ymd_ok_0010() {
    assert_case("random-ymd-ok-0010");
}

#[test]
fn random_ymd_ok_0011() {
    assert_case("random-ymd-ok-0011");
}

#[test]
fn random_ymd_ok_0012() {
    assert_case("random-ymd-ok-0012");
}

#[test]
fn random_ymd_ok_0013() {
    assert_case("random-ymd-ok-0013");
}

#[test]
fn random_ymd_ok_0014() {
    assert_case("random-ymd-ok-0014");
}

#[test]
fn upstream_test_civil_from_days_1969_12_31_0001() {
    assert_case("upstream-test-civil-from-days-1969-12-31-0001");
}

#[test]
fn upstream_test_civil_from_days_2015_08_09_0001() {
    assert_case("upstream-test-civil-from-days-2015-08-09-0001");
}

#[test]
fn upstream_test_civil_from_days_day_point_0001() {
    assert_case("upstream-test-civil-from-days-day-point-0001");
}

#[test]
fn upstream_test_civil_from_days_day_point_0002() {
    assert_case("upstream-test-civil-from-days-day-point-0002");
}

#[test]
fn upstream_test_days_from_civil_1969_12_31_0001() {
    assert_case("upstream-test-days-from-civil-1969-12-31-0001");
}

#[test]
fn upstream_test_days_from_civil_2015_08_09_0001() {
    assert_case("upstream-test-days-from-civil-2015-08-09-0001");
}

#[test]
fn upstream_test_days_from_civil_day_point_0001() {
    assert_case("upstream-test-days-from-civil-day-point-0001");
}

#[test]
fn upstream_test_days_from_civil_day_point_0002() {
    assert_case("upstream-test-days-from-civil-day-point-0002");
}

#[test]
fn upstream_test_days_from_civil_day_point_0003() {
    assert_case("upstream-test-days-from-civil-day-point-0003");
}

#[test]
fn upstream_test_days_from_civil_day_point_0004() {
    assert_case("upstream-test-days-from-civil-day-point-0004");
}

#[test]
fn upstream_test_days_from_civil_day_point_0005() {
    assert_case("upstream-test-days-from-civil-day-point-0005");
}

#[test]
fn upstream_test_weekday_from_days_day_point_0001() {
    assert_case("upstream-test-weekday-from-days-day-point-0001");
}

#[test]
fn upstream_test_weekday_from_days_day_point_0002() {
    assert_case("upstream-test-weekday-from-days-day-point-0002");
}

#[test]
fn upstream_test_weekday_from_days_day_point_0003() {
    assert_case("upstream-test-weekday-from-days-day-point-0003");
}

#[test]
fn upstream_test_ymd_ok_2000_02_29_0001() {
    assert_case("upstream-test-ymd-ok-2000-02-29-0001");
}

#[test]
fn upstream_test_ymd_ok_2000_02_30_0001() {
    assert_case("upstream-test-ymd-ok-2000-02-30-0001");
}

#[test]
fn upstream_test_ymd_ok_2100_02_28_0001() {
    assert_case("upstream-test-ymd-ok-2100-02-28-0001");
}

#[test]
fn upstream_test_ymd_ok_2100_02_29_0001() {
    assert_case("upstream-test-ymd-ok-2100-02-29-0001");
}
