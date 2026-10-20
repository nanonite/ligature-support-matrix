#!/usr/bin/env python3
"""Write oracle/random-cases.jsonl and its manifest (seeded random cases, chainlink #53).

Run from the pilot root after building the driver (oracle/build_upstream.sh):

    python3 oracle/generate_random_cases.py --seed 20261020 \\
        --driver /tmp/crypto-mixed-oracle-build/driver/oracle_driver

The protocol's third case source (oracle-PROTOCOL.md section 8). Every input
comes from a SplitMix64 stream seeded with --seed, with lengths biased toward
block and padding edges. Valid-decryption cases need ciphertexts that only
an implementation can produce, so the generator runs the pinned Botan driver
once on its own random encrypt cases and uses Botan's output, unchanged or
randomly mutated, as the decrypt inputs. The Rust port is never consulted.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ORACLE = Path(__file__).resolve().parent
CASE_FILE = "random-cases.jsonl"
UPSTREAM_COMMIT = "2a81eef56c96c237e590c27f9a75e60317c9c700"
GENERATOR = "splitmix64-v1"
MASK = (1 << 64) - 1
CAP = 1 << 38
RFC_MAX_MESSAGE = CAP - 64
EDGE_LENGTHS = [0, 1, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129]
COUNTS = {
    "aead-encrypt": 200,
    "aead-output-length": 50,
    "chacha20-xor": 200,
    "chacha20-remaining": 60,
    "poly1305-mac": 150,
    "poly1305-mac-pieces": 100,
    "poly1305-mac-split": 50,
}


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, bound):
        """Uniform integer in [0, bound) by rejection sampling."""
        if bound <= 0:
            raise ValueError("bound must be positive")
        limit = (1 << 64) - ((1 << 64) % bound)
        while True:
            value = self.next()
            if value < limit:
                return value % bound

    def between(self, low, high):
        return low + self.below(high - low + 1)

    def hex(self, length):
        out = bytearray()
        while len(out) < length:
            out += self.next().to_bytes(8, "little")
        return bytes(out[:length]).hex()

    def length(self, maximum):
        """An edge length a third of the time, otherwise uniform in [0, maximum]."""
        if self.below(3) == 0:
            return EDGE_LENGTHS[self.below(len(EDGE_LENGTHS))]
        return self.below(maximum + 1)


def seek_for(rng, length):
    """A byte offset below 2^38: small, block-aligned, anywhere, or near the cap."""
    kind = rng.below(5)
    if kind == 0:
        return rng.below(10_000)
    if kind == 1:
        return rng.below(1 << 32) * 64
    if kind == 2:
        return rng.below(CAP - length) if length < CAP else 0
    return CAP - rng.between(1, 600)  # kinds 3 and 4: near the cap, often past it


def flip_bit(rng, hex_value):
    data = bytearray.fromhex(hex_value)
    index = rng.below(len(data))
    data[index] ^= 1 << rng.below(8)
    return data.hex()


def generate(seed, driver):
    rng = SplitMix64(seed)
    cases = []

    def add(op_name, number, op, inputs):
        cases.append({"case_id": f"random-{op_name}-{number:04d}", "op": op, "inputs": inputs})

    encrypt_inputs = []
    for number in range(1, COUNTS["aead-encrypt"] + 1):
        inputs = {"key": rng.hex(32), "nonce": rng.hex(12), "ad": rng.hex(rng.length(80)),
                  "plaintext": rng.hex(rng.length(300))}
        encrypt_inputs.append(inputs)
        add("aead-encrypt", number, "aead_encrypt", inputs)

    for number in range(1, COUNTS["aead-output-length"] + 1):
        direction = "encrypt" if rng.below(2) == 0 else "decrypt"
        limit = RFC_MAX_MESSAGE if direction == "encrypt" else RFC_MAX_MESSAGE + 16
        length = rng.below(limit + 1) if rng.below(2) == 0 else rng.length(300)
        add("aead-output-length", number, "aead_output_length",
            {"direction": direction, "input_length": length})

    for number in range(1, COUNTS["chacha20-xor"] + 1):
        length = rng.length(300)
        add("chacha20-xor", number, "chacha20_xor",
            {"key": rng.hex(32), "nonce": rng.hex(12), "seek": seek_for(rng, length),
             "input": rng.hex(length)})

    for number in range(1, COUNTS["chacha20-remaining"] + 1):
        writes = [rng.length(300) for _ in range(rng.below(5))]
        add("chacha20-remaining", number, "chacha20_remaining",
            {"key": rng.hex(32), "nonce": rng.hex(12), "seek": seek_for(rng, sum(writes)),
             "writes": writes})

    for number in range(1, COUNTS["poly1305-mac"] + 1):
        add("poly1305-mac", number, "poly1305_mac",
            {"key": rng.hex(32), "message": rng.hex(rng.length(400))})

    for number in range(1, COUNTS["poly1305-mac-pieces"] + 1):
        message = rng.hex(rng.length(400))
        cuts = sorted(rng.below(len(message) // 2 + 1) for _ in range(rng.below(6)))
        bounds = [0, *cuts, len(message) // 2]
        pieces = [message[2 * start:2 * end] for start, end in zip(bounds, bounds[1:])]
        add("poly1305-mac-pieces", number, "poly1305_mac_pieces", {"key": rng.hex(32), "pieces": pieces})

    for number in range(1, COUNTS["poly1305-mac-split"] + 1):
        message = rng.hex(rng.length(400))
        add("poly1305-mac-split", number, "poly1305_mac_split",
            {"key": rng.hex(32), "message": message, "split": rng.below(len(message) // 2 + 1)})

    # Botan encrypts the random AEAD inputs; its ciphertexts become decrypt inputs.
    ciphertexts = botan_ciphertexts(driver, [c for c in cases if c["op"] == "aead_encrypt"])
    for number, inputs in enumerate(encrypt_inputs, 1):
        ciphertext = ciphertexts[f"random-aead-encrypt-{number:04d}"]
        add("aead-decrypt", number, "aead_decrypt",
            {"key": inputs["key"], "nonce": inputs["nonce"], "ad": inputs["ad"], "ciphertext": ciphertext})
        mutated = {"key": inputs["key"], "nonce": inputs["nonce"], "ad": inputs["ad"], "ciphertext": ciphertext}
        kind = rng.below(4)
        if kind == 0:
            mutated["ciphertext"] = flip_bit(rng, ciphertext)
        elif kind == 1:
            mutated["nonce"] = flip_bit(rng, inputs["nonce"])
        elif kind == 2:
            mutated["ad"] = flip_bit(rng, inputs["ad"]) if inputs["ad"] else rng.hex(1)
        else:
            # Resize like Botan's mutate_vec(maybe_resize): drop or append bytes.
            size = len(ciphertext) // 2
            if size and rng.below(2) == 0:
                mutated["ciphertext"] = ciphertext[:2 * (size - rng.between(1, size))]
            else:
                mutated["ciphertext"] = ciphertext + rng.hex(rng.between(1, 16))
        add("aead-decrypt-mutated", number, "aead_decrypt", mutated)

    cases.sort(key=lambda case: case["case_id"].encode())
    return cases


def botan_ciphertexts(driver, encrypt_cases):
    with tempfile.TemporaryDirectory() as tmp:
        cases_path = Path(tmp) / "encrypt.jsonl"
        results_path = Path(tmp) / "encrypt-results.jsonl"
        cases_path.write_text("".join(json.dumps(c, separators=(",", ":")) + "\n" for c in encrypt_cases),
                              encoding="utf-8")
        subprocess.run([driver, str(cases_path), str(results_path)], check=True)
        results = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
    out = {}
    for result in results:
        if result["status"] != "ok":
            raise ValueError(f"Botan rejected {result['case_id']}: {result}")
        out[result["case_id"]] = result["value"]["value"]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--driver", required=True, help="path to the built oracle_driver")
    args = parser.parse_args()
    cases = generate(args.seed, args.driver)
    (ORACLE / CASE_FILE).write_text(
        "".join(json.dumps(case, separators=(",", ":")) + "\n" for case in cases), encoding="utf-8")
    manifest = {
        "case_file": CASE_FILE,
        "source": "random",
        "seed": args.seed,
        "generator": GENERATOR,
        "command": f"python3 oracle/generate_random_cases.py --seed {args.seed} --driver {args.driver}",
        "upstream_commit": UPSTREAM_COMMIT,
        "case_count": len(cases),
        "derived_from_upstream": "random-aead-decrypt-* and random-aead-decrypt-mutated-* ciphertexts are the "
                                 "driver's (Botan's) output for random-aead-encrypt-* with the same number",
    }
    (ORACLE / f"{CASE_FILE}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} random cases to oracle/{CASE_FILE} (seed {args.seed})")


if __name__ == "__main__":
    main()
