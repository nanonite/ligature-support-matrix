# Analysis-only reproduction for Chainlink #120

This is an isolated copy of the pilot crate with the tracked-map experiment and
proof-only branch/value-remap probes. It is not production source. The pilot's only
production change from this issue is the `WasNeverFull` counter/spec correction in
`rust/swisstable-verus-core/src/control_bytes.rs`; the exact source delta is in the
parent `was-never-full-fix.patch`.

The experiment adds `Tracked<LiveIndex>` and `Map<u64, usize>` to `RawTable`, integrates
map updates into insert/erase/clear/resize, and adds branch/value-remap proof helpers.
The command used was:

```sh
PATH=/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/7igjywfjlfa7v2sknkd9dbvpv2s5qf6g-z3-4.15.4/bin:/home/goya/.cargo/bin:$PATH \
CARGO_TARGET_DIR=/tmp/issue120-tracked-map/target-repro \
cargo verus verify --locked
```

The complete output is `../integration-transcript.log`. The corrected production crate
was verified from `rust/swisstable-verus-core/` with:

```sh
PATH=/nix/store/57l94534x07sysi7gjf4zkkpai6cw6vc-verus-tools/bin:/nix/store/7igjywfjlfa7v2sknkd9dbvpv2s5qf6g-z3-4.15.4/bin:/home/goya/.cargo/bin:$PATH \
CARGO_TARGET_DIR=/tmp/issue120-tracked-map/target-production \
cargo verus verify --locked
```

Its full output is `../production-crate-verification.log`.
