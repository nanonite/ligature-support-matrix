# Differential Oracle Protocol

Version: 1.0

This document is the shared contract for the C++ oracle driver, the Rust parity tests, and the coverage map in each pilot root. It describes observable differential behavior only. It is not the limitations-ledger schema: `case_id` is an oracle case identifier, not the limitations record field `id`.

## 1. Protocol invariants

Every pilot uses the same file roles:

- `oracle/cases.jsonl` contains input cases.
- `oracle/golden/results.jsonl` contains the C++ results captured from the pinned upstream checkout.
- `oracle/test-map.csv` maps upstream C++ test names and case IDs to Rust test names.
- A case generator may create additional case files, but each generated file has its own reproducibility metadata.
- All JSONL files are UTF-8, use LF line endings, contain no comments, and contain one JSON object per non-empty line. Empty lines are not permitted in committed case or result files.

The C++ implementation and the Rust implementation must agree on the operation name, input schema, result schema, error taxonomy, and value normalization for each operation. A driver or test must not invent a second interpretation of an input or result.

## 2. Case format

Each line is exactly one JSON object with these required fields:

```json
{"case_id":"boundary-add-normal-001","op":"add","inputs":{"a":2,"b":3}}
```

- `case_id` is a non-empty string, unique within one case file, and stable across regenerations.
- `op` is the operation name. Operation names are lower snake case unless an existing upstream API requires a different stable name.
- `inputs` is a JSON object. Its fields are defined by the operation contract for the pilot; unknown fields are an error rather than silently ignored input.

A case file may also contain these protocol metadata fields:

- `oracle_scope` is either `compare` or `excluded`. Its default is `compare`.
- `exclusion_reason` is required and must be a non-empty string when `oracle_scope` is `excluded`. It is forbidden when `oracle_scope` is `compare`.

The case format allows the two metadata fields above; no other undeclared top-level fields are added without updating this protocol and the pilot operation contract. This keeps case files interoperable while making observability exclusions explicit.

### 2.1 Stable case IDs

Use a deterministic naming convention:

```text
<source>-<operation>-<number>
```

`<source>` is one of:

- `upstream-test` for a case translated from an upstream C++ test;
- `boundary` for a hand-written boundary or edge case;
- `random` for a seeded-random case.

Use only lower-case ASCII letters, digits, and hyphens in the components. The numeric suffix is zero-padded to a fixed width, normally four digits, and is never reused within a file even when a case is removed. If an upstream test has several meaningful cases, include a short stable discriminator after the operation, for example `upstream-test-add-invalid-month-0001`. A changed input, operation, or expected behavior requires a new stable case ID; silently changing the meaning of an existing ID is prohibited.

`case_id` is not a global ledger key. A pilot may reuse a name in a different case file, but the file path is part of its identity. A test map should still spell out the file when more than one case file contains similarly named cases.

## 3. Result format

The C++ driver writes one result object for every case, including excluded cases:

```json
{"case_id":"boundary-add-normal-001","status":"ok","value":5}
```

An error result is:

```json
{"case_id":"boundary-add-overflow-003","status":"err","err_kind":"integer_overflow"}
```

The rules are:

- `case_id` is copied exactly from the input case.
- `status` is exactly `ok` or `err`.
- `value` is present if and only if `status` is `ok`.
- `err_kind` is present if and only if `status` is `err`.
- `err_kind` is a stable lower-snake-case string. It identifies the operation-level error category, not a transient message or stack trace.
- The result stream contains no duplicate or missing `case_id` values.

The result file is written in ascending bytewise lexicographic `case_id` order, regardless of the order in which cases were generated. The input file is the source of case identity; the result order is a deterministic artifact. A Rust checker may parse results by key, but a checked-in golden file must retain the required order.

### 3.1 Portable values and non-portable representations

`value` may be any JSON-serializable value: null, boolean, string, array, object, or number. The operation contract must define a canonical representation when a language-native value has no direct cross-language equivalent.

The following rules are mandatory:

- JSON numbers must be finite. `NaN` and positive or negative infinity are not result values; return `status: "err"` with an operation-defined stable `err_kind` such as `non_finite_result` instead.
- Signed 64-bit integer results are emitted as JSON integer numbers in the range `[-9223372036854775808, 9223372036854775807]`.
- An integer outside that range, or an integer whose exact representation is important, is emitted as a tagged object rather than a lossy floating-point number, for example `{"type":"integer","encoding":"decimal","value":"18446744073709551615"}`.
- A non-integral numeric result must use the pilot's declared decimal representation and comparison rule. If two languages cannot produce the same declared representation, the case is out of scope rather than compared approximately.
- Raw byte strings are never serialized as language-native byte objects. When bytes are genuinely observable and comparable, use a declared encoding such as `{"type":"bytes","encoding":"hex","value":"00ff"}` with lower-case hexadecimal and an explicit byte order in the operation contract.
- The excluded-case placeholder is `{"case_id":"...","status":"ok","value":null}`. The checker recognizes the placeholder from the case metadata and does not compare it as a behavioral value.

A raw hash value produced by a language's native hash implementation is not a portable value. The protocol never compares native hash algorithms or their raw internal bytes. When a pilot depends on hashing, the pilot injects the same versioned hash function, key, seed, and byte-order convention into both implementations and compares only outputs produced by that shared algorithm. This protocol does not certify that the two hash implementations are identical.

## 4. Golden-file decision

The C++ driver runs once against the pinned upstream commit and writes the checked-in `oracle/golden/results.jsonl`. The Rust test suite reads that golden file and compares its own results; the Rust test command does not rebuild or invoke the C++ driver.

This golden-file approach is required because it avoids requiring the C++ toolchain and upstream checkout at every `cargo nextest` run, makes Rust tests faster and usable in verifier-oriented environments, and makes the upstream observation reproducible at the recorded commit. The golden file is evidence of the C++ side, not a substitute for recording the upstream commit and refreshing the file when the pin changes.

### 4.1 Refreshing a golden file

When a pilot upstream pin changes:

1. Record the new upstream commit in the pilot descriptor and refresh the case manifest if the case source changed.
2. Build the pilot C++ driver with the flake-provided CMake and compiler.
3. Run the driver against the complete case file using the same operation and value normalization contract.
4. Review the complete `golden/results.jsonl` diff. A changed result requires an explanation tied to a case, an upstream change, or an intentional protocol change.
5. Run the generated Rust checks with `cargo nextest run --profile ci` and retain the JUnit artifact.
6. Update `test-map.csv` if source tests, case IDs, or generated Rust test names changed.
7. Record any behavior that became non-observable or non-portable as an explicit exclusion, not as a golden diff to be accepted automatically.

The upstream commit, case source, driver command, and any random seed are part of the refresh evidence. A golden file with no pinned upstream provenance is not accepted as a pilot oracle.

## 5. C++ driver contract

A pilot has one small C++ executable, conventionally named `oracle_driver`, built with CMake. Its command-line contract is:

```text
oracle_driver <cases.jsonl> <results.jsonl>
```

The driver must:

1. Read the UTF-8 JSONL case file from the first argument.
2. Validate required fields, uniqueness, operation schema, and exclusion metadata.
3. Sort cases by bytewise `case_id` order.
4. Execute `op(inputs)` against the pinned upstream C++ code for each comparable case.
5. Write exactly one result object per case to the second argument, also in `case_id` order.
6. Return zero only after the complete result file is flushed successfully; return non-zero for malformed input, an unknown operation, an internal driver failure, or a failure to write the output.
7. Keep diagnostics on stderr and keep the result stream valid JSONL. A case-level expected error is represented in its result object, not by aborting the whole driver.

The minimal CMake shape expected for a pilot is:

```cmake
cmake_minimum_required(VERSION 3.16)
project(pilot_oracle LANGUAGES CXX)

add_executable(oracle_driver driver.cpp)
target_compile_features(oracle_driver PRIVATE cxx_std_17)
```

A pilot may link the pinned upstream target and a project-approved JSON parser. The driver must not fetch upstream sources at runtime, silently substitute another revision, or use a different operation implementation from the one described by the case contract.

## 6. Rust test generator contract

Each pilot uses a small, inspectable codegen script named `generate_oracle_tests.py` rather than a `build.rs` or proc macro. The script reads `cases.jsonl` and `golden/results.jsonl`, validates that their case IDs agree, and writes a Rust integration-test file such as `rust/tests/generated_cases.rs` with one `#[test]` per case.

The chosen granularity is one test per case. The advantages are that nextest and JUnit report each case independently, a failing case is immediately visible, and the generated test name can be recorded in `test-map.csv`. The trade-off is generated-file churn and repeated fixture loading; both are acceptable for the small, bounded case files in this workspace. A pilot with very large case files may choose a parameterized test only by updating this protocol and its generator, not by mixing granularity within one pilot.

The generated tests, or their shared support code, must read both the case file and golden file at runtime, select the case by `case_id`, recompute the operation, and compare the complete result object. They must not invoke the C++ driver during `cargo nextest`. A generator run must be deterministic, reject duplicate or missing case IDs, and fail if a comparable case has no golden result.

From a pilot Rust workspace, the required command shape is:

```text
cargo nextest run --profile ci
```

The workspace configuration must include this JUnit setting. The `path` is relative to the nextest profile run directory, so `junit.xml` produces `target/nextest/ci/junit.xml` for the default `ci` profile in this workspace:

```toml
[profile.ci]
retries = 0

[profile.ci.junit]
path = "junit.xml"
```

The test run is not complete until the configured JUnit file exists and is nonempty. A pilot may choose a different relative path, but the command transcript must report the resulting path.

## 7. `test-map.csv`

The map has exactly these columns:

```csv
upstream_test_name,case_ids,nextest_test_name,coverage_status
```

- `upstream_test_name` is the stable upstream C++ test name, preferably its fully qualified name.
- `case_ids` is a semicolon-separated list of case IDs. It is empty when no case was created. Do not use commas inside this field.
- `nextest_test_name` is the exact generated Rust test name, or empty when there is no Rust test.
- `coverage_status` is exactly one of `mapped`, `unmapped`, or `rust-only`.

The meanings are:

- `mapped`: the upstream behavior has at least one comparable case whose Rust test compares against the golden result. Every listed comparable case is actually checked.
- `unmapped`: no comparable Rust parity is claimed. This includes a deliberately excluded observability property or an upstream test that has not yet been translated. If an excluded case is listed, its case metadata must contain the required exclusion reason.
- `rust-only`: the Rust test has no C++ analog, such as a Rust-only error variant. `case_ids` is empty, and this row must not be counted as differential parity.

When porting an upstream suite, first translate each upstream test into one or more cases where possible, then run the generator, then record the exact generated nextest name. Add boundary and random cases without pretending they are upstream tests. Review the map for duplicate upstream names, missing case IDs, stale Rust names, and rows whose `mapped` status is not backed by a comparable golden comparison.

## 8. Case sourcing and reproducibility

Every pilot combines three sources:

1. **Upstream tests:** translate upstream C++ tests one-to-one into cases where the behavior can be expressed as an operation and JSON inputs. Preserve the upstream test name in `test-map.csv`; the case ID uses the `upstream-test` prefix.
2. **Boundary cases:** add hand-written minimum, maximum, empty, malformed, invalid-domain, and transition cases using the `boundary` prefix. Boundary cases are intentional probes, not replacements for upstream coverage.
3. **Random cases:** generate deterministic cases with a recorded seed using the `random` prefix. A random case file must have adjacent reproducibility metadata, preferably `cases.jsonl.manifest.json`:

```json
{"case_file":"cases.jsonl","source":"random","seed":20260924,"generator":"pilot-rng-v1","command":"python3 tools/generate_random_cases.py --seed 20260924"}
```

The manifest also records the upstream commit when applicable. The seed, generator version, and command are required; a random file without them is not reproducible and must not be used as a golden source. The seed is metadata, not an extra case field, unless the operation explicitly consumes it as an input.

## 9. Non-observable and non-portable properties

The differential oracle compares only behavior that both sides expose through the documented operation. It cannot certify the following properties, and a passing differential result must never be reported as evidence for them:

- iteration order or traversal order when the C++ and Rust APIs do not promise the same order;
- pointer identity, addresses, allocation identity, or pointer stability across language implementations;
- raw native hash bytes, native hash algorithms, or internal hash representations across languages;
- Rust-only error variants with no C++ analog;
- any other property explicitly marked as unspecified by the C++ API or implementation-defined by the Rust side.

For P2 SwissTable, the oracle may compare observable map contents and specified operations, but not iteration order or pointer stability. This is the general oracle observability gap tracked as C.10 in chainlink epic #54. For P2 hashing, the pilot must inject the same hash implementation into the C++ driver and Rust port, including the algorithm version, key, seed, and byte-order convention. The protocol compares outputs from that shared algorithm; it does not compare the algorithms themselves.

A property is marked out of scope in the case file rather than quietly dropped:

```json
{"case_id":"boundary-iteration-order-004","op":"iteration-order","inputs":{"values":[3,1,2]},"oracle_scope":"excluded","exclusion_reason":"iteration order is not an observable cross-language contract"}
```

For an excluded case, the driver still emits a deterministic placeholder result with `status: "ok"` and `value: null`. The generated Rust test checks that the case and exclusion reason are present and that the placeholder is present, then skips behavioral comparison. A row for this case in `test-map.csv` is `unmapped`, not `mapped`. A Rust-only error variant is represented by a `rust-only` test-map row and does not receive a fabricated C++ golden result.

## 10. Worked standalone example

The workspace contains `oracle-example/` as a small format and plumbing check, separate from all three pilots. It uses integer `add(a, b)` with checked 64-bit addition:

- `cases.jsonl` has normal, negative, overflow, and excluded iteration-order cases.
- `driver.cpp` reads the JSONL file, checks the operation, and writes sorted golden results.
- `generate_oracle_tests.py` reads the cases and golden file and emits one nextest test per case.
- `rust-check/` recomputes each comparable case in Rust and compares the complete result object.
- The JUnit file is `oracle-example/rust-check/target/nextest/ci/junit.xml`.

The example is intentionally not a date, SwissTable, or Botan implementation. A pilot may copy the file layout and contracts, but must replace the operation, cases, driver, generator paths, and test map with its own pinned upstream data.
