# Divergence: AEAD length query past RFC 8439's message limit

Investigated with `rdb-divergence-workflow.md` on 2026-10-20 (chainlink #48).
**Classification:** semantic divergence, ruled acceptable by the operator.

## Trigger

```text
$ cd oracle/rust-check && cargo nextest run --profile ci --no-fail-fast    # exit 100
     Summary [   1.862s] 1370 tests run: 1367 passed, 3 failed, 0 skipped
assertion `left == right` failed: oracle mismatch for boundary-aead-output-length-encrypt-0003
  left: Object {"case_id": String("boundary-aead-output-length-encrypt-0003"), "err_kind": String("message_too_long"), "status": String("err")}
 right: Object {"case_id": String("boundary-aead-output-length-encrypt-0003"), "status": String("ok"), "value": Number(274877906897)}
```

| Case | Input | Golden (Botan) | Port |
|---|---|---|---|
| `boundary-aead-output-length-encrypt-0003` | encrypt, 274877906881 (2^38-63) | ok 274877906897 | err `message_too_long` |
| `boundary-aead-output-length-encrypt-0004` | encrypt, 2^62 | ok 4611686018427387920 | err `message_too_long` |
| `boundary-aead-output-length-decrypt-0009` | decrypt, 274877906897 | ok 274877906881 | err `message_too_long` |

`case.jsonl`, `golden.jsonl` and `nextest-no-fail-fast.log` preserve the
first case and the full run. The pilot root is `crypto-mixed/`.

## Minimized reproducer and rdb

`rust-check/src/bin/oracle_repro.rs` calls only
`ChaCha20Poly1305::encryption_output_length(274877906881)`. It is built as a
non-PIE binary, so the static symbol address is valid:

```text
$ RUSTFLAGS="-C link-arg=-no-pie" CARGO_TARGET_DIR=target/repro cargo build --bin oracle_repro
$ target/repro/debug/oracle_repro
case_id=boundary-aead-output-length-encrypt-0003 input_length=274877906881 expected=Ok(274877906897) result=Err(MessageTooLong)
$ nm -C target/repro/debug/oracle_repro | grep encryption_output_length
00000000002111f0 T crypto_mixed_core::aead::ChaCha20Poly1305::encryption_output_length
$ rdb target/repro/debug/oracle_repro < rdb-commands.txt
```

`rdb-version.txt` records `rdb 0.0.0` at `/home/goya/.cargo/bin/rdb`.
`rdb-transcript.txt` holds the full session; the relevant lines are:

```text
breakpoint set at 0x2111f0
rdx = 0x3fffffffc1
.../crypto-mixed-core/src/aead.rs:21
.../crypto-mixed-core/src/aead.rs:22
.../crypto-mixed-core/src/aead.rs:27
```

**First differing value.** The length arrives intact: `rdx = 0x3fffffffc1`,
which is 274877906881. The function returns its 16-byte `Result` through a
hidden pointer in `rdi`, so `rsi` holds `&self` and `rdx` holds the length,
not `rsi`/`rdx` as in the workflow's demo. At `aead.rs:21` the check
`plaintext_length > MAX_MESSAGE_BYTES` (`0x3fffffffc0`) is true, and
`aead.rs:22` returns `Err(MessageTooLong)`. Botan's
`ChaCha20Poly1305_Encryption::output_length` (`chacha20poly1305.cpp:107`)
only rejects `size_t` overflow, so it returns 274877906897. Botan enforces the
RFC 8439 limit later, when it processes the message (`chacha20poly1305.cpp:119`,
`Invalid_State` "message length limit exceeded").

## Classification

Neither a port defect nor an oracle defect. Both implementations reject
messages longer than 2^38-64 bytes, but they reject them at different calls:
the port at the length query, Botan when it processes the message. The port's
guard is deliberate. `encrypt` and `decrypt` call it before touching the
stream, and the Kani bridges BR-CRYPTO-MIXED-002 and BR-CRYPTO-MIXED-003 verify
that every length it accepts fits the counter-one keystream. Matching Botan
would mean moving that check, which reopens those obligations.

**Operator ruling (2026-10-20):** accepted as a semantic divergence. The three
case IDs are retired. Their inputs return as excluded cases
`boundary-aead-output-length-{encrypt,decrypt}-past-rfc-limit-00{10,11,12}`,
which cite this record. Within the limit the length queries are compared and
pass. Recorded as `crypto-rdb-001` in `findings/limitations.jsonl` (the rdb
workflow assigns rdb-located divergences to `tool: rdb`) and in `PORT-GAPS.md`.
