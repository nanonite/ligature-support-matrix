# Issue #38 — Miri suite and rehash path under rdb

Date: 2026-10-10

## Miri over the generated nextest suite

The first run used the pinned nightly through the SwissTable dev shell without changing Miri isolation. It failed because the generated oracle tests read JSONL fixtures from disk; Miri's default isolation rejects `open` (`unsupported operation: open not available when isolation is enabled`). This is test-harness file I/O, not a Rust undefined-behavior report.

The suite passes when run with `MIRIFLAGS=-Zmiri-disable-isolation`:

```text
cd rust/swisstable-verus-core
rustup run nightly-2026-04-21-x86_64-unknown-linux-gnu cargo miri nextest run --locked --profile ci --config-file ../../oracle/nextest.toml
```

with `MIRIFLAGS=-Zmiri-disable-isolation` in the environment and from the `swisstable-verus` Nix dev shell. Result:

```text
Preparing a sysroot for Miri ... done
Starting 16 tests across 2 binaries
Summary [ 11.127s] 16 tests run: 16 passed, 0 skipped
```

JUnit `rust/swisstable-verus-core/target/nextest/ci/junit.xml`: 16 testcases, 0 failures, 0 errors. The run ID is `f3b8b9c8-30e5-47be-a2e7-0b6547ca5f46`. Finding `swisstable-verus-037` records the isolation friction and workaround. The findings schema has no `miri` tool value, so this `cargo miri nextest` runner finding uses its permitted `nextest` value. No production source or test code changed.

## Rehash path under rdb

A temporary standalone binary in `/tmp/issue38-rdb` constructed `SwissTable::new(5)`, inserted keys 1–6 with values `key * 100`, and called `reserve(1)`. It asserted all keys remained present and every occupied slot still associated each key with its value. The binary was built in debug mode with a non-PIE final link so rdb's numeric software breakpoints could use the resolved addresses. No pilot Cargo manifest was edited.

The resolved symbols were:

```text
00000000002132e0 T swisstable_verus_core::swiss_table::SwissTable::reserve
0000000000214db0 T swisstable_verus_core::raw_table::RawTable::resize
```

rdb was run from the project's Nix dev shell (`/home/goya/.cargo/bin/rdb`, `rdb 0.0.0`). At the `reserve` breakpoint, `additional` was 1 (`rsi = 0x1`). After stepping over the entry, the resize breakpoint showed `new_capacity_bits = 6` (`rsi = 0x6`) and this stack:

```text
#0 RawTable::resize
#1 SwissTable::reserve
#2 rehash_probe::trigger_rehash
#3 rehash_probe::main
```

Source-level `next` steps reached `raw_table.rs:1160` (`RawTable::new`), the transfer loop at `:1165`, the live-slot branch at `:1221`, and the first reinsert at `:1264`. Continuing completed all assertions:

```text
rehash_probe before_capacity=31 after_capacity=63 before_len=6 after_len=6 retained_key_values=6
Exited(Pid(...), 0)
```

No mismatch or rehash defect was found. Since there was no oracle failure, this was a direct path exercise, not a divergence investigation. The existing rdb path/version entries in `tools/versions.lock` were used unchanged.

## Scope and closeout checks

- `python3 tools/ligature/ligature.pyz write-set-check --issue 38 --json` returned `"state":"clean"`, `"mutated_workspace":false`, and `"violations":[]`.
- `flake.nix` SHA-256: `f837c3419f226c97399b6f48c4a2d0c8fd7c4abf159cbc699c510b88ef0694a9`.
- `flake.lock` SHA-256: `79232a474e4623868368bd9fd0c2c12807cc8d685b9e7dffc8ded5ca00ff8eb6`.
- No descriptor, Cargo manifest, production source, verifier scope, Kani cluster, or Ligature configuration changed. The standalone probe and target directory stayed under `/tmp`.
- No new C++→Rust behavior gap was identified, so `PORT-GAPS.md` needed no new entry.
