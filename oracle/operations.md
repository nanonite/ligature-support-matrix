# crypto-mixed oracle operation contract

The pilot operation contract referenced by `oracle-PROTOCOL.md`. The C++ side
is `driver.cpp` against Botan 3.13.0 (commit
`2a81eef56c96c237e590c27f9a75e60317c9c700`, minimized scalar build). The Rust
side is `rust-check/src/lib.rs` against `crates/crypto-mixed-core`. Both
sides implement exactly the operations below.

## Encodings

- Byte strings in `inputs` are lower-case hex JSON strings (`""` is empty).
- `key` is always 32 bytes and `nonce` always 12 bytes. Other sizes are out
  of the port's scope and are rejected by the driver as malformed input.
- Byte results are `{"type":"bytes","encoding":"hex","value":"<lower-case hex>"}`.
- Integer inputs and results are JSON integers. Every integer result is
  below 2^63.
- Results use only `ok` with a value, or `err` with an `err_kind` below.

## Error taxonomy

| `err_kind` | Botan 3.13.0 | Rust port |
|---|---|---|
| `authentication_failed` | `Invalid_Authentication_Tag` from AEAD decryption | `CryptoError::AuthenticationFailed` |
| `ciphertext_too_short` | `Invalid_Argument` from AEAD decryption or decryption `output_length` when the input is shorter than the 16-byte tag | `CryptoError::CiphertextTooShort` |
| `message_too_long` | `Invalid_State` "message length limit exceeded" | `CryptoError::MessageTooLong` |
| `keystream_exhausted` | `Invalid_State` from `ChaCha(20)` encryption or `write_keystream` past the 96-bit-nonce cap | `CryptoError::CounterExhausted` |
| `key_not_set` | `Invalid_State` from a Poly1305 `update` without key material | `CryptoError::KeyNotSet` |

`CryptoError::InvalidState` and `CryptoError::InvalidSplit` have no Botan
analog (`invalid_state`, `invalid_split`). No compared case can produce them,
and `invalid_split` is covered by a `rust-only` test. Any other Botan
exception aborts the driver with exit 3.

## Operations

| `op` | `inputs` | Botan call sequence | Rust call sequence |
|---|---|---|---|
| `aead_encrypt` | `key`, `nonce`, `ad`, `plaintext` | `AEAD_Mode` "ChaCha20Poly1305" encryption: `set_key`, `set_associated_data`, `start(nonce)`, `finish` | `ChaCha20Poly1305::encrypt` |
| `aead_decrypt` | `key`, `nonce`, `ad`, `ciphertext` (ciphertext and tag) | the same in the decryption direction | `ChaCha20Poly1305::decrypt` |
| `aead_output_length` | `direction` (`"encrypt"` or `"decrypt"`), `input_length` (at most 2^62) | `output_length(input_length)` on that direction's mode | `encryption_output_length` / `decryption_output_length` |
| `chacha20_xor` | `key`, `nonce`, `seek` (byte offset, below 2^38), `input` (at most 2^20 bytes) | `StreamCipher` "ChaCha(20)": `set_key`, `set_iv`, `seek`, `encrypt` in place | `ChaCha20::with_counter(seek / 64)`, discard `seek % 64` keystream bytes, `apply_keystream(input)` |
| `chacha20_remaining` | `key`, `nonce`, `seek`, `writes` (list of lengths, each at most 2^20) | as above, then `write_keystream` for each length, then `remaining_keystream_bytes()` | as above, then `apply_keystream` on that many zero bytes for each length, then `bytes_remaining()` |
| `poly1305_mac` | `key`, `message` | `MessageAuthenticationCode` "Poly1305": `set_key`, `update`, `final` | `Poly1305::compute_tag` (one-shot) |
| `poly1305_mac_pieces` | `key`, `pieces` (list of byte strings) | `set_key`, one `update` per piece, `final` | `Poly1305::new`, `set_key`, one `update` per piece, `finalize` |
| `poly1305_mac_split` | `key`, `message`, `split` (at most the message length) | `update(message[..split])`, `update(message[split..])`, `final` | `Poly1305::compute_tag_chunked` |
| `poly1305_update_unkeyed` | `message` | `update` on a fresh, unkeyed MAC | `Poly1305::new().update` |
| `poly1305_update_after_final` | `key`, `first`, `second` | `set_key`, `update(first)`, `final`, then `update(second)` | `set_key`, `update(first)`, `finalize`, then `update(second)` |

The two `poly1305_update_*` operations report the `update` call only: `ok`
with value `"accepted"` if it is accepted, or `err` `key_not_set`.

The port can start a stream only at a block counter, so byte-offset seeking
is composed on the Rust side as shown. That composition is part of this
contract, not a port API (PORT-GAPS: byte-offset seek).

## Case sources

`make_cases.py` writes `cases.jsonl` deterministically. The adjacent
`cases.jsonl.manifest.json` records the upstream commit, the vector-file
hashes, the vector file and line behind every `upstream-test` case, the
vectors that were not translated, and the retired case IDs.

- `upstream-test-aead-*` come from `src/tests/data/aead/chacha20poly1305.vec`,
  12-byte-nonce vectors only. Each vector gives an encrypt case, a decrypt
  case, three tampered-decrypt cases and two `output_length` cases. Botan's
  test mutates the ciphertext, nonce and AD with its RNG; the translation
  uses a fixed one-bit flip of the first byte (or one appended zero byte for
  empty AD).
- `upstream-test-chacha20-xor-NNNN` come from the `[ChaCha(20)]` section of
  `src/tests/data/stream/chacha.vec`, 12-byte-nonce and 32-byte-key vectors
  only. As in Botan, a missing `In` means an all-zero input of the output
  length.
- `upstream-test-poly1305-mac-*` come from `src/tests/data/mac/poly1305.vec`.
  This includes Botan's "split mac" check (first byte, middle, last byte) for
  messages longer than 2 bytes.
- `upstream-test-chacha20-remaining-*` and
  `upstream-test-chacha20-xor-oversize-encrypt-0001` translate the 96-bit-nonce
  checks of `src/tests/test_stream.cpp` (`StreamCipher::remaining_keystream_bytes`,
  `StreamCipher keystream exhaustion`, and the at-limit seek of
  `StreamCipher seek rejection past counter limits`).
- `boundary-*` cases are hand-written: padding and block edges, the keystream
  cap, the length guards and the Poly1305 key-state errors.
- `random-*` cases live in their own file, `random-cases.jsonl`, with
  `random-cases.jsonl.manifest.json` and `golden/random-results.jsonl`
  (#53). `generate_random_cases.py` draws every input from a seeded
  SplitMix64 stream. The `random-aead-decrypt-*` and
  `random-aead-decrypt-mutated-*` ciphertexts are the driver's output for
  `random-aead-encrypt-*`, used unchanged or randomly mutated (bit flip in
  the ciphertext, nonce or AD, or a resize). Random cases stay within the
  compared domain: no length query past RFC 8439's limit.

## Excluded cases

The three `boundary-aead-output-length-*-past-rfc-limit-*` cases are
excluded. Past RFC 8439's 2^38-64-byte message limit, Botan's `output_length`
checks only `size_t` overflow and rejects the message during processing. The
port's length guard rejects it at the query, and that guard is what the Kani
bridges BR-CRYPTO-MIXED-002 and BR-CRYPTO-MIXED-003 verify. The operator ruled
this an accepted divergence on 2026-10-20 (chainlink #48). The `rdb`
investigation is in `divergences/boundary-aead-output-length-encrypt-0003/`.
The case IDs that compared these inputs are retired.

## Not compared

These Botan test checks have no comparable operation, so a passing oracle run
is not evidence for them (oracle-PROTOCOL.md section 9):

- **Not ported:** 64-bit-nonce and XChaCha (192-bit-nonce) AEAD and ChaCha20,
  ChaCha(8)/ChaCha(12), 128-bit ChaCha keys, the C FFI, the libsodium
  compatibility API, TLS and ChaCha_RNG. `test-map.csv` lists each as
  `unmapped`.
- **The port's AEAD is one-shot:** incremental `update`/`process`, AD
  persistence across messages and `reset()`, AD set before the key,
  re-keying, and clone independence are not part of the port's API.
- **Plaintext zeroing after a failed tag check:** the port returns an error
  and never exposes unauthenticated plaintext, so there is no buffer to
  inspect.
- **Rejecting a seek past the counter limit:** the port's counter is a `u32`,
  so a seek past 2^38 cannot be expressed; only the at-limit acceptance is
  compared.
- **Unkeyed `remaining_keystream_bytes()`:** a port stream always has a key.
- **Leaving the buffer untouched after an oversize encrypt:** the port
  borrows its input immutably, so this holds by construction.
- **Provider and CPUID variants:** the driver links Botan's scalar providers
  only, matching the scalar port. Botan's SIMD providers are not compared.
