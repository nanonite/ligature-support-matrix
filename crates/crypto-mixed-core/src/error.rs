/// Errors returned by the bounded scalar crypto API.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CryptoError {
    /// The stream would pass the final 32-bit ChaCha block counter.
    CounterExhausted,
    /// An operation needs a Poly1305 key that has not been set.
    KeyNotSet,
    /// The operation has no usable message state (for example, after finalize).
    InvalidState,
    /// A message exceeds the RFC 8439 length limit.
    MessageTooLong,
    /// The supplied ciphertext does not contain a complete tag.
    CiphertextTooShort,
    /// The supplied authentication tag is invalid.
    AuthenticationFailed,
    /// A requested chunk split is outside the message.
    InvalidSplit,
}
