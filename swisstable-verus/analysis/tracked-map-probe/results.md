# Tracked Map probe results — Chainlink #120

Date: 2026-10-08. The original pilot contracts remain unchanged; every tracked-map
integration edit is in the `reproduction/` analysis clone.

## P1 and P2 smoke reproduction

- `p1.rs` uses an exec struct containing `Tracked<GhostState>`, a tracked struct with
  `Map<u64,u64>`, and `tracked_empty/insert/remove`. P1 transcript:
  `verification results:: 4 verified, 0 errors`.
- `p2.rs` adds a bounded insert loop, two-way domain invariants, and broadcast
  map/set axiom groups. P2 transcript: `verification results:: 4 verified, 0 errors`.

Both source files and complete direct-Verus transcripts are retained next to this
report. From this directory, with the pinned Verus binary on `PATH`, the exact commands
are `verus --crate-type=lib --multiple-errors 20 p1.rs` and the same command with
`p2.rs`; each transcript is the complete one-line verifier result. The pinned binary
reports `Verus 0.2026.05.24.ecee80a` (release, linux_x86_64, toolchain
1.95.0-x86_64-unknown-linux-gnu).

## Integrated model, erase, and resize

The reproduction clone adds a tracked `LiveIndex` with `Map<u64, usize>` to `RawTable`.
Its map domain is the set of live hashes and each value is the physical slot currently
holding that hash. `live_map_model()` states both directions directly: every full slot
has a map entry at its slot index, and every map key resolves to a full slot. It does
not prove equality of two `Set::new` comprehensions and does not use `ext_equal`.

`RawTable::insert` adds a new key/slot entry only on insertion; `erase` removes the
key, and `clear` resets the tracked map. The erase contract names both branches:
`WasNeverFull` implies the erased byte is empty and the final map/slot model holds;
the other branch implies a tombstone and the same final model. Concrete control-window
fixtures verify the predicate returns the `kEmpty` outcome for one isolated full slot
and `kDeleted` for a 16-slot run around the erased index. The method proof verifies
both conditional postconditions with map removal.

`RawTable::resize` retains its original count/frame and source/destination placement
records (`dest` and `owner`). Its loop rebuilds the live map at destination slots.
`SwissTable::reserve` keeps the old `(hash,value)` associations and verifies each value
at the resized slot. The resize smoke checks `values[tracked_map[32]] == 320` after the
call. The vstd `Map::tracked_borrow_mut` operation is not used; `Tracked::borrow_mut()`
only accesses the wrapped tracked struct. No source/destination obligation was dropped.
An optional stronger assertion that this key's numeric slot changed (`new_slot !=
old_slot`) was not discharged: the attempt reports 153 verified, 1 error, with the
assertion failure and a resource-limit error. The required value-preservation slice
remains proved through `reserve`'s bidirectional key/value postconditions and the
final map-selected slot lookup; the probe does not claim a specific numeric slot delta.
The failed assertion source delta and full transcript are retained beside this report.

Full analysis-clone transcript: `verification results:: 154 verified, 0 errors`.
The clone includes branch probes and a single-key `reserve` value-remap smoke. It is
an analysis artifact, not production source.

## Newly found erase counter bug

The branch fixtures exposed that both the executable counters and recursive
specifications overwrote their count at every empty byte. They were measuring the last
empty position instead of the leading run of non-empty bytes. Since the implementation
and specification shared this mistake, the previous 149/0 proof did not expose it.
The pilot's `control_bytes.rs` now keeps the count fixed once the first empty is seen;
the specification recursion and step lemmas match. The corrected pilot crate verifies
at 149/0; its exact transcript is `production-crate-verification.log`.

## Scope and claim

The probe shows that this tracked representation is viable for the exercised
insert/erase/clear/resize slice. It does not establish the old extensionality contracts
or authorize replacing the production derived model. The vstd axiom cost is in
`tcb.md`. On 2026-10-08 the operator chose to keep the 2026-10-02 scope ruling, so
production retains the derived model and existing contracts. No runtime test or
C++/Rust oracle parity is claimed.
