# #34 — Vec-backed control-byte layout and proof cost

Date: 2026-10-08. Pilot: `swisstable-verus`.

## Evidence

- Pinned Abseil lays out `capacity` real control bytes, a sentinel, and `Group::kWidth - 1` cloned bytes (`upstream/abseil-cpp/absl/container/internal/raw_hash_set.h:70-77,1149-1153`). At width 16, `NumControlBytes` is `capacity + 16`.
- `InitializeMirroredControlBytes` initializes the sentinel plus the first 15 control-byte mirrors (`raw_hash_set.cc:1461-1467`); `SetCtrlNoSanitizeImpl` keeps the corresponding mirror synchronized on control-byte updates (`raw_hash_set.cc:523-529`).
- The port allocates `capacity + 1 + 16` bytes. Index `capacity` is the sentinel and all 16 following bytes are `EMPTY` (`rust/swisstable-verus-core/src/control_bytes.rs:358-401,415-430`). This is one byte larger than the upstream width-16 layout and, more significantly, these bytes do not mirror the first 15 slots.
- `GroupProbe` owns a `Vec<u8>` window. Each load clears it and pushes 16 bytes from the source Vec one at a time; each mask is then built by a 16-step scalar loop (`rust/swisstable-verus-core/src/group_probe.rs:61-65,86-100,121-143,150-208,214-235`). Upstream x86-64 uses an unaligned 16-byte SSE load and derives masks with vector comparisons and movemask (`hashtable_control_bytes.h:277-315`).
- `RawTable::find` only accepts candidate positions below `capacity` (`rust/swisstable-verus-core/src/raw_table.rs:723-724`). If the window's free mask is nonzero it stops the group walk (`raw_table.rs:757-760`) and runs a full-slot fallback (`:762-780`). For a concrete width-16 example, with `capacity = 31` and `base = 17`, the window spans slots 17–30, the sentinel at 31, and the first mirrored slot at 32. If slot 0 is full, upstream has no free bit in that window; the port reads `EMPTY` at 32 and sets the free bit. An all-`EMPTY` tail can therefore stop a near-end probe even when the mirrored prefix bytes upstream would be occupied. The fallback preserves lookup completeness; it does not restore the original group-probe cost.

## Root cause

The control-byte invariant models a sentinel followed by static all-empty padding, while Abseil's invariant models a sentinel followed by live mirrors of the first 15 control bytes. The port's setters update only the primary slot and their frame clauses promise every other byte remains unchanged (`rust/swisstable-verus-core/src/control_bytes.rs:725-770`); there is no mirror relation to preserve. Consequently, a group that crosses the array end receives different input bytes from the upstream group, and `MaskEmptyOrDeleted` can report padding as an early free position.

This is a representation/transfer gap, not a failed proof of the current contracts: the full-slot fallback maintains completeness. Correct mirror semantics would require changing the representation invariant and the control-byte mutator frame obligations, which #34 explicitly keeps intact. No production code or proof contract was changed here.

## Proof and transfer cost

The current pinned crate verification was run as:

```text
cd rust/swisstable-verus-core && PATH=/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/7igjywfjlfa7v2sknkd9dbvpv2s5qf6g-z3-4.15.4/bin:/home/goya/.cargo/bin:$PATH CARGO_TARGET_DIR=/tmp/issue34-verus-target cargo verus verify --locked
```

The crate result was `verification results:: 149 verified, 0 errors`; Cargo finished with `Finished dev profile`. This is a whole-crate baseline, not a differential measurement of the Vec representation. The proof-facing costs visible in the implementation are explicit Vec length/shape invariants, a scalar 16-byte load loop with an index-bound invariant, and scalar bit-mask loops with bit-vector lemmas. No alternate representation or performance benchmark was run, so the marginal runtime/proof cost is not quantified.

## Outcome

Keep the existing Vec-backed production representation and #30 contracts for this task. Record the missing mirrors and scalar-copy path as a worked-around transfer gap, linked to the already-documented full-scan fallback (`swisstable-verus-004`). Revisit if the later group-probe or oracle work requires upstream window behavior or makes a performance claim.
