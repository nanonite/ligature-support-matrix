//! HashMix -- the H1/H2 split of one user hash value.
//!
//! Reference: absl/container/internal/raw_hash_set.h L832 (`H1`) and L837
//! (`H2`).  Upstream `H1(hash)` is the identity and `H2(hash)` is the seven most
//! significant bits, used as the occupied control byte's tag.  The per-table seed
//! that upstream also mixes into H1 is out of this concept (see the concept
//! spec's `source_references`).
//!
//! `h2` is the reference's `hash >> 57`, not a substitute.  See
//! `verif/lemmas.rs::lemma_shr57` for the one bit-vector fact it needs
//! (`swisstable-verus-014`).

#[cfg(verus_only)]
use crate::lemmas::lemma_shr57;
use vstd::prelude::*;

verus! {

/// One 64-bit user hash split into the probe start (H1) and the seven-bit
/// control-byte tag (H2).
pub struct HashMix {
    /// The most recently supplied hash; the only thing either query observes.
    pub hash: u64,
    /// HashMix.C001: a query is only observed after `from_hash` supplied a hash.
    pub supplied: bool,
}

impl HashMix {
    pub fn new() -> (s: Self)
        ensures
            !s.supplied,
            s.hash == 0,
    {
        HashMix { hash: 0, supplied: false }
    }

    /// Supply the hash to split.  This is what discharges HashMix.C001 for every
    /// later query.
    pub fn from_hash(&mut self, hash: u64)
        ensures
            final(self).supplied,                  // HashMix.C001
            final(self).hash == hash,
    {
        self.hash = hash;
        self.supplied = true;
    }

    /// HashMix.C002 (`h1` is the supplied hash unchanged) and HashMix.C004
    /// (no query observes any field other than the supplied hash).
    pub fn h1(&self) -> (r: u64)
        requires
            self.supplied,                        // HashMix.C001
        ensures
            r == self.hash,                       // HashMix.C002 / C004
    {
        self.hash
    }

    /// HashMix.C003 (`h2` is the seven most significant bits) and HashMix.C004.
    ///
    /// `lemma_shr57` is a `#[verifier::bit_vector]` proof function supplying the
    /// one fact integer mode cannot derive: that the shift lands in `[0, 128)`, so
    /// the `u64 -> u8` truncation is lossless and C003 can be stated over `u64`.
    /// The reference's second `H2` fact -- that the shift agrees with dividing by
    /// `2^57` -- comes from the same lemma and is asserted here so the two forms
    /// are known equal rather than assumed equal.
    pub fn h2(&self) -> (r: u8)
        requires
            self.supplied,                        // HashMix.C001
        ensures
            r as u64 == self.hash >> 57,          // HashMix.C003
            r <= 0x7F,
    {
        proof { lemma_shr57(self.hash); }
        let t = self.hash >> 57;
        assert(t <= 0x7F);
        t as u8
    }
}

} // verus!
