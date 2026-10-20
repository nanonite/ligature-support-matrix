#!/usr/bin/env python3
"""Rust test generator and test map for the crypto-mixed differential oracle.

Run from the pilot root:  python3 oracle/generate_oracle_tests.py

For each case file below, reads it and its golden file, validates that their
case IDs agree (oracle-PROTOCOL.md section 6), and writes one `#[test]` per
case to its test file under oracle/rust-check/tests/. Each test calls
crypto_mixed_oracle_check::assert_case, which loads both fixtures at runtime,
recomputes the case through the Rust port, and compares the complete result
object. The C++ driver is never invoked from cargo nextest. The random case
file must carry its reproducibility manifest (protocol section 8).

It also writes oracle/test-map.csv from UPSTREAM_TESTS below: every Botan
3.13.0 test result in analysis/upstream/botan-3.13.0-make-check-success.log
that names ChaCha or Poly1305, mapped to the case IDs translated from it.
Random cases are not upstream tests and stay out of the map.
"""

import csv
import io
import json
import re
from pathlib import Path

ORACLE = Path(__file__).resolve().parent
TESTS = ORACLE / "rust-check" / "tests"
# (case file, golden file, generated test file, required case-ID prefix or None)
CASE_FILES = [
    ("cases.jsonl", "golden/results.jsonl", "generated_cases.rs", None),
    ("random-cases.jsonl", "golden/random-results.jsonl", "random_cases.rs", "random-"),
]
RANDOM_MANIFEST_FIELDS = {"case_file", "source", "seed", "generator", "command", "upstream_commit"}
TEST_MAP = ORACLE / "test-map.csv"

HEX, KEY, NONCE, INT, DIRECTION, HEX_LIST, INT_LIST = range(7)
OP_INPUTS = {
    "aead_encrypt": {"key": KEY, "nonce": NONCE, "ad": HEX, "plaintext": HEX},
    "aead_decrypt": {"key": KEY, "nonce": NONCE, "ad": HEX, "ciphertext": HEX},
    "aead_output_length": {"direction": DIRECTION, "input_length": INT},
    "chacha20_xor": {"key": KEY, "nonce": NONCE, "seek": INT, "input": HEX},
    "chacha20_remaining": {"key": KEY, "nonce": NONCE, "seek": INT, "writes": INT_LIST},
    "poly1305_mac": {"key": KEY, "message": HEX},
    "poly1305_mac_pieces": {"key": KEY, "pieces": HEX_LIST},
    "poly1305_mac_split": {"key": KEY, "message": HEX, "split": INT},
    "poly1305_update_unkeyed": {"message": HEX},
    "poly1305_update_after_final": {"key": KEY, "first": HEX, "second": HEX},
}
CASE_FIELDS = {"case_id", "op", "inputs", "oracle_scope", "exclusion_reason"}
HEX_RE = re.compile(r"(?:[0-9a-f]{2})*")
CASE_ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# (upstream test "<registered test>/<result name>", case-ID pattern or None).
# A bracketed suffix names the vectors of one upstream test that were not
# translated; oracle/operations.md gives each reason.
UPSTREAM_TESTS = [
    ("aead/ChaCha20Poly1305", r"upstream-test-aead-.*"),
    ("aead/ChaCha20Poly1305 [64-bit nonce vectors]", None),
    ("aead/ChaCha20Poly1305 [XChaCha20Poly1305 192-bit nonce vectors]", None),
    ("stream_ciphers/ChaCha(20)", r"upstream-test-chacha20-xor-\d{4}"),
    ("stream_ciphers/ChaCha(20) [64-bit nonce vectors]", None),
    ("stream_ciphers/ChaCha(20) [XChaCha20 192-bit nonce vectors]", None),
    ("stream_ciphers/ChaCha(8)", None),
    ("stream_ciphers/ChaCha(12)", None),
    ("mac_algos/Poly1305", r"upstream-test-poly1305-mac-.*"),
    ("stream_cipher_keystream_cap/StreamCipher::remaining_keystream_bytes",
     r"upstream-test-chacha20-remaining-(fresh-capacity|after-100-byte-write|after-near-end-seek)-\d{4}"),
    ("stream_cipher_keystream_cap/StreamCipher keystream exhaustion",
     r"upstream-test-chacha20-(remaining-consume-to-cap|remaining-write-past-cap|xor-oversize-encrypt)-\d{4}"),
    ("stream_cipher_seek/StreamCipher seek rejection past counter limits",
     r"upstream-test-chacha20-remaining-seek-at-counter-limit-\d{4}"),
    ("stream_cipher_seek/StreamCipher seek idempotence and round-trip at high offsets", None),
    ("ffi_chacha/FFI ChaCha20Poly1305", None),
    ("sodium/crypto_aead_chacha20poly1305", None),
    ("sodium/crypto_aead_chacha20poly1305_ietf", None),
    ("sodium/crypto_aead_xchacha20poly1305", None),
    ("sodium/crypto_box_curve25519xsalsa20poly1305", None),
    ("sodium/crypto_onetimeauth_poly1305", None),
    ("sodium/crypto_stream_chacha20", None),
    ("sodium/crypto_stream_xchacha20", None),
    ("sodium/secretbox_xsalsa20poly1305", None),
    ("unit_tls/TLS v1.2 ChaCha20Poly1305 ECDH", None),
    ("unit_tls/TLS v1.3 ChaCha20Poly1305 ECDH", None),
    ("chacha_rng/ChaCha_RNG", None),
    ("chacha_rng_unit/ChaCha_RNG Broken Entropy Input", None),
    ("chacha_rng_unit/ChaCha_RNG Nonce Check", None),
    ("chacha_rng_unit/ChaCha_RNG Prediction Resistance", None),
    ("chacha_rng_unit/ChaCha_RNG Randomize With Timestamp Input", None),
    ("chacha_rng_unit/ChaCha_RNG Reseed", None),
    ("chacha_rng_unit/ChaCha_RNG Reseed KAT", None),
    ("chacha_rng_unit/ChaCha_RNG Security Level", None),
    ("chacha_rng_unit/ChaCha_RNG randomize", None),
]
RUST_ONLY_TESTS = [
    ("rust-only: Poly1305::compute_tag_chunked split past the message end",
     "poly1305_split_past_message_end_is_invalid_split"),
]


def load_jsonl(path):
    text = path.read_text(encoding="utf-8")
    if "\r" in text:
        raise ValueError(f"{path} must use LF line endings")
    values = []
    for number, line in enumerate(text.split("\n")[:-1] if text.endswith("\n") else text.split("\n"), 1):
        if not line.strip():
            raise ValueError(f"blank line in {path}:{number}")
        values.append(json.loads(line))
    return values


def check_input(case_id, name, kind, value):
    def fail(message):
        raise ValueError(f"{case_id}: input {name} {message}")

    if kind in (HEX, KEY, NONCE):
        if not isinstance(value, str) or not HEX_RE.fullmatch(value):
            fail("must be lower-case hex")
        if kind == KEY and len(value) != 64:
            fail("must be 32 bytes")
        if kind == NONCE and len(value) != 24:
            fail("must be 12 bytes")
    elif kind == INT:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail("must be a non-negative integer")
    elif kind == DIRECTION:
        if value not in ("encrypt", "decrypt"):
            fail('must be "encrypt" or "decrypt"')
    elif kind == HEX_LIST:
        if not isinstance(value, list) or not all(isinstance(v, str) and HEX_RE.fullmatch(v) for v in value):
            fail("must be a list of lower-case hex strings")
    elif kind == INT_LIST:
        if not isinstance(value, list) or not all(
                isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 1 << 20 for v in value):
            fail("must be a list of integers in [0, 2^20]")


def validate_cases(cases):
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not CASE_ID_RE.fullmatch(case_id):
            raise ValueError(f"bad case_id {case_id!r}")
        unknown = set(case) - CASE_FIELDS
        if unknown:
            raise ValueError(f"{case_id}: unknown case fields {sorted(unknown)}")
        spec = OP_INPUTS.get(case.get("op"))
        if spec is None:
            raise ValueError(f"{case_id}: unknown op {case.get('op')!r}")
        inputs = case.get("inputs")
        if not isinstance(inputs, dict) or set(inputs) != set(spec):
            raise ValueError(f"{case_id}: inputs must be exactly {sorted(spec)}")
        for name, kind in spec.items():
            check_input(case_id, name, kind, inputs[name])
        scope = case.get("oracle_scope", "compare")
        if scope not in ("compare", "excluded"):
            raise ValueError(f"{case_id}: bad oracle_scope {scope!r}")
        if (scope == "excluded") != bool(case.get("exclusion_reason")):
            raise ValueError(f"{case_id}: exclusion_reason must be present exactly when excluded")


def rust_test_name(case_id):
    return case_id.replace("-", "_")


def build_test_map(case_ids):
    claimed = set()
    rows = []
    for upstream, pattern in UPSTREAM_TESTS:
        if pattern is None:
            rows.append((upstream, "", "", "unmapped"))
            continue
        matched = [case_id for case_id in case_ids if re.fullmatch(pattern, case_id)]
        if not matched:
            raise ValueError(f"no cases for mapped upstream test {upstream}")
        overlap = claimed.intersection(matched)
        if overlap:
            raise ValueError(f"{upstream} reuses cases {sorted(overlap)[:3]}")
        claimed.update(matched)
        rows.append((upstream, ";".join(matched), ";".join(map(rust_test_name, matched)), "mapped"))
    unclaimed = [c for c in case_ids if c.startswith("upstream-test-") and c not in claimed]
    if unclaimed:
        raise ValueError(f"upstream-test cases missing from the test map: {unclaimed[:5]}")
    for upstream, test_name in RUST_ONLY_TESTS:
        rows.append((upstream, "", test_name, "rust-only"))
    names = [row[0] for row in rows]
    if len(names) != len(set(names)):
        raise ValueError("duplicate upstream test names in the test map")
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["upstream_test_name", "case_ids", "nextest_test_name", "coverage_status"])
    writer.writerows(rows)
    return out.getvalue()


def check_random_manifest(case_file):
    path = ORACLE / f"{case_file}.manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    missing = RANDOM_MANIFEST_FIELDS - set(manifest)
    if missing:
        raise ValueError(f"{path.name} lacks {sorted(missing)}")
    if manifest["case_file"] != case_file or manifest["source"] != "random":
        raise ValueError(f"{path.name} does not describe {case_file} as a random case file")
    if f"--seed {manifest['seed']}" not in manifest["command"]:
        raise ValueError(f"{path.name}: command does not use the recorded seed")


def checked_case_ids(case_file, golden_file, prefix):
    cases = load_jsonl(ORACLE / case_file)
    golden = load_jsonl(ORACLE / golden_file)
    validate_cases(cases)
    case_ids = [case["case_id"] for case in cases]
    golden_ids = [result["case_id"] for result in golden]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"duplicate case_id in {case_file}")
    if len(golden_ids) != len(set(golden_ids)):
        raise ValueError(f"duplicate case_id in {golden_file}")
    if set(case_ids) != set(golden_ids):
        missing = sorted(set(case_ids) - set(golden_ids))
        extra = sorted(set(golden_ids) - set(case_ids))
        raise ValueError(f"{case_file} and {golden_file} differ (missing={missing[:5]}, extra={extra[:5]})")
    if golden_ids != sorted(golden_ids, key=str.encode):
        raise ValueError(f"{golden_file} is not in bytewise case_id order")
    for case_id in case_ids:
        if prefix is not None and not case_id.startswith(prefix):
            raise ValueError(f"{case_file}: {case_id} lacks the {prefix!r} prefix")
        if prefix is None and case_id.startswith("random-"):
            raise ValueError(f"{case_file}: random case {case_id} belongs in the random case file")
    return sorted(case_ids, key=str.encode)


def main():
    all_ids = set()
    main_ids = None
    for case_file, golden_file, test_file, prefix in CASE_FILES:
        if prefix == "random-":
            check_random_manifest(case_file)
        ordered = checked_case_ids(case_file, golden_file, prefix)
        if all_ids.intersection(ordered):
            raise ValueError(f"{case_file} reuses case IDs from another case file")
        all_ids.update(ordered)
        if prefix is None:
            main_ids = ordered
        tests = [
            f"// Generated by oracle/generate_oracle_tests.py from oracle/{case_file}; do not edit.\n"
            "use crypto_mixed_oracle_check::assert_case;\n"
        ]
        for case_id in ordered:
            tests.append(f"#[test]\nfn {rust_test_name(case_id)}() {{\n"
                         f"    assert_case(\"{case_file}\", \"{golden_file}\", \"{case_id}\");\n}}\n")
        TESTS.mkdir(parents=True, exist_ok=True)
        (TESTS / test_file).write_text("\n".join(tests), encoding="utf-8")
        print(f"generated {len(ordered)} tests in oracle/rust-check/tests/{test_file}")
    TEST_MAP.write_text(build_test_map(main_ids), encoding="utf-8")
    print(f"wrote {TEST_MAP.relative_to(ORACLE.parent)}")


if __name__ == "__main__":
    main()
