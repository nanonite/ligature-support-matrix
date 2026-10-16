# date-creusot oracle operation contract

This document is the pilot operation contract referenced by
`oracle-PROTOCOL.md` (sections 1, 2, and 5). The C++ driver (`driver.cpp`)
and the Rust test generator (`generate_oracle_tests.py`) must agree with
this contract exactly; a driver or test that invents a second
interpretation of an input or result is a protocol violation.

## Operations

| op | inputs | result | C++ source (pinned v3.0.5) |
|---|---|---|---|
| `days_from_civil` | `y`, `m`, `d` | `value`: i32 epoch day count | `sys_days{year_month_day{year{y}, month{m}, day{d}}}` |
| `civil_from_days` | `z` | `value`: `{"y": i16, "m": u8, "d": u8}` | `year_month_day{sys_days{days{z}}}` |
| `weekday_from_days` | `z` | `value`: u8, 0=Sunday .. 6=Saturday | `weekday{sys_days{days{z}}}.c_encoding()` |
| `ymd_ok` | `y`, `m`, `d` | `value`: bool | `year_month_day{...}.ok()` |
| `iso_weekday_from_days` | `z` | `value`: u8, 1=Monday .. 7=Sunday | `iso_week::weekday{sys_days{days{z}}}` |

All operations are total over their input domain: the C++ spellings are
unguarded, and the Rust port deliberately mirrors that (evidence E-15:
`to_days` normalizes an out-of-range month/day into the following month
rather than failing). No operation in this contract returns `err`; a
case whose inputs fall outside the domain below is a malformed case and
the driver exits non-zero.

## Input domains

The domains are the representable ranges of the C++ newtypes, which the
Rust port mirrors exactly (`Year` = i16, `Month`/`Day` = u8, `Days` =
i32):

- `days_from_civil`, `ymd_ok`: `y` in `[-32768, 32767]`, `m` in
  `[0, 255]`, `d` in `[0, 255]`. (`-32768` is the single year for which
  `ok()` is false; out-of-range `m`/`d` normalize.)
- `civil_from_days`: `z` in `[-12687428, 11248737]`, the range
  `days_from_civil` produces over valid years. Outside it the C++ era
  decomposition has signed-overflow UB, so there is no defined behavior
  to port or compare.
- `weekday_from_days`, `iso_weekday_from_days`: `z` in `[INT32_MIN,
  INT32_MAX]`; both weekday spellings are defined for every `int`
  (evidence E-13).

## Result normalization

- `days_from_civil` results are JSON integers in `[-12687428, 11248737]`
  over the valid year domain (widening to `[-12687428 - 60, 11248737 +
  60]`-scale values only through the normalization probes); no tagged
  integer form is needed because every result fits i32.
- `civil_from_days` results are objects `{"y": ..., "m": ..., "d": ...}`
  with i16/u8 values, serialized as JSON integers.
- weekday results are JSON integers in `[0, 6]` (c_encoding) and `[1, 7]`
  (ISO) respectively.
- `ymd_ok` results are JSON booleans.

## Upstream provenance

- Upstream checkout: HowardHinnant/date v3.0.5, commit
  `179a6b921ccd6179b5b04dce812a89f71a51b4df`
  (`date-creusot/upstream/date`). The upstream test baseline (ctest
  inventory and statuses) is `date-creusot/upstream/test-baseline.txt`.
- The driver compiles against the upstream headers with the
  flake-provided CMake (`oracle/CMakeLists.txt`); it fetches nothing at
  runtime and links no JSON third party (the driver embeds a strict
  minimal parser so the golden pipeline has no dependencies beyond the
  pinned headers).
- Random cases: `tools/generate_random_cases.py --seed 20260924`,
  recorded in `oracle/cases.jsonl.manifest.json`.

## Upstream test coverage parity

`oracle/test-map.csv` maps the upstream ctest names for the pilot's
concept subset to case IDs and generated nextest test names. The one
`mapped` upstream test is `date_test_pass_year_month_day_test`; its
static assertions and its day-point conversion loop (every date in
`[-1000-01-01, 3000-12-31]`) are translated into `upstream-test-*`
cases. The other subset upstream tests (`date_test_pass_weekday_test`,
`iso_week_pass_weekday_test`, ...) exercise operations the pilot does not
port (weekday arithmetic, `last`, weeknum types), so their rows are
`unmapped` with no cases; the ported `weekday_from_days` and
`iso_weekday_from_days` functions are still differentially tested through
`boundary-*` and `random-*` cases.
