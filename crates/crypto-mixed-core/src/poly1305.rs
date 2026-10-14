use crate::CryptoError;

const LIMB_MASK: u64 = (1 << 26) - 1;

/// Streaming scalar Poly1305 with a one-time 32-byte key.
pub struct Poly1305 {
    state: Option<Poly1305State>,
}

impl Default for Poly1305 {
    fn default() -> Self {
        Self::new()
    }
}

impl Poly1305 {
    pub fn new() -> Self {
        Self { state: None }
    }

    /// Initialize with exactly one 32-byte one-time key.
    pub fn set_key(&mut self, key: &[u8; 32]) -> Result<(), CryptoError> {
        self.state = Some(Poly1305State::new(key));
        Ok(())
    }

    /// Append message bytes to the current authentication state.
    pub fn update(&mut self, input: &[u8]) -> Result<(), CryptoError> {
        self.state
            .as_mut()
            .ok_or(CryptoError::KeyNotSet)?
            .update(input);
        Ok(())
    }

    /// Finalize and consume the one-time key state.
    pub fn finalize(&mut self) -> Result<[u8; 16], CryptoError> {
        self.state
            .take()
            .map(Poly1305State::finish)
            .ok_or(CryptoError::KeyNotSet)
    }

    /// Compute a one-shot Poly1305 tag.
    pub fn compute_tag(&self, key: &[u8; 32], message: &[u8]) -> [u8; 16] {
        let mut state = Poly1305State::new(key);
        state.update(message);
        state.finish()
    }

    /// Compute a tag by splitting the message at `split_at`.
    pub fn compute_tag_chunked(
        &self,
        key: &[u8; 32],
        message: &[u8],
        split_at: usize,
    ) -> Result<[u8; 16], CryptoError> {
        if split_at > message.len() {
            return Err(CryptoError::InvalidSplit);
        }
        let mut state = Poly1305State::new(key);
        state.update(&message[..split_at]);
        state.update(&message[split_at..]);
        Ok(state.finish())
    }

    pub(crate) fn compute_tag_segments(key: &[u8; 32], segments: &[&[u8]]) -> [u8; 16] {
        let mut state = Poly1305State::new(key);
        for segment in segments {
            state.update(segment);
        }
        state.finish()
    }
}

struct Poly1305State {
    r: [u64; 5],
    h: [u64; 5],
    pad: [u32; 4],
    buffer: [u8; 16],
    buffer_len: usize,
}

impl Poly1305State {
    fn new(key: &[u8; 32]) -> Self {
        let r = [
            (load_u32_le(key, 0) & 0x3ff_ffff) as u64,
            ((load_u32_le(key, 3) >> 2) & 0x3ff_ff03) as u64,
            ((load_u32_le(key, 6) >> 4) & 0x3ff_c0ff) as u64,
            ((load_u32_le(key, 9) >> 6) & 0x3f0_3fff) as u64,
            ((load_u32_le(key, 12) >> 8) & 0x00f_ffff) as u64,
        ];
        let pad = [
            load_u32_le(key, 16),
            load_u32_le(key, 20),
            load_u32_le(key, 24),
            load_u32_le(key, 28),
        ];
        Self {
            r,
            h: [0; 5],
            pad,
            buffer: [0; 16],
            buffer_len: 0,
        }
    }

    fn update(&mut self, mut input: &[u8]) {
        if self.buffer_len != 0 {
            let take = (16 - self.buffer_len).min(input.len());
            self.buffer[self.buffer_len..self.buffer_len + take].copy_from_slice(&input[..take]);
            self.buffer_len += take;
            input = &input[take..];
            if self.buffer_len == 16 {
                let block = self.buffer;
                self.process_block(&block, true);
                self.buffer_len = 0;
            } else {
                return;
            }
        }

        while input.len() >= 16 {
            let block: &[u8; 16] = input[..16].try_into().expect("sixteen-byte block");
            self.process_block(block, true);
            input = &input[16..];
        }

        if !input.is_empty() {
            self.buffer[..input.len()].copy_from_slice(input);
            self.buffer_len = input.len();
        }
    }

    fn process_block(&mut self, block: &[u8; 16], complete: bool) {
        let t0 = load_u32_le(block, 0) as u64;
        let t1 = load_u32_le(block, 4) as u64;
        let t2 = load_u32_le(block, 8) as u64;
        let t3 = load_u32_le(block, 12) as u64;

        self.h[0] += t0 & LIMB_MASK;
        self.h[1] += ((t0 >> 26) | (t1 << 6)) & LIMB_MASK;
        self.h[2] += ((t1 >> 20) | (t2 << 12)) & LIMB_MASK;
        self.h[3] += ((t2 >> 14) | (t3 << 18)) & LIMB_MASK;
        self.h[4] += (t3 >> 8) | if complete { 1 << 24 } else { 0 };

        let [r0, r1, r2, r3, r4] = self.r;
        let s1 = r1 * 5;
        let s2 = r2 * 5;
        let s3 = r3 * 5;
        let s4 = r4 * 5;

        let [h0, h1, h2, h3, h4] = self.h;
        let d0 = h0 * r0 + h1 * s4 + h2 * s3 + h3 * s2 + h4 * s1;
        let d1 = h0 * r1 + h1 * r0 + h2 * s4 + h3 * s3 + h4 * s2;
        let d2 = h0 * r2 + h1 * r1 + h2 * r0 + h3 * s4 + h4 * s3;
        let d3 = h0 * r3 + h1 * r2 + h2 * r1 + h3 * r0 + h4 * s4;
        let d4 = h0 * r4 + h1 * r3 + h2 * r2 + h3 * r1 + h4 * r0;

        let mut carry = d0 >> 26;
        self.h[0] = d0 & LIMB_MASK;
        let d1 = d1 + carry;
        carry = d1 >> 26;
        self.h[1] = d1 & LIMB_MASK;
        let d2 = d2 + carry;
        carry = d2 >> 26;
        self.h[2] = d2 & LIMB_MASK;
        let d3 = d3 + carry;
        carry = d3 >> 26;
        self.h[3] = d3 & LIMB_MASK;
        let d4 = d4 + carry;
        carry = d4 >> 26;
        self.h[4] = d4 & LIMB_MASK;

        self.h[0] += carry * 5;
        carry = self.h[0] >> 26;
        self.h[0] &= LIMB_MASK;
        self.h[1] += carry;
    }

    fn finish(mut self) -> [u8; 16] {
        if self.buffer_len != 0 {
            self.buffer[self.buffer_len] = 1;
            self.buffer[self.buffer_len + 1..].fill(0);
            let block = self.buffer;
            self.process_block(&block, false);
        }

        let mut h0 = self.h[0];
        let mut h1 = self.h[1];
        let mut h2 = self.h[2];
        let mut h3 = self.h[3];
        let mut h4 = self.h[4];
        let mut carry = h1 >> 26;
        h1 &= LIMB_MASK;
        h2 += carry;
        carry = h2 >> 26;
        h2 &= LIMB_MASK;
        h3 += carry;
        carry = h3 >> 26;
        h3 &= LIMB_MASK;
        h4 += carry;
        carry = h4 >> 26;
        h4 &= LIMB_MASK;
        h0 += carry * 5;
        carry = h0 >> 26;
        h0 &= LIMB_MASK;
        h1 += carry;

        let mut g0 = h0 + 5;
        carry = g0 >> 26;
        g0 &= LIMB_MASK;
        let mut g1 = h1 + carry;
        carry = g1 >> 26;
        g1 &= LIMB_MASK;
        let mut g2 = h2 + carry;
        carry = g2 >> 26;
        g2 &= LIMB_MASK;
        let mut g3 = h3 + carry;
        carry = g3 >> 26;
        g3 &= LIMB_MASK;
        let g4 = h4.wrapping_add(carry).wrapping_sub(1 << 26);

        let g_mask = (g4 >> 63).wrapping_sub(1);
        let h_mask = !g_mask;
        h0 = (h0 & h_mask) | (g0 & g_mask);
        h1 = (h1 & h_mask) | (g1 & g_mask);
        h2 = (h2 & h_mask) | (g2 & g_mask);
        h3 = (h3 & h_mask) | (g3 & g_mask);
        h4 = (h4 & h_mask) | (g4 & g_mask);

        let words = [
            (h0 | (h1 << 26)) as u32,
            ((h1 >> 6) | (h2 << 20)) as u32,
            ((h2 >> 12) | (h3 << 14)) as u32,
            ((h3 >> 18) | (h4 << 8)) as u32,
        ];

        let mut f0 = u64::from(words[0]) + u64::from(self.pad[0]);
        let mut f1 = u64::from(words[1]) + u64::from(self.pad[1]) + (f0 >> 32);
        let mut f2 = u64::from(words[2]) + u64::from(self.pad[2]) + (f1 >> 32);
        let f3 = u64::from(words[3]) + u64::from(self.pad[3]) + (f2 >> 32);
        f0 &= u64::from(u32::MAX);
        f1 &= u64::from(u32::MAX);
        f2 &= u64::from(u32::MAX);

        let mut tag = [0u8; 16];
        store_u32_le(f0 as u32, &mut tag, 0);
        store_u32_le(f1 as u32, &mut tag, 4);
        store_u32_le(f2 as u32, &mut tag, 8);
        store_u32_le(f3 as u32, &mut tag, 12);
        tag
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
