#!/usr/bin/env python3
"""Remove the unused bridge_003 Kani harness from crypto-mixed's kani_proofs.rs.

Refuses unless the exact harness text occurs exactly once; touches nothing else.
Usage: remove_bridge003.py [path-to-kani_proofs.rs]
"""
import pathlib
import sys

DEFAULT = "/home/goya/storage/full-ligature-port-workspace/crypto-mixed/crates/crypto-mixed-core/src/kani_proofs.rs"
path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
block = """#[kani::proof]
fn bridge_003_limits_aead_ciphertext_to_the_counter_one_stream() {
    let ciphertext_and_tag_length: usize = kani::any();
    let aead = ChaCha20Poly1305::new();
    let stream = ChaCha20::with_counter([0; 32], [0; 12], 1);

    if let Ok(message_length) = aead.decryption_output_length(ciphertext_and_tag_length) {
        assert!(message_length <= stream.bytes_remaining());
    }
}

"""
text = path.read_text()
count = text.count(block)
if count != 1:
    raise SystemExit(f"refused: bridge_003 harness found {count} times, expected exactly 1")
path.write_text(text.replace(block, ""))
print("removed bridge_003 harness from", path)
