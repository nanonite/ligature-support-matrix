//! Minimized reproducer for oracle case boundary-aead-output-length-encrypt-0003
//! (rdb-divergence-workflow.md section 3). Golden: status=ok, value=274877906897.

use crypto_mixed_core::ChaCha20Poly1305;

fn main() {
    // One byte past RFC 8439's 2^38 - 64 plaintext limit.
    let input_length: usize = 274_877_906_881;
    let result = ChaCha20Poly1305::new().encryption_output_length(input_length);
    println!(
        "case_id=boundary-aead-output-length-encrypt-0003 input_length={input_length} \
         expected=Ok(274877906897) result={result:?}"
    );
}
