# crypto-mixed differential oracle (Stage 8B, chainlink #48)

This directory compares the Rust port in `crates/crypto-mixed-core` against
pinned Botan 3.13.0 (commit `2a81eef56c96c237e590c27f9a75e60317c9c700`),
following [`oracle-PROTOCOL.md`](oracle-PROTOCOL.md). The operations, error
taxonomy, case sources, exclusions, and what the oracle does not compare are
in [`operations.md`](operations.md).

| File | Role |
|---|---|
| `make_cases.py` | Writes `cases.jsonl` and `cases.jsonl.manifest.json` from Botan's vector files plus boundary cases |
| `build_upstream.sh`, `CMakeLists.txt`, `driver.cpp` | Minimized scalar Botan build and the C++ driver, built outside the pilot |
| `golden/results.jsonl` | Driver output for `cases.jsonl` (checked in; nextest never runs the driver) |
| `generate_oracle_tests.py` | Writes `rust-check/tests/generated_cases.rs` (one test per case) and `test-map.csv` |
| `rust-check/` | Test crate: `src/lib.rs` recomputes each case through the port; `tests/rust_only.rs` holds the `rust-only` test |
| `divergences/` | Evidence for each oracle mismatch, following the rdb workflow |

## Refresh

From the pilot root, inside `nix develop path:/home/goya/storage/full-ligature-port-workspace#crypto-mixed`:

```sh
oracle/build_upstream.sh                     # Botan subset + driver in /tmp/crypto-mixed-oracle-build
python3 oracle/make_cases.py
/tmp/crypto-mixed-oracle-build/driver/oracle_driver oracle/cases.jsonl oracle/golden/results.jsonl
python3 oracle/generate_oracle_tests.py
(cd oracle/rust-check && cargo nextest run --profile ci)
```

`build_upstream.sh` refuses to run if `upstream/botan` is not at the pinned
commit or has local changes, and checks again after the build. Botan
3.13.0 has no CMake build, so the library comes from its own `configure.py`
(`--minimized-build --enable-modules=chacha20poly1305,chacha,poly1305
--disable-shared-library --cc=clang`). That build loads only the scalar
providers: `aead base chacha chacha20poly1305 hex mac modes poly1305 rng
stream utils`. The flake shell's compiler is clang 21.1.7 with CMake 4.1.2,
cargo-nextest 0.9.133, and rustc 1.95.0.

## Result (2026-10-20)

```text
$ oracle_driver oracle/cases.jsonl oracle/golden/results.jsonl     # exit 0; a second run is byte-identical
$ cargo nextest run --profile ci
     Summary [   2.158s] 1370 tests run: 1370 passed, 0 skipped
$ grep -o 'tests="[0-9]*" failures="[0-9]*" errors="[0-9]*"' target/nextest/ci/junit.xml
tests="1370" failures="0" errors="0"
```

The JUnit file is `oracle/rust-check/target/nextest/ci/junit.xml`.

- **1,369 cases:** 1,303 `upstream-test` and 66 `boundary`.
  - 1,366 are compared; 3 are excluded by the #48 ruling.
  - One extra `rust-only` test brings the run to 1,370.
- **Not translated:** 1,606 Botan vectors fall outside the ported subset:
  - 1,569 XChaCha20Poly1305 and 1 64-bit-nonce AEAD vector;
  - 20 ChaCha(8) and 2 ChaCha(12) vectors;
  - 10 64-bit-nonce and 4 192-bit-nonce ChaCha(20) vectors.
- **Before the ruling:** the first full run passed 1,367 of 1,370 tests. The
  three failures were the `output_length` queries past RFC 8439's message
  limit (`divergences/boundary-aead-output-length-encrypt-0003/`).

`test-map.csv` covers every Botan test result in the pinned `make check` log
that names ChaCha or Poly1305: 6 `mapped`, 27 `unmapped`, 1 `rust-only`.

| Upstream test | Case IDs |
|---|---|
| `aead/ChaCha20Poly1305` | 980 (140 vectors x 7 checks) |
| `stream_ciphers/ChaCha(20)` | 73 |
| `mac_algos/Poly1305` | 243 (123 MACs + 120 split MACs) |
| `stream_cipher_keystream_cap/StreamCipher::remaining_keystream_bytes` | 3 |
| `stream_cipher_keystream_cap/StreamCipher keystream exhaustion` | 3 |
| `stream_cipher_seek/StreamCipher seek rejection past counter limits` | 1 |

A bracketed suffix such as `aead/ChaCha20Poly1305 [XChaCha20Poly1305 192-bit
nonce vectors]` marks the part of an upstream test that was not translated.
The test-map name is `<registered test>/<result name>`, as in the `make
check` log.

## Sensitivity check

Two hand-made mutants of a scratch copy of the port, run with
`cargo nextest run --profile ci --no-fail-fast`:

| Mutant | Summary |
|---|---|
| ChaCha quarter-round `rotate_left(7)` changed to `rotate_left(6)` | `1370 tests run: 1000 passed, 370 failed` |
| AEAD ciphertext padding `(16 - len % 16) % 16` changed to `16 - len % 16` | `1370 tests run: 1110 passed, 260 failed` (128 vectors x encrypt/decrypt, plus 4 boundary cases) |
