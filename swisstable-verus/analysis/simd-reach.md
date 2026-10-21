# #36 — SIMD group-probing reach

Date: 2026-10-08. Pilot: `swisstable-verus`.

## Result

No new limitation was found beyond `swisstable-verus-002`. For the current P2 implementation, group probing remains scalar-only and SIMD is recorded as a scope cut. This is a statement about the selected port boundary, not evidence that Verus cannot verify every intrinsic or that Kani owns an implementation.

## Evidence

- The pinned Abseil chooses `GroupSse2Impl` on SSE2 systems (16 lanes), `GroupAArch64Impl` on supported AArch64 systems (8 lanes), and `GroupPortableImpl` otherwise (8 lanes) (`upstream/abseil-cpp/absl/container/internal/hashtable_control_bytes.h:277-315,361-377,441-460,504-521`). The implementations use architecture-specific loads/comparisons and convert lanes into masks.
- The Rust port has only a scalar 16-byte `GroupProbe`; the current source scan found no architecture intrinsics, `target_feature`, or SIMD types. The existing `grep -c '_mm_\|std::arch\|core::arch' rust/swisstable-verus-core/src/group_probe.rs` output was `0` with exit 1; the only wider-source `_mm_` match is an explanatory comment for the upstream clear-dead operation.
- The descriptor remains `verifier_policy.default = "verus"` and has no Kani cluster. There is no SIMD implementation to assign to either verifier.

## Decision and limit

Keep the scalar 16-wide path as the current P2 subset and record the SIMD implementation as a scope cut. Do not create a Kani cluster or change the descriptor. The scalar loops express per-lane mask predicates for a fixed input window; this does not establish instruction/performance parity, the 8-lane group scheduling on AArch64/portable builds, or any verifier's reach over a future intrinsic implementation. No performance benchmark was run, and no code or proof contract changed. `E-010` remains deferred for the operator's Stage 4 review.
