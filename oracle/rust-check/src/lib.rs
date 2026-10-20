//! Rust side of the crypto-mixed differential oracle (oracle-PROTOCOL.md section 6).
//!
//! Each generated test calls [`assert_case`] with its case file and golden file
//! (`cases.jsonl` with `golden/results.jsonl`, or `random-cases.jsonl` with
//! `golden/random-results.jsonl`). Both are loaded at runtime; the case is
//! recomputed through the `crypto-mixed-core` port and the complete result
//! object is compared with the Botan golden result. The operation contract is
//! `oracle/operations.md`.

use std::fs;
use std::path::{Path, PathBuf};

use crypto_mixed_core::{ChaCha20, ChaCha20Poly1305, CryptoError, Poly1305};
use serde_json::{json, Map, Value};

fn oracle_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join(name)
}

fn load_jsonl(path: &Path) -> Vec<Value> {
    fs::read_to_string(path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()))
        .lines()
        .map(|line| serde_json::from_str(line).expect("parse JSONL fixture line"))
        .collect()
}

fn find<'a>(values: &'a [Value], case_id: &str) -> &'a Value {
    values
        .iter()
        .find(|value| value.get("case_id").and_then(Value::as_str) == Some(case_id))
        .unwrap_or_else(|| panic!("no entry for {case_id}"))
}

/// Recompute one case from `case_file` and compare it with its result in `golden_file`.
pub fn assert_case(case_file: &str, golden_file: &str, case_id: &str) {
    let cases = load_jsonl(&oracle_path(case_file));
    let golden = load_jsonl(&oracle_path(golden_file));
    let case = find(&cases, case_id);
    let expected = find(&golden, case_id);
    if case.get("oracle_scope").and_then(Value::as_str) == Some("excluded") {
        let reason = case.get("exclusion_reason").and_then(Value::as_str);
        assert!(reason.is_some_and(|reason| !reason.is_empty()), "{case_id} lacks an exclusion reason");
        assert_eq!(*expected, json!({"case_id": case_id, "status": "ok", "value": null}));
        return;
    }
    assert_eq!(run_case(case), *expected, "oracle mismatch for {case_id}");
}

/// Recompute one comparable case and return its protocol result object.
pub fn run_case(case: &Value) -> Value {
    let case_id = case["case_id"].as_str().expect("case_id");
    let op = case["op"].as_str().expect("op");
    let inputs = case["inputs"].as_object().expect("inputs object");
    let outcome = match op {
        "aead_encrypt" => ChaCha20Poly1305::new()
            .encrypt(&key(inputs), &nonce(inputs), &bytes(inputs, "ad"), &bytes(inputs, "plaintext"))
            .map(bytes_value),
        "aead_decrypt" => ChaCha20Poly1305::new()
            .decrypt(&key(inputs), &nonce(inputs), &bytes(inputs, "ad"), &bytes(inputs, "ciphertext"))
            .map(bytes_value),
        "aead_output_length" => {
            let aead = ChaCha20Poly1305::new();
            let length = usize::try_from(integer(inputs, "input_length")).expect("input_length fits usize");
            match inputs["direction"].as_str() {
                Some("encrypt") => aead.encryption_output_length(length),
                Some("decrypt") => aead.decryption_output_length(length),
                other => panic!("bad direction {other:?}"),
            }
            .map(|length| json!(length))
        }
        "chacha20_xor" => seeked_stream(inputs)
            .and_then(|mut stream| stream.apply_keystream(&bytes(inputs, "input")))
            .map(bytes_value),
        "chacha20_remaining" => seeked_stream(inputs).and_then(|mut stream| {
            for write in inputs["writes"].as_array().expect("writes array") {
                let length = usize::try_from(write.as_u64().expect("write length")).expect("fits usize");
                stream.apply_keystream(&vec![0; length])?;
            }
            Ok(json!(stream.bytes_remaining()))
        }),
        "poly1305_mac" => Ok(bytes_value(
            Poly1305::new().compute_tag(&key(inputs), &bytes(inputs, "message")).to_vec(),
        )),
        "poly1305_mac_pieces" => {
            let mut mac = Poly1305::new();
            mac.set_key(&key(inputs)).and_then(|()| {
                for piece in inputs["pieces"].as_array().expect("pieces array") {
                    mac.update(&decode_hex(piece.as_str().expect("hex piece")))?;
                }
                mac.finalize().map(|tag| bytes_value(tag.to_vec()))
            })
        }
        "poly1305_mac_split" => {
            let split = usize::try_from(integer(inputs, "split")).expect("split fits usize");
            Poly1305::new()
                .compute_tag_chunked(&key(inputs), &bytes(inputs, "message"), split)
                .map(|tag| bytes_value(tag.to_vec()))
        }
        "poly1305_update_unkeyed" => Poly1305::new().update(&bytes(inputs, "message")).map(|()| json!("accepted")),
        "poly1305_update_after_final" => {
            let mut mac = Poly1305::new();
            mac.set_key(&key(inputs))
                .and_then(|()| mac.update(&bytes(inputs, "first")))
                .and_then(|()| mac.finalize())
                .and_then(|_| mac.update(&bytes(inputs, "second")))
                .map(|()| json!("accepted"))
        }
        _ => panic!("unknown op {op}"),
    };
    match outcome {
        Ok(value) => json!({"case_id": case_id, "status": "ok", "value": value}),
        Err(error) => json!({"case_id": case_id, "status": "err", "err_kind": err_kind(error)}),
    }
}

/// The stable err_kind for each port error (oracle/operations.md).
pub fn err_kind(error: CryptoError) -> &'static str {
    match error {
        CryptoError::CounterExhausted => "keystream_exhausted",
        CryptoError::KeyNotSet => "key_not_set",
        CryptoError::InvalidState => "invalid_state",
        CryptoError::MessageTooLong => "message_too_long",
        CryptoError::CiphertextTooShort => "ciphertext_too_short",
        CryptoError::AuthenticationFailed => "authentication_failed",
        CryptoError::InvalidSplit => "invalid_split",
    }
}

/// A ChaCha20 stream positioned at byte offset `seek`.
///
/// The port starts streams only at a block counter, so a byte offset is the
/// block `seek / 64` followed by discarding `seek % 64` keystream bytes.
fn seeked_stream(inputs: &Map<String, Value>) -> Result<ChaCha20, CryptoError> {
    let seek = integer(inputs, "seek");
    let counter = u32::try_from(seek / 64).expect("seek is below 2^38");
    let mut stream = ChaCha20::with_counter(key(inputs), nonce(inputs), counter);
    let discard = (seek % 64) as usize;
    if discard > 0 {
        stream.apply_keystream(&vec![0; discard])?;
    }
    Ok(stream)
}

fn integer(inputs: &Map<String, Value>, name: &str) -> u64 {
    inputs[name].as_u64().unwrap_or_else(|| panic!("{name} is not a non-negative integer"))
}

fn bytes(inputs: &Map<String, Value>, name: &str) -> Vec<u8> {
    decode_hex(inputs[name].as_str().unwrap_or_else(|| panic!("{name} is not a hex string")))
}

fn key(inputs: &Map<String, Value>) -> [u8; 32] {
    bytes(inputs, "key").try_into().expect("32-byte key")
}

fn nonce(inputs: &Map<String, Value>) -> [u8; 12] {
    bytes(inputs, "nonce").try_into().expect("12-byte nonce")
}

fn decode_hex(text: &str) -> Vec<u8> {
    assert!(text.len() % 2 == 0, "odd-length hex");
    (0..text.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&text[index..index + 2], 16).expect("hex digit"))
        .collect()
}

fn bytes_value(bytes: Vec<u8>) -> Value {
    let hex: String = bytes.iter().map(|byte| format!("{byte:02x}")).collect();
    json!({"type": "bytes", "encoding": "hex", "value": hex})
}
