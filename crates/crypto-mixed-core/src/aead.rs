use crate::{ChaCha20, CryptoError, Poly1305};

const TAG_BYTES: usize = 16;
const MAX_MESSAGE_BYTES: u64 = (1u64 << 38) - 64;

/// RFC 8439 ChaCha20-Poly1305 using the scalar 96-bit-nonce construction.
pub struct ChaCha20Poly1305;

impl Default for ChaCha20Poly1305 {
    fn default() -> Self {
        Self::new()
    }
}

impl ChaCha20Poly1305 {
    pub fn new() -> Self {
        Self
    }

    pub fn encryption_output_length(&self, plaintext_length: usize) -> Result<usize, CryptoError> {
        if plaintext_length as u128 > MAX_MESSAGE_BYTES as u128 {
            return Err(CryptoError::MessageTooLong);
        }
        plaintext_length
            .checked_add(TAG_BYTES)
            .ok_or(CryptoError::MessageTooLong)
    }

    pub fn decryption_output_length(&self, ciphertext_length: usize) -> Result<usize, CryptoError> {
        if ciphertext_length < TAG_BYTES {
            return Err(CryptoError::CiphertextTooShort);
        }
        let message_length = ciphertext_length - TAG_BYTES;
        if message_length as u128 > MAX_MESSAGE_BYTES as u128 {
            return Err(CryptoError::MessageTooLong);
        }
        Ok(message_length)
    }

    pub fn encrypt(
        &mut self,
        key: &[u8; 32],
        nonce: &[u8; 12],
        aad: &[u8],
        plaintext: &[u8],
    ) -> Result<Vec<u8>, CryptoError> {
        let output_length = self.encryption_output_length(plaintext.len())?;
        let mut chacha = ChaCha20::with_counter(*key, *nonce, 1);
        if plaintext.len() > chacha.bytes_remaining() {
            return Err(CryptoError::CounterExhausted);
        }
        let ciphertext = chacha.apply_keystream(plaintext)?;
        let tag = self.tag(key, nonce, aad, &ciphertext);

        let mut output = Vec::with_capacity(output_length);
        output.extend_from_slice(&ciphertext);
        output.extend_from_slice(&tag);
        Ok(output)
    }

    pub fn decrypt(
        &mut self,
        key: &[u8; 32],
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext_and_tag: &[u8],
    ) -> Result<Vec<u8>, CryptoError> {
        let plaintext_length = self.decryption_output_length(ciphertext_and_tag.len())?;
        let (ciphertext, supplied_tag) = ciphertext_and_tag.split_at(plaintext_length);
        let expected_tag = self.tag(key, nonce, aad, ciphertext);
        if !tags_equal(&expected_tag, supplied_tag) {
            return Err(CryptoError::AuthenticationFailed);
        }

        let mut chacha = ChaCha20::with_counter(*key, *nonce, 1);
        chacha.apply_keystream(ciphertext)
    }

    pub fn verify(
        &self,
        key: &[u8; 32],
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext_and_tag: &[u8],
    ) -> bool {
        let Ok(plaintext_length) = self.decryption_output_length(ciphertext_and_tag.len()) else {
            return false;
        };
        let (ciphertext, supplied_tag) = ciphertext_and_tag.split_at(plaintext_length);
        let expected_tag = self.tag(key, nonce, aad, ciphertext);
        tags_equal(&expected_tag, supplied_tag)
    }

    fn tag(&self, key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], ciphertext: &[u8]) -> [u8; 16] {
        let poly_key = derive_poly1305_key(key, nonce);
        let zeroes = [0u8; 16];
        let aad_padding = (16 - (aad.len() % 16)) % 16;
        let ciphertext_padding = (16 - (ciphertext.len() % 16)) % 16;
        let mut lengths = [0u8; 16];
        lengths[..8].copy_from_slice(&(aad.len() as u64).to_le_bytes());
        lengths[8..].copy_from_slice(&(ciphertext.len() as u64).to_le_bytes());

        Poly1305::compute_tag_segments(
            &poly_key,
            &[
                aad,
                &zeroes[..aad_padding],
                ciphertext,
                &zeroes[..ciphertext_padding],
                &lengths,
            ],
        )
    }
}

pub(crate) fn derive_poly1305_key(key: &[u8; 32], nonce: &[u8; 12]) -> [u8; 32] {
    let chacha = ChaCha20::new(*key, *nonce);
    let first_block = chacha.block(*key, *nonce, 0);
    let mut poly_key = [0u8; 32];
    poly_key.copy_from_slice(&first_block[..32]);
    poly_key
}

fn tags_equal(expected: &[u8; 16], supplied: &[u8]) -> bool {
    if supplied.len() != TAG_BYTES {
        return false;
    }
    let mut difference = 0u8;
    for index in 0..TAG_BYTES {
        difference |= expected[index] ^ supplied[index];
    }
    difference == 0
}
