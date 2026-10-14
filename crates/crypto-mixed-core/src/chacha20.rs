use crate::CryptoError;

const BLOCK_BYTES: usize = 64;
const COUNTER_SPACE: u64 = 1u64 << 32;

/// The scalar IETF ChaCha20 stream cipher (20 rounds, 96-bit nonce).
pub struct ChaCha20 {
    key: [u8; 32],
    nonce: [u8; 12],
    next_counter: u64,
    block: [u8; BLOCK_BYTES],
    block_position: usize,
}

impl ChaCha20 {
    /// Start a stream at counter zero.
    pub fn new(key: [u8; 32], nonce: [u8; 12]) -> Self {
        Self::with_counter(key, nonce, 0)
    }

    /// Start a stream at the requested 32-bit block counter.
    pub fn with_counter(key: [u8; 32], nonce: [u8; 12], counter: u32) -> Self {
        Self {
            key,
            nonce,
            next_counter: u64::from(counter),
            block: [0; BLOCK_BYTES],
            block_position: BLOCK_BYTES,
        }
    }

    /// Return one RFC 8439 ChaCha20 block for the given inputs.
    pub fn block(&self, key: [u8; 32], nonce: [u8; 12], counter: u32) -> [u8; 64] {
        let _ = self;
        chacha20_block(&key, &nonce, counter)
    }

    /// Number of stream bytes available before the 32-bit counter is exhausted.
    pub fn bytes_remaining(&self) -> usize {
        let future_blocks = COUNTER_SPACE - self.next_counter;
        let buffered_bytes = if self.block_position < BLOCK_BYTES {
            (BLOCK_BYTES - self.block_position) as u64
        } else {
            0
        };
        let remaining = future_blocks * BLOCK_BYTES as u64 + buffered_bytes;
        if remaining > usize::MAX as u64 {
            usize::MAX
        } else {
            remaining as usize
        }
    }

    /// XOR the next stream bytes with `input`.
    ///
    /// An overlong request is rejected before stream state changes.
    pub fn apply_keystream(&mut self, input: &[u8]) -> Result<Vec<u8>, CryptoError> {
        if input.len() > self.bytes_remaining() {
            return Err(CryptoError::CounterExhausted);
        }

        let mut output = vec![0u8; input.len()];
        let mut consumed = 0;
        while consumed < input.len() {
            if self.block_position == BLOCK_BYTES {
                if self.next_counter >= COUNTER_SPACE {
                    return Err(CryptoError::CounterExhausted);
                }
                self.block = chacha20_block(&self.key, &self.nonce, self.next_counter as u32);
                self.next_counter += 1;
                self.block_position = 0;
            }

            let take = (BLOCK_BYTES - self.block_position).min(input.len() - consumed);
            for offset in 0..take {
                let index = consumed + offset;
                output[index] = input[index] ^ self.block[self.block_position + offset];
            }
            consumed += take;
            self.block_position += take;
        }
        Ok(output)
    }
}

fn load_u32_le(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([
        bytes[offset],
        bytes[offset + 1],
        bytes[offset + 2],
        bytes[offset + 3],
    ])
}

fn store_u32_le(value: u32, output: &mut [u8], offset: usize) {
    let bytes = value.to_le_bytes();
    output[offset..offset + 4].copy_from_slice(&bytes);
}

fn quarter_round(state: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    state[a] = state[a].wrapping_add(state[b]);
    state[d] = (state[d] ^ state[a]).rotate_left(16);
    state[c] = state[c].wrapping_add(state[d]);
    state[b] = (state[b] ^ state[c]).rotate_left(12);
    state[a] = state[a].wrapping_add(state[b]);
    state[d] = (state[d] ^ state[a]).rotate_left(8);
    state[c] = state[c].wrapping_add(state[d]);
    state[b] = (state[b] ^ state[c]).rotate_left(7);
}

fn chacha20_block(key: &[u8; 32], nonce: &[u8; 12], counter: u32) -> [u8; 64] {
    let mut initial = [0u32; 16];
    initial[0] = 0x6170_7865;
    initial[1] = 0x3320_646e;
    initial[2] = 0x7962_2d32;
    initial[3] = 0x6b20_6574;

    for word in 0..8 {
        initial[4 + word] = load_u32_le(key, word * 4);
    }
    initial[12] = counter;
    for word in 0..3 {
        initial[13 + word] = load_u32_le(nonce, word * 4);
    }

    let mut state = initial;
    for _ in 0..10 {
        quarter_round(&mut state, 0, 4, 8, 12);
        quarter_round(&mut state, 1, 5, 9, 13);
        quarter_round(&mut state, 2, 6, 10, 14);
        quarter_round(&mut state, 3, 7, 11, 15);
        quarter_round(&mut state, 0, 5, 10, 15);
        quarter_round(&mut state, 1, 6, 11, 12);
        quarter_round(&mut state, 2, 7, 8, 13);
        quarter_round(&mut state, 3, 4, 9, 14);
    }

    let mut output = [0u8; 64];
    for word in 0..16 {
        store_u32_le(
            state[word].wrapping_add(initial[word]),
            &mut output,
            word * 4,
        );
    }
    output
}
