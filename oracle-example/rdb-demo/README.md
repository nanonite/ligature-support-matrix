# rdb divergence demo

This crate is a deliberate, isolated demonstration of the divergence workflow. Its `add` implementation initially returned `Ok(i64::MAX)` for the overflow case, making the single `boundary_add_overflow_003` test fail against the expected `Err("integer_overflow")` result from the protocol golden file. The issue #8 transcript was captured with that bug present; the implementation is now fixed and the test passes.

The `rdb_add_divergence` binary is a standalone `[[bin]]` target for stepping through the minimized case. The demo does not modify the verified `oracle-example/cases.jsonl`, `oracle-example/golden/results.jsonl`, `oracle-example/driver.cpp`, or `oracle-example/rust-check/`.
