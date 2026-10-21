# rdb Divergence Workflow

This workflow starts only after an oracle case in `oracle-PROTOCOL.md` fails: the Rust result disagrees with the C++ golden result for a specific `case_id`. It is a root-only workflow document. Each pilot keeps its own `findings/limitations.jsonl`; the schema is defined by the existing `findings-schema.md` and is not redefined here.

## 1. Trigger and evidence to preserve

A trigger is a failing case from the pilot Rust suite, normally from:

```text
cargo nextest run --profile ci
```

Preserve all of the following before changing the case, port, or oracle:

- the exact `case_id`;
- the complete `inputs` object from `oracle/cases.jsonl`;
- the corresponding `status`, `err_kind`, and `value` from `oracle/golden/results.jsonl`;
- the nextest test name, command, exit code, and failure output;
- the relevant pilot root and upstream commit.

A mismatch is not automatically a port defect. It may be a wrong Rust implementation, a stale golden result, a bad case, a shared-hash/configuration mistake, or a property that is explicitly non-observable. The workflow below finds the first differing value; the final classification is recorded after that investigation.

## 2. Minimize the case

Do not debug inside the full generated test suite. Extract the one failing `case_id` and its `inputs` into a standalone reproducer. The reproducer must contain the same operation and input values, the same expected result as the golden line, and no unrelated test cases.

For a JSONL case such as:

```json
{"case_id":"boundary-add-overflow-003","op":"add","inputs":{"a":9223372036854775807,"b":1}}
```

the standalone reproducer should retain:

```text
case_id: boundary-add-overflow-003
operation: add
inputs.a: 9223372036854775807
inputs.b: 1
expected: status=err, err_kind=integer_overflow
```

Do not modify the original `cases.jsonl` or `golden/results.jsonl` to make a failure disappear. If minimization changes the input, retain the original case as evidence and record the minimized command in `repro_cmd`.

## 3. Build a debuggable binary

Use a normal Cargo `[[bin]]` target, not a `cargo test` target. A test executable is placed under `target/debug/deps/` with a hashed name; a binary target is placed at the stable path that rdb consumes.

The target should be small and deterministic. A minimal `Cargo.toml` target is:

```toml
[[bin]]
name = "oracle_repro"
path = "src/bin/oracle_repro.rs"
```

The binary should parse or hard-code only the minimized inputs, call the operation entry point, and print the computed result and expected result. Build it in debug mode:

```text
cargo build --bin oracle_repro
```

The resulting executable is `target/debug/oracle_repro`. If the pilot needs source-level stepping, keep debug information enabled. The verified demo used `RUSTFLAGS="-C link-arg=-no-pie"` because rdb 0.0.0 accepts numeric addresses and the demo needed a stable symbol address. A normal position-independent pilot binary requires resolving the runtime load address; do not assume that a static `nm` address is valid for a PIE executable.

## 4. Run rdb

The installed executable is `/home/goya/.cargo/bin/rdb`, outside Nix. The flake's `rdbShellHook` puts it on PATH when present. The observed version is:

```text
rdb 0.0.0
```

The actual top-level help is:

```text
Usage: rdb [OPTIONS] [PROGRAM]

Arguments:
  [PROGRAM]

Options:
  -p, --pid <PID>
  -h, --help       Print help
  -V, --version    Print version
```

The in-REPL `help` command reports these commands:

```text
continue,c
step,s
next,n
finish
stepi,si
break,b <addr>
watch,wp set <addr> <size> <mode>
watch,wp clear <index>
watch,wp list
catch,cp syscall [name]
register,reg <name>
memory,mem <addr> [len]
backtrace,bt
disasm,dis <addr> [count]
variable,var list
variable,var <name>
expression,expr,e <expr>
up / down
thread,t
help,h [topic]
quit,q
```

Start the minimized binary with:

```text
rdb target/debug/oracle_repro
```

The rdb version in this workspace documents `break` as an address command, not a source-function command. Resolve the operation entry address before starting rdb, for example with `nm -C target/debug/oracle_repro`, and use the verified numeric address. A typical sequence is:

```text
break 0x211040
continue
variable list
register rsi
register rdx
next
variable list
register rax
next
continue
quit
```

The commands mean:

- `break 0x...` sets a software breakpoint at the operation entry.
- `continue` runs until that breakpoint.
- `variable list` lists visible local-variable locations.
- `register <name>` reads a machine register. In the verified Rust demo, the operation arguments were in `rsi` and `rdx`, and the returned value was in `rax` after the first source-level `next`.
- `next` performs a source-level step over the current line. Repeat it until the first line that changes the expected result.
- `memory <address> [length]` reads raw bytes when a local variable is in memory.
- `backtrace`, `disasm`, `up`, and `down` are available for locating the active frame and instruction.
- `quit` ends the session.

`expression` is listed by the in-REPL help but rdb 0.0.0 returned `expression evaluation not yet supported` for the demo. Use `variable`, `register`, and `memory` instead. `variable list` showed Rust local locations in the demo, while named local lookup was not sufficient for the register-passed arguments; register inspection supplied the exact values. This is a real rdb capability limitation, not a guessed command, and should be recorded as tooling friction if it blocks a pilot investigation.

### 4.1 First differing value

At the operation-entry breakpoint, record the minimized inputs and expected result. After each `next`, record the source line, relevant register or memory value, and the first point where the computed value no longer can produce the golden result. Continue only far enough to establish that point; do not debug unrelated later code.

The verified issue #8 demo transcript was:

```text
breakpoint set at 0x211040
Stopped(Pid(1504289), SIGTRAP)
a = 0x7fffffff5d68 (i64)
b = 0x7fffffff5d70 (i64)
rsi = 0x7fffffffffffffff
rdx = 0x1
/home/goya/storage/full-ligature-port-workspace/oracle-example/rdb-demo/src/lib.rs:2
a = 0x7fffffff5cf0 (i64)
b = 0x7fffffff5cf8 (i64)
rax = 0x7fffffffffffffff
/home/goya/storage/full-ligature-port-workspace/oracle-example/rdb-demo/src/lib.rs:3
case_id=boundary-add-overflow-003 a=9223372036854775807 b=1 expected=Err("integer_overflow") result=Ok(9223372036854775807)
Exited(Pid(1504289), 0)
```

The golden result is `status=err, err_kind=integer_overflow`. The first differing value is at `src/lib.rs:2`: the inputs are `i64::MAX` and `1`, but the deliberate branch assigns `a` and produces `rax=0x7fffffffffffffff`, so the binary returns `Ok(9223372036854775807)` instead of the expected overflow error. The demo bug was fixed after this transcript was captured.

## 5. Classify and record the outcome

There are two valid outcomes:

1. **Port defect:** the minimized Rust operation computes a different observable result. Keep the minimized case, fix or scope-cut the Rust implementation, rerun nextest, and record the finding in the relevant pilot's `findings/limitations.jsonl` according to `findings-schema.md`.
2. **Test or oracle defect:** the Rust implementation and golden result are correct, but the case, result, shared configuration, or test expectation is wrong. Fix the test/oracle input, document the correction in the same ledger shape, and do not claim port parity from the old golden result.

A finding uses the existing schema fields, including `id`, `pilot`, `stage`, `command`, `tool`, `chain`, `symptom`, `repro_cmd`, `exit_code`, `expected`, `actual`, `workaround`, `severity`, `revisit_trigger`, `pyz_sha256`, `tool_path`, and `tool_version`. For an rdb investigation, `tool` is `rdb` when rdb located the first differing value, `tool_path` is the resolved rdb path, and `tool_version` is the output from `rdb --version`. The `command` and `exit_code` should preserve the failing nextest command and its non-zero exit code; `repro_cmd` should contain the minimized rdb invocation. The `pyz_sha256` is the relevant pilot's pinned ligature artifact hash, not a hash of rdb. Keep the oracle `case_id` in `symptom` and `actual`; do not add a second top-level `case_id` field to the limitations schema.

For the issue #8 demo, the divergence was a deliberate throwaway Rust implementation bug, not a finding in date-creusot, swisstable-verus, or crypto-mixed. The bug was fixed and the demo now passes, so no pilot limitation entry was fabricated. A real pilot divergence must be recorded in that pilot's ledger after classification.

## 6. Completion checklist

- The original failing `case_id`, inputs, golden result, and nextest output are preserved.
- The case is minimized outside the generated test suite.
- A `[[bin]]` target exists and runs from `target/debug/<name>`.
- rdb is invoked through the flake shell and its version/path are recorded in the pilot `tools/versions.lock`.
- The operation-entry breakpoint is set with a verified rdb address.
- `variable`, `register`, or `memory` inspection and source-level `next` steps identify the first differing value.
- The result is classified as a port defect or a test/oracle defect.
- A real pilot defect or correction is recorded using `findings-schema.md`; the throwaway demo is fixed or removed.
