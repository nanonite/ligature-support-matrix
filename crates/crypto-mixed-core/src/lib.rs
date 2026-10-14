//! Scalar ChaCha20, Poly1305, and RFC 8439 ChaCha20-Poly1305.
//!
//! This crate implements the bounded P3 subset selected for Botan 3.13.0:
//! 256-bit keys, 96-bit nonces, 20-round ChaCha, and byte-slice AEAD inputs.
//! SIMD providers, XChaCha, legacy nonce modes, and constant-time claims are
//! outside this port's scope.

mod aead;
mod chacha20;
mod error;
mod poly1305;

#[cfg(kani)]
mod kani_proofs;

pub use aead::ChaCha20Poly1305;
pub use chacha20::ChaCha20;
pub use error::CryptoError;
pub use poly1305::Poly1305;
