#!/usr/bin/env python3
"""Write oracle/cases.jsonl and its provenance manifest for the crypto-mixed oracle.

Run from the pilot root:  python3 oracle/make_cases.py

Two of the protocol's three case sources (oracle-PROTOCOL.md section 8):

* upstream-test: Botan 3.13.0's own test vectors and checks, translated one
  vector at a time for the ported subset (32-byte key, 12-byte nonce,
  20-round ChaCha). Vectors are read the way Botan's Text_Based_Test reads
  them: key/value lines accumulate until the output key ("Out"), then the
  record is complete and cleared.
* boundary: hand-written edge cases (padding and block edges, keystream cap,
  length guards, key-state errors).

Seeded random cases are chainlink #53. The output is deterministic; the
manifest records the upstream commit, the vector-file hashes and, for every
upstream-test case, the vector file and line it came from.
"""

import hashlib
import json
from pathlib import Path

ORACLE = Path(__file__).resolve().parent
PILOT = ORACLE.parent
BOTAN = PILOT / "upstream" / "botan"
UPSTREAM_COMMIT = "2a81eef56c96c237e590c27f9a75e60317c9c700"
VECTOR_FILES = {
    "aead": "src/tests/data/aead/chacha20poly1305.vec",
    "stream": "src/tests/data/stream/chacha.vec",
    "mac": "src/tests/data/mac/poly1305.vec",
}
CAP = 1 << 38  # ChaCha20 96-bit-nonce keystream: 2^32 blocks of 64 bytes
RFC_MAX_MESSAGE = CAP - 64
PAST_RFC_LIMIT_REASON = (
    "RFC 8439 limits a message to 2^38-64 bytes, so the length query past that limit is "
    "implementation-defined: Botan's output_length checks only size_t overflow and rejects the "
    "message when processing it, while the port's length guard rejects it at the query. "
    "Ruled an accepted divergence by the operator on 2026-10-20 (chainlink #48; "
    "oracle/divergences/boundary-aead-output-length-encrypt-0003)."
)
# Case IDs are never reused (oracle-PROTOCOL.md section 2.1).
RETIRED_CASE_IDS = {
    case_id: "compared past RFC 8439's message limit; re-added as an excluded case after the #48 ruling"
    for case_id in (
        "boundary-aead-output-length-encrypt-0003",
        "boundary-aead-output-length-encrypt-0004",
        "boundary-aead-output-length-decrypt-0009",
    )
}

cases = []
sources = {}
not_translated = {}


def add(case_id, op, inputs, source=None, exclusion_reason=None):
    assert case_id not in RETIRED_CASE_IDS, case_id
    case = {"case_id": case_id, "op": op, "inputs": inputs}
    if exclusion_reason is not None:
        case["oracle_scope"] = "excluded"
        case["exclusion_reason"] = exclusion_reason
    cases.append(case)
    if source is not None:
        sources[case_id] = source


def skip(reason):
    not_translated[reason] = not_translated.get(reason, 0) + 1


def read_vectors(name):
    """Return [(section, fields, line_number_of_Out)] in file order."""
    path = BOTAN / VECTOR_FILES[name]
    vectors = []
    section = None
    fields = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            fields = {}
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        fields[key] = value.lower()
        if key == "Out":
            vectors.append((section, fields, number))
            fields = {}
    return vectors


def hexlen(value):
    return len(value) // 2


def flip_first_byte(value):
    return f"{int(value[:2], 16) ^ 0x01:02x}{value[2:]}"


def pattern(length, start=0):
    return "".join(f"{(start + i) & 0xFF:02x}" for i in range(length))


# --- upstream-test: aead / ChaCha20Poly1305 ---------------------------------

aead_index = 0
for section, v, line in read_vectors("aead"):
    assert section == "ChaCha20Poly1305", section
    nonce_bytes = hexlen(v["Nonce"])
    if nonce_bytes == 8:
        skip("aead/ChaCha20Poly1305: 64-bit nonce (draft-agl) vector")
        continue
    if nonce_bytes == 24:
        skip("aead/ChaCha20Poly1305: XChaCha20Poly1305 192-bit nonce vector")
        continue
    assert nonce_bytes == 12 and hexlen(v["Key"]) == 32, (line, v)
    aead_index += 1
    n = f"{aead_index:04d}"
    src = f"{VECTOR_FILES['aead']}:{line}"
    key, nonce, ad = v["Key"], v["Nonce"], v.get("AD", "")
    plaintext, ciphertext = v["In"], v["Out"]
    add(f"upstream-test-aead-encrypt-{n}", "aead_encrypt",
        {"key": key, "nonce": nonce, "ad": ad, "plaintext": plaintext}, src)
    add(f"upstream-test-aead-decrypt-{n}", "aead_decrypt",
        {"key": key, "nonce": nonce, "ad": ad, "ciphertext": ciphertext}, src)
    # Botan mutates the ciphertext, nonce and AD with its test RNG; these use
    # a fixed one-bit flip (or, for empty AD, one appended zero byte).
    add(f"upstream-test-aead-decrypt-modified-ciphertext-{n}", "aead_decrypt",
        {"key": key, "nonce": nonce, "ad": ad, "ciphertext": flip_first_byte(ciphertext)}, src)
    add(f"upstream-test-aead-decrypt-modified-nonce-{n}", "aead_decrypt",
        {"key": key, "nonce": flip_first_byte(nonce), "ad": ad, "ciphertext": ciphertext}, src)
    add(f"upstream-test-aead-decrypt-modified-ad-{n}", "aead_decrypt",
        {"key": key, "nonce": nonce, "ad": flip_first_byte(ad) if ad else "00",
         "ciphertext": ciphertext}, src)
    add(f"upstream-test-aead-output-length-encrypt-{n}", "aead_output_length",
        {"direction": "encrypt", "input_length": hexlen(plaintext)}, src)
    add(f"upstream-test-aead-output-length-decrypt-{n}", "aead_output_length",
        {"direction": "decrypt", "input_length": hexlen(ciphertext)}, src)

# --- upstream-test: stream_ciphers / ChaCha(20) -----------------------------

stream_index = 0
for section, v, line in read_vectors("stream"):
    if section != "ChaCha(20)":
        skip(f"stream_ciphers/{section}: reduced-round ChaCha vector")
        continue
    nonce_bytes = hexlen(v.get("Nonce", ""))
    if nonce_bytes != 12:
        skip(f"stream_ciphers/ChaCha(20): {nonce_bytes * 8}-bit nonce vector")
        continue
    if hexlen(v["Key"]) != 32:
        skip("stream_ciphers/ChaCha(20): 128-bit key vector")
        continue
    stream_index += 1
    # Botan encrypts an all-zero buffer of the output length when In is absent.
    data = v.get("In") or "00" * hexlen(v["Out"])
    add(f"upstream-test-chacha20-xor-{stream_index:04d}", "chacha20_xor",
        {"key": v["Key"], "nonce": v["Nonce"], "seek": int(v.get("Seek", "0")), "input": data},
        f"{VECTOR_FILES['stream']}:{line}")

# --- upstream-test: mac_algos / Poly1305 ------------------------------------

mac_index = 0
for section, v, line in read_vectors("mac"):
    assert section == "Poly1305" and hexlen(v["Key"]) == 32, (line, v)
    mac_index += 1
    n = f"{mac_index:04d}"
    src = f"{VECTOR_FILES['mac']}:{line}"
    add(f"upstream-test-poly1305-mac-{n}", "poly1305_mac",
        {"key": v["Key"], "message": v["In"]}, src)
    message = v["In"]
    if hexlen(message) > 2:
        # Botan's "split mac": update(first byte), update(middle), update(last byte).
        add(f"upstream-test-poly1305-mac-pieces-split-{n}", "poly1305_mac_pieces",
            {"key": v["Key"], "pieces": [message[:2], message[2:-2], message[-2:]]}, src)

# --- upstream-test: stream_cipher_keystream_cap / stream_cipher_seek --------
# 96-bit-nonce ChaCha(20) checks from src/tests/test_stream.cpp.

zero_key, zero_nonce, ff_nonce = "00" * 32, "00" * 12, "ff" * 12
cap_src = "src/tests/test_stream.cpp"
for case_id, nonce, seek, writes in [
    ("upstream-test-chacha20-remaining-fresh-capacity-0001", zero_nonce, 0, []),
    ("upstream-test-chacha20-remaining-after-100-byte-write-0001", zero_nonce, 0, [100]),
    ("upstream-test-chacha20-remaining-after-near-end-seek-0001", zero_nonce, CAP - 64, []),
    ("upstream-test-chacha20-remaining-consume-to-cap-0001", ff_nonce, CAP - 200, [200]),
    ("upstream-test-chacha20-remaining-write-past-cap-0001", ff_nonce, CAP - 200, [200, 1]),
    ("upstream-test-chacha20-remaining-seek-at-counter-limit-0001", zero_nonce, CAP - 1, []),
]:
    add(case_id, "chacha20_remaining",
        {"key": zero_key, "nonce": nonce, "seek": seek, "writes": writes}, cap_src)
add("upstream-test-chacha20-xor-oversize-encrypt-0001", "chacha20_xor",
    {"key": zero_key, "nonce": ff_nonce, "seek": CAP - 100, "input": "00" * 200}, cap_src)

# --- boundary ---------------------------------------------------------------

rfc_key = pattern(32, 0x80)
rfc_nonce = "070000004041424344454647"
for number, (ad_len, pt_len) in enumerate(
        [(0, 0), (0, 1), (1, 0), (15, 15), (16, 16), (17, 17), (0, 63), (0, 64), (0, 65), (31, 129)], 1):
    add(f"boundary-aead-encrypt-ad{ad_len}-pt{pt_len}-{number:04d}", "aead_encrypt",
        {"key": rfc_key, "nonce": rfc_nonce, "ad": pattern(ad_len, 0xA0),
         "plaintext": pattern(pt_len)})

reference = next(c for c in cases if c["case_id"] == "upstream-test-aead-decrypt-0001")["inputs"]
for number, (label, ciphertext) in enumerate([
        ("empty", ""),
        ("fifteen-bytes", "00" * 15),
        ("zero-tag-only", "00" * 16),
        ("truncated-tag", reference["ciphertext"][:-2]),
        ("flipped-last-tag-byte", reference["ciphertext"][:-2]
         + f"{int(reference['ciphertext'][-2:], 16) ^ 0x80:02x}"),
        ("appended-byte", reference["ciphertext"] + "00"),
], 1):
    add(f"boundary-aead-decrypt-{label}-{number:04d}", "aead_decrypt",
        {"key": reference["key"], "nonce": reference["nonce"], "ad": reference["ad"],
         "ciphertext": ciphertext})

for number, direction, length in [
        (1, "encrypt", 0), (2, "encrypt", RFC_MAX_MESSAGE), (5, "decrypt", 0), (6, "decrypt", 15),
        (7, "decrypt", 16), (8, "decrypt", RFC_MAX_MESSAGE + 16),
]:
    add(f"boundary-aead-output-length-{direction}-{number:04d}", "aead_output_length",
        {"direction": direction, "input_length": length})
for number, direction, length in [
        (10, "encrypt", RFC_MAX_MESSAGE + 1), (11, "encrypt", 1 << 62),
        (12, "decrypt", RFC_MAX_MESSAGE + 17),
]:
    add(f"boundary-aead-output-length-{direction}-past-rfc-limit-{number:04d}", "aead_output_length",
        {"direction": direction, "input_length": length}, exclusion_reason=PAST_RFC_LIMIT_REASON)

for number, (seek, length) in enumerate([
        (0, 0), (1, 70), (63, 70), (64, 70), (65, 70), (1 << 32, 70),
        (CAP - 64, 64), (CAP - 64, 65), (CAP - 1, 1), (CAP - 1, 2), (CAP - 1, 0),
], 1):
    add(f"boundary-chacha20-xor-seek-{number:04d}", "chacha20_xor",
        {"key": rfc_key, "nonce": rfc_nonce, "seek": seek, "input": pattern(length, 0x30)})

for number, (seek, writes) in enumerate([
        (1, []), (63, [1]), (0, [64, 64]), (CAP - 64, [64]), (CAP - 64, [64, 0]),
        (CAP - 1, [0]), (CAP - 1, [1, 1]),
], 1):
    add(f"boundary-chacha20-remaining-{number:04d}", "chacha20_remaining",
        {"key": rfc_key, "nonce": rfc_nonce, "seek": seek, "writes": writes})

poly_key = "85d6be7857556d337f4452fe42d506a80103808afb0db2fd4abff6af4149f51b"  # RFC 8439 2.5.2
for number, length in enumerate([0, 1, 15, 16, 17, 31, 32, 33, 64], 1):
    add(f"boundary-poly1305-mac-len{length}-{number:04d}", "poly1305_mac",
        {"key": poly_key, "message": pattern(length, 0x40)})
add("boundary-poly1305-mac-unclamped-key-0010", "poly1305_mac",
    {"key": "ff" * 32, "message": "ff" * 16})

for number, pieces in enumerate([
        [], ["", ""], [pattern(15), pattern(1, 15), pattern(16, 16)],
        [pattern(1, i) for i in range(17)],
], 1):
    add(f"boundary-poly1305-mac-pieces-{number:04d}", "poly1305_mac_pieces",
        {"key": poly_key, "pieces": pieces})

for number, split in enumerate([0, 1, 16, 17, 33], 1):
    add(f"boundary-poly1305-mac-split-{number:04d}", "poly1305_mac_split",
        {"key": poly_key, "message": pattern(33, 0x40), "split": split})

for number, message in enumerate(["", "00"], 1):
    add(f"boundary-poly1305-update-unkeyed-{number:04d}", "poly1305_update_unkeyed",
        {"message": message})

for number, (first, second) in enumerate([("", ""), ("00", "00")], 1):
    add(f"boundary-poly1305-update-after-final-{number:04d}", "poly1305_update_after_final",
        {"key": poly_key, "first": first, "second": second})

# --- write ------------------------------------------------------------------

ids = [case["case_id"] for case in cases]
assert len(ids) == len(set(ids)), "duplicate case_id"
cases.sort(key=lambda case: case["case_id"].encode())
(ORACLE / "cases.jsonl").write_text(
    "".join(json.dumps(case, separators=(",", ":")) + "\n" for case in cases), encoding="utf-8")

manifest = {
    "case_file": "cases.jsonl",
    "source": ["upstream-test", "boundary"],
    "generator": "crypto-mixed-cases-v1",
    "command": "python3 oracle/make_cases.py",
    "upstream": {"repo": "https://github.com/randombit/botan", "tag": "3.13.0",
                 "commit": UPSTREAM_COMMIT},
    "vector_files": {path: hashlib.sha256((BOTAN / path).read_bytes()).hexdigest()
                     for path in VECTOR_FILES.values()},
    "case_count": len(cases),
    "not_translated": dict(sorted(not_translated.items())),
    "retired_case_ids": RETIRED_CASE_IDS,
    "upstream_sources": dict(sorted(sources.items())),
}
(ORACLE / "cases.jsonl.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(cases)} cases ({len(sources)} upstream-test); not translated: {not_translated}")
