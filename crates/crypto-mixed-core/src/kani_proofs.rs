use crate::aead::derive_poly1305_key;
use crate::{ChaCha20, ChaCha20Poly1305, CryptoError, Poly1305};

const fn hex_nibble(value: u8) -> u8 {
    match value {
        b'0'..=b'9' => value - b'0',
        b'a'..=b'f' => value - b'a' + 10,
        b'A'..=b'F' => value - b'A' + 10,
        _ => 0,
    }
}

const fn decode_hex<const N: usize>(encoded: &str) -> [u8; N] {
    let encoded = encoded.as_bytes();
    let mut decoded = [0; N];
    let mut index = 0;
    while index < N {
        decoded[index] = (hex_nibble(encoded[index * 2]) << 4) | hex_nibble(encoded[index * 2 + 1]);
        index += 1;
    }
    decoded
}

const CHACHA_VECTOR_KEY: [u8; 32] =
    decode_hex("000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F");
const CHACHA_VECTOR_NONCE: [u8; 12] = decode_hex("000102030405060708090A0B");
const CHACHA_VECTOR_STREAM: [u8; 64] = decode_hex(
    "103AF111C18B549D39248FB07D60C29A95D1DB88D892F7B4AF709A5FD47A9E4BD5FF9A658DD52C708BEF1F0F622B3747040FA3551300B1F293150A88620D5FED",
);

const POLY1305_VECTOR_KEY: [u8; 32] =
    decode_hex("DDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFC");
const POLY1305_VECTOR_INPUT: [u8; 73] = decode_hex(
    "797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1",
);
const POLY1305_VECTOR_TAG: [u8; 16] = decode_hex("DDB9DA7DDD5E52792730ED5CDA5F90A4");

const AEAD_VECTOR_KEY: [u8; 32] =
    decode_hex("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
const AEAD_VECTOR_NONCE: [u8; 12] = decode_hex("BBBBBBBBBBBBBBBBBBBBBBBB");
const AEAD_VECTOR_AAD: [u8; 16] = decode_hex("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC");
const AEAD_VECTOR_INPUT: [u8; 16] = decode_hex("DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD");
const AEAD_VECTOR_OUTPUT: [u8; 32] =
    decode_hex("A0C9391216A037370BDFF40626C5DD137E93A01836AF9B8A5C1F929EF18C9350");

#[kani::proof]
#[kani::unwind(66)]
fn kani_chacha20_apply_keystream_output_length() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let input = kani::vec::any_vec::<u8, 65>();
    let mut stream = ChaCha20::new(key, nonce);
    let output = stream.apply_keystream(&input).unwrap();
    assert_eq!(output.len(), input.len());
}

#[kani::proof]
#[kani::unwind(66)]
fn kani_chacha20_c002_exact_length_65_boundary() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let input: [u8; 65] = kani::any();
    let mut stream = ChaCha20::new(key, nonce);
    let output = stream.apply_keystream(&input).unwrap();
    assert_eq!(output.len(), input.len());
}

#[kani::proof]
#[kani::unwind(66)]
fn chacha20_apply_keystream_preserves_a_two_block_boundary_length() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let input: [u8; 65] = kani::any();
    let mut stream = ChaCha20::new(key, nonce);
    let output = stream.apply_keystream(&input).unwrap();
    assert_eq!(output.len(), input.len());
}

#[kani::proof]
fn chacha20_c003_rejects_counter_overrun_without_consuming_stream() {
    let mut stream = ChaCha20::with_counter([0; 32], [0; 12], u32::MAX);
    let before = stream.bytes_remaining();
    let input = [0u8; 65];
    assert_eq!(before, 64);
    assert_eq!(
        stream.apply_keystream(&input),
        Err(CryptoError::CounterExhausted)
    );
    assert_eq!(stream.bytes_remaining(), before);
}

#[kani::proof]
#[kani::unwind(66)]
fn kani_chacha20_apply_keystream_capacity() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let input = kani::vec::any_vec::<u8, 65>();
    let counter: u32 = kani::any();
    let mut stream = ChaCha20::with_counter(key, nonce, counter);
    let before = stream.bytes_remaining();

    if input.len() > before {
        assert_eq!(
            stream.apply_keystream(&input),
            Err(CryptoError::CounterExhausted)
        );
        assert_eq!(stream.bytes_remaining(), before);
    } else {
        let output = stream.apply_keystream(&input).unwrap();
        assert_eq!(output.len(), input.len());
    }
}

#[kani::proof]
fn kani_chacha20_c003_aead_counter_one_stream_capacity() {
    let requested_length: usize = kani::any();
    let aead = ChaCha20Poly1305::new();
    let stream = ChaCha20::with_counter([0; 32], [0; 12], 1);

    if aead.encryption_output_length(requested_length).is_ok() {
        assert!(requested_length <= stream.bytes_remaining());
    }
}

#[kani::proof]
#[kani::unwind(66)]
fn chacha20_capacity_is_enforced_at_the_counter_boundary_for_65_bytes() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let input: [u8; 65] = kani::any();
    let counter: u32 = kani::any();
    let mut stream = ChaCha20::with_counter(key, nonce, counter);
    let before = stream.bytes_remaining();

    if input.len() > before {
        assert_eq!(
            stream.apply_keystream(&input),
            Err(CryptoError::CounterExhausted)
        );
        assert_eq!(stream.bytes_remaining(), before);
    } else {
        let output = stream.apply_keystream(&input).unwrap();
        assert_eq!(output.len(), input.len());
    }
}

#[kani::proof]
#[kani::unwind(128)]
fn chacha20_matches_the_pinned_botan_twenty_round_vector() {
    let mut stream = ChaCha20::new(CHACHA_VECTOR_KEY, CHACHA_VECTOR_NONCE);
    let output = stream.apply_keystream(&[0; 64]).unwrap();
    assert_eq!(output.as_slice(), &CHACHA_VECTOR_STREAM);
}

#[kani::proof]
#[kani::unwind(32)]
fn kani_poly1305_finalize_tag_length() {
    let key: [u8; 32] = kani::any();
    let message = kani::vec::any_vec::<u8, 65>();
    let poly = Poly1305::new();
    let tag = poly.compute_tag(&key, &message);
    assert_eq!(tag.len(), 16);
}

#[kani::proof]
// Kani 0.67.0 did not discharge this symbolic split proof within 180 seconds.
#[kani::unwind(16)]
fn poly1305_chunked_update_matches_one_shot_for_bounded_messages() {
    let key: [u8; 32] = kani::any();
    let message: [u8; 8] = kani::any();
    let split_at: usize = kani::any();
    kani::assume(split_at <= message.len());

    let poly = Poly1305::new();
    let one_shot = poly.compute_tag(&key, &message);
    let chunked = poly.compute_tag_chunked(&key, &message, split_at).unwrap();
    assert_eq!(one_shot, chunked);
}

#[kani::proof]
#[kani::unwind(128)]
fn poly1305_chunked_update_matches_one_shot_at_block_boundaries() {
    let poly = Poly1305::new();
    let expected = POLY1305_VECTOR_TAG;
    assert_eq!(
        poly.compute_tag(&POLY1305_VECTOR_KEY, &POLY1305_VECTOR_INPUT),
        expected
    );
    for split_at in [15, 16, 17, 32, 64, 73] {
        assert_eq!(
            poly.compute_tag_chunked(&POLY1305_VECTOR_KEY, &POLY1305_VECTOR_INPUT, split_at)
                .unwrap(),
            expected
        );
    }
}

#[kani::proof]
#[kani::unwind(128)]
fn poly1305_matches_the_pinned_botan_self_test_vector() {
    let poly = Poly1305::new();
    let tag = poly.compute_tag(&POLY1305_VECTOR_KEY, &POLY1305_VECTOR_INPUT);
    assert_eq!(tag, POLY1305_VECTOR_TAG);
}

#[kani::proof]
fn bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let poly_key = derive_poly1305_key(&key, &nonce);
    assert_eq!(poly_key.len(), 32);

    let mut poly = Poly1305::new();
    assert!(poly.set_key(&poly_key).is_ok());
}

#[kani::proof]
fn bridge_002_limits_aead_plaintext_to_the_counter_one_stream() {
    let requested_length: usize = kani::any();
    let aead = ChaCha20Poly1305::new();
    let stream = ChaCha20::with_counter([0; 32], [0; 12], 1);

    if aead.encryption_output_length(requested_length).is_ok() {
        assert!(requested_length <= stream.bytes_remaining());
    }
}

#[kani::proof]
fn bridge_003_limits_aead_ciphertext_to_the_counter_one_stream() {
    let ciphertext_and_tag_length: usize = kani::any();
    let aead = ChaCha20Poly1305::new();
    let stream = ChaCha20::with_counter([0; 32], [0; 12], 1);

    if let Ok(message_length) = aead.decryption_output_length(ciphertext_and_tag_length) {
        assert!(message_length <= stream.bytes_remaining());
    }
}

#[kani::proof]
#[kani::unwind(64)]
// Kani 0.67.0 did not finish this symbolic one-byte round trip within 180 seconds.
fn aead_round_trip_holds_for_one_symbolic_byte() {
    let key: [u8; 32] = kani::any();
    let nonce: [u8; 12] = kani::any();
    let aad: [u8; 1] = kani::any();
    let plaintext: [u8; 1] = kani::any();
    let mut aead = ChaCha20Poly1305::new();

    let ciphertext_and_tag = aead.encrypt(&key, &nonce, &aad, &plaintext).unwrap();
    assert_eq!(ciphertext_and_tag.len(), plaintext.len() + 16);
    assert!(aead.verify(&key, &nonce, &aad, &ciphertext_and_tag));
    let recovered = aead
        .decrypt(&key, &nonce, &aad, &ciphertext_and_tag)
        .unwrap();
    assert_eq!(recovered, plaintext);
}

#[kani::proof]
#[kani::unwind(64)]
fn aead_verify_and_decrypt_accept_the_pinned_botan_vector() {
    let mut aead = ChaCha20Poly1305::new();
    assert!(aead.verify(
        &AEAD_VECTOR_KEY,
        &AEAD_VECTOR_NONCE,
        &AEAD_VECTOR_AAD,
        &AEAD_VECTOR_OUTPUT
    ));
    let recovered = aead
        .decrypt(
            &AEAD_VECTOR_KEY,
            &AEAD_VECTOR_NONCE,
            &AEAD_VECTOR_AAD,
            &AEAD_VECTOR_OUTPUT,
        )
        .unwrap();
    assert_eq!(recovered.as_slice(), &AEAD_VECTOR_INPUT);
}

#[kani::proof]
#[kani::unwind(64)]
fn aead_rejects_a_modified_tag_without_returning_plaintext() {
    let mut aead = ChaCha20Poly1305::new();
    let mut ciphertext_and_tag = AEAD_VECTOR_OUTPUT;
    let last = ciphertext_and_tag.len() - 1;
    ciphertext_and_tag[last] ^= 1;
    assert!(!aead.verify(
        &AEAD_VECTOR_KEY,
        &AEAD_VECTOR_NONCE,
        &AEAD_VECTOR_AAD,
        &ciphertext_and_tag
    ));
    assert_eq!(
        aead.decrypt(
            &AEAD_VECTOR_KEY,
            &AEAD_VECTOR_NONCE,
            &AEAD_VECTOR_AAD,
            &ciphertext_and_tag
        ),
        Err(CryptoError::AuthenticationFailed)
    );
}

#[kani::proof]
#[kani::unwind(64)]
fn aead_matches_the_pinned_botan_vector() {
    let mut aead = ChaCha20Poly1305::new();
    let output = aead
        .encrypt(
            &AEAD_VECTOR_KEY,
            &AEAD_VECTOR_NONCE,
            &AEAD_VECTOR_AAD,
            &AEAD_VECTOR_INPUT,
        )
        .unwrap();
    assert_eq!(output.as_slice(), &AEAD_VECTOR_OUTPUT);
}

#[kani::proof]
fn kani_chacha20_c004_with_counter_stream_capacity() {
    let counter: u32 = kani::any();
    let stream = ChaCha20::with_counter([0; 32], [0; 12], counter);
    let expected = ((1u64 << 32) - u64::from(counter)) * 64;
    assert_eq!(stream.bytes_remaining() as u64, expected);
}

#[kani::proof]
#[kani::unwind(66)]
fn kani_chacha20_c005_bytes_remaining_tracks_consumption() {
    let input = [0u8; 65];
    let cases: [(u32, usize); 8] = [
        (0, 1),
        (0, 63),
        (0, 64),
        (0, 65),
        (1, 65),
        (u32::MAX - 1, 65),
        (u32::MAX, 64),
        (u32::MAX, 65),
    ];
    for (counter, length) in cases {
        let mut stream = ChaCha20::with_counter([0; 32], [0; 12], counter);
        let before = stream.bytes_remaining();
        if stream.apply_keystream(&input[..length]).is_ok() {
            assert_eq!(stream.bytes_remaining(), before - length);
        } else {
            assert!(length > before);
            assert_eq!(stream.bytes_remaining(), before);
        }
    }

    // Buffered bytes: 63 then 2 crosses a block boundary inside one stream.
    let mut stream = ChaCha20::with_counter([0; 32], [0; 12], 0);
    let start = stream.bytes_remaining();
    stream.apply_keystream(&input[..63]).unwrap();
    stream.apply_keystream(&input[..2]).unwrap();
    assert_eq!(stream.bytes_remaining(), start - 65);
}

#[kani::proof]
#[kani::unwind(128)]
fn kani_poly1305_c005_segments_match_concatenation() {
    let message = &POLY1305_VECTOR_INPUT;
    let splits: [(usize, usize); 7] = [
        (0, 0),
        (0, 73),
        (15, 16),
        (16, 32),
        (17, 64),
        (31, 72),
        (73, 73),
    ];
    for (first, second) in splits {
        let segmented = Poly1305::compute_tag_segments(
            &POLY1305_VECTOR_KEY,
            &[
                &message[..first],
                &message[first..second],
                &message[second..],
            ],
        );
        assert_eq!(segmented, POLY1305_VECTOR_TAG);
    }
}
