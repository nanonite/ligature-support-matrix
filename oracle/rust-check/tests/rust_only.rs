//! Rust-only checks: port behavior with no Botan analog, so no golden result
//! (oracle-PROTOCOL.md section 7, coverage_status `rust-only`).

use crypto_mixed_core::{CryptoError, Poly1305};

#[test]
fn poly1305_split_past_message_end_is_invalid_split() {
    let key = [7u8; 32];
    let message = [1u8; 33];
    assert_eq!(
        Poly1305::new().compute_tag_chunked(&key, &message, message.len() + 1),
        Err(CryptoError::InvalidSplit)
    );
}
