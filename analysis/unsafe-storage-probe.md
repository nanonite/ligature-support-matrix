# #35 — raw slot storage and Kani reach

Date: 2026-10-08. Pilot: `swisstable-verus`.

## Result

No new limitation was found beyond `swisstable-verus-001` and `swisstable-verus-003`. The existing gap remains: Abseil's generic raw-slot lifetime, address, allocator and sanitizer behavior is not represented by this Verus port. The current source has no unsafe layer for Kani to verify, so no Kani sub-cluster is warranted for this implementation.

## Evidence

- Pinned Abseil's layout uses a policy-parameterized `slot_type` array adjacent to control bytes (`upstream/abseil-cpp/absl/container/internal/raw_hash_set.h:67-79,2231-2236`). It poisons/unpoisons slot storage at control transitions and transfers/deallocates backing allocations during resize (`raw_hash_set.cc:505-516,2104-2135`).
- The port uses `ControlBytes.bytes: Vec<u8>`, `RawTable.hashes: Vec<u64>`, and `SwissTable.values: Vec<u64>` (`rust/swisstable-verus-core/src/control_bytes.rs:358-363`, `rust/swisstable-verus-core/src/raw_table.rs:179-195`, `rust/swisstable-verus-core/src/swiss_table.rs:57-62`). The slot values are initialized and zero marks an unused value; storage is not `Vec<Option<T>>` and no C++ object lifetime or pointer identity is modeled.
- A targeted syntax-pattern scan across `src/` and `verif/` found no `unsafe` blocks/functions/impls, raw pointer types, `MaybeUninit`, `from_raw` operations, or `transmute`. Its only textual match was the explanatory Rust doc comment in `rust/swisstable-verus-core/src/raw_table.rs:12`.
- `project-descriptor.json` declares `verifier_policy.default = "verus"`; it has no Kani support or cluster entry. This was read only and left unchanged.

## Decision

Keep the current initialized parallel Vec representation as the existing source-level scope cut. Do not introduce `Vec<Option<T>>` or an artificial unsafe layer solely to route it to Kani. If a future requirement adds raw/uninitialized storage or demands C++ lifetime/address parity, create a separate concrete implementation and then evaluate a Kani-owned cluster. The physical transfer gap remains open and linked to findings `swisstable-verus-001` and `swisstable-verus-003`.

No code, proof contract, verifier policy, or descriptor state changed. Kani was not run because the source under evaluation contains no unsafe code.
