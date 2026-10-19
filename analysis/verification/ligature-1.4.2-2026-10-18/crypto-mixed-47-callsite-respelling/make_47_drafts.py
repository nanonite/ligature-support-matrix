#!/usr/bin/env python3
"""Write the #47 Stage 3 re-entry draft responses (manual LLM backend) as JSON files.

Usage: make_47_drafts.py <pilot-root> <out-dir>
Reads the current promoted concept specs from the pilot and emits one response
file per draft target, plus targets.json mapping target path -> response file.
"""
import copy
import json
import sys
from pathlib import Path

pilot = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
specs = pilot / "crates/crypto-mixed-core/specs"
TARGET = "x86_64-unknown-linux-gnu"
targets = {}


def emit(target, name, doc):
    path = out / f"{name}.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    targets[target] = path.name


def revise(spec_file, query, constraints, adversaries):
    doc = json.loads((specs / spec_file).read_text())
    doc.pop("review", None)
    # G1a only admits &self methods as concept queries; constructors and
    # associated functions are named in applies_to instead.
    if "&self" in query["rust_sig"]:
        doc["queries"].append(query)
    doc["constraints"].extend(constraints)
    doc["adversary_table"].extend(adversaries)
    return doc


chacha = revise(
    "cha_cha20.json",
    {
        "english": "Start a ChaCha20 stream at the requested 32-bit block counter.",
        "rust_sig": "fn with_counter(key: [u8; 32], nonce: [u8; 12], counter: u32) -> Self",
        "pure": True,
        "witness_required": False,
    },
    [
        {
            "english": "A stream started at block counter c has (2^32 - c) * 64 keystream bytes available.",
            "logic": "ChaCha20::with_counter(key, nonce, counter).bytes_remaining() as u64 == (4294967296 - counter as u64) * 64",
            "kind": "postcondition",
            "source": "hand",
            "applies_to": ["with_counter"],
            "id": "C004",
        },
        {
            "english": "The remaining capacity drops by exactly the input length after a successful keystream application and is unchanged after a rejected one.",
            "logic": "match self.apply_keystream(input) { Ok(_) => self.bytes_remaining() == old(self.bytes_remaining()) - input.len(), Err(_) => self.bytes_remaining() == old(self.bytes_remaining()) }",
            "kind": "postcondition",
            "source": "hand",
            "applies_to": ["bytes_remaining"],
            "id": "C005",
        },
    ],
    [
        {
            "scenario": "Start streams at counters 0, 1, and 2^32 - 1 and query the remaining capacity.",
            "violates": "C004",
            "resolution": "report exactly the remaining whole-block capacity for the starting counter",
        },
        {
            "scenario": "Consume 1, 63, 64, and 65 bytes, including an overlong request near counter exhaustion, then query the remaining capacity.",
            "violates": "C005",
            "resolution": "lower the capacity by exactly the consumed length and leave it unchanged on rejection",
        },
    ],
)
emit("crates/crypto-mixed-core/specs/cha_cha20.json", "spec-cha_cha20", chacha)

poly = revise(
    "poly1305.json",
    {
        "english": "Compute the Poly1305 tag over a sequence of message segments.",
        "rust_sig": "fn compute_tag_segments(key: &[u8; 32], segments: &[&[u8]]) -> [u8; 16]",
        "pure": True,
        "witness_required": False,
    },
    [
        {
            "english": "Authenticating a sequence of segments gives the tag of their concatenation.",
            "logic": "compute_tag_segments(key, segments) == compute_tag(key, &segments.concat())",
            "kind": "postcondition",
            "source": "hand",
            "applies_to": ["compute_tag_segments"],
            "id": "C005",
        }
    ],
    [
        {
            "scenario": "Split the RFC test message into three segments at block and non-block offsets, including empty segments.",
            "violates": "C005",
            "resolution": "produce the same tag as one-shot authentication of the concatenated message",
        }
    ],
)
emit("crates/crypto-mixed-core/specs/poly1305.json", "spec-poly1305", poly)

SNAKE = {"ChaCha20Poly1305": "cha_cha20_poly1305", "ChaCha20": "cha_cha20", "Poly1305": "poly1305"}
HARNESS = {
    "ChaCha20.C002": "kani_chacha20_c002_exact_length_65_boundary",
    "ChaCha20.C003": "kani_chacha20_c003_aead_counter_one_stream_capacity",
    "ChaCha20.C004": "kani_chacha20_c004_with_counter_stream_capacity",
    "ChaCha20.C005": "kani_chacha20_c005_bytes_remaining_tracks_consumption",
    "Poly1305.C005": "kani_poly1305_c005_segments_match_concatenation",
}
CLAIM = {"ChaCha20.C003": "callee-precondition-established"}

EDGES = [
    ("I-CRYPTO-MIXED-004", "encrypt", "ChaCha20", "with_counter", ["ChaCha20.C004"],
     ["numeric-domain-boundary", "stateful"], ["E-002", "E-005"],
     "AEAD encryption starts the ChaCha20 stream at block counter one, so its message limit depends on the capacity that starting counter leaves."),
    ("I-CRYPTO-MIXED-005", "encrypt", "ChaCha20", "bytes_remaining", ["ChaCha20.C005"],
     ["numeric-domain-boundary"], ["E-005"],
     "AEAD encryption compares the plaintext length with the stream's reported remaining capacity before applying the keystream."),
    ("I-CRYPTO-MIXED-006", "decrypt", "ChaCha20", "with_counter", ["ChaCha20.C004"],
     ["numeric-domain-boundary", "stateful"], ["E-002", "E-005"],
     "AEAD decryption starts the ChaCha20 stream at block counter one after authentication, so its message limit depends on the capacity that starting counter leaves."),
    ("I-CRYPTO-MIXED-007", "decrypt", "ChaCha20", "apply_keystream", ["ChaCha20.C002", "ChaCha20.C003"],
     ["stateful", "error-panic-boundary", "numeric-domain-boundary"], ["E-002", "E-005"],
     "AEAD decryption applies the stream cipher to the authenticated ciphertext and must respect its finite block-counter capacity while preserving the message length."),
    ("I-CRYPTO-MIXED-008", "tag", "Poly1305", "compute_tag_segments", ["Poly1305.C005"],
     ["numeric-domain-boundary"], ["E-003", "E-005"],
     "The AEAD tag authenticates the RFC 8439 MAC data (AAD, padding, ciphertext, padding, and the two little-endian lengths) as Poly1305 segments whose tag must equal that of their concatenation."),
]

for iid, caller_method, callee, callee_method, obligations, edge_class, evidence, rationale in EDGES:
    caller = "ChaCha20Poly1305"
    boundary_id = f"{SNAKE[caller]}_{caller_method}__to__{SNAKE[callee]}_{callee_method}"
    emit(f"crates/crypto-mixed-core/specs/_boundaries/{boundary_id}.json", f"boundary-{boundary_id}", {
        "schema_version": "1.0",
        "boundary_id": boundary_id,
        "caller": {"concept": caller, "method": caller_method},
        "callee": {"concept": callee, "method": callee_method},
        "callee_guarantees": obligations,
    })
    emit(f"crates/crypto-mixed-core/specs/_interactions/{iid}.json", f"interaction-{iid}", {
        "schema_version": "1.0",
        "interaction_id": iid,
        "caller": {"concept": caller, "method": caller_method},
        "callee": {"concept": callee, "method": callee_method},
        "edge_class": edge_class,
        "eligibility": "boundary-required",
        "rationale": rationale,
        "evidence_links": evidence,
        "reliances": [
            {
                "obligation_id": ob,
                "required_assurance": {
                    "required_claims": [CLAIM.get(ob, "postcondition-holds")],
                    "accepted_evidence_kinds": ["kani-bounded-model-check"],
                    "minimum_scope": {"input_domain": f"the bounded model encoded by Kani harness {HARNESS[ob]}"},
                    "trust_policy": {"assumptions_allowed": []},
                },
            }
            for ob in obligations
        ],
        "protocol_class": "pairwise",
        "realization": {
            "requirement": "required",
            "config_scope": {"target": TARGET, "features": ["default"], "cfg": []},
        },
    })

emit("crates/crypto-mixed-core/specs/_bridges/BR-CRYPTO-MIXED-003.json", "bridge-BR-CRYPTO-MIXED-003", {
    "schema_version": "1.0",
    "bridge_id": "BR-CRYPTO-MIXED-003",
    "boundary_id": "cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream",
    "callee_requirement": "ChaCha20.C003",
    "available_contract_facts": [
        {"obligation_id": "ChaCha20Poly1305.C002", "role": "caller-precondition"}
    ],
    "required_local_facts": [
        {"fact_id": "fresh_counter_one_stream", "expression": "chacha.bytes_remaining() == 274877906880"}
    ],
    "target_expression": "chacha.apply_keystream(ciphertext)",
    "protocol_class": "pairwise",
    "bridge_logic": {
        "bindings": {"caller_self": "ChaCha20Poly1305", "chacha": "ChaCha20", "ciphertext": "&[u8]"},
        "premises": [
            "ChaCha20Poly1305.C002(caller_self, ciphertext)",
            "fresh_counter_one_stream(chacha, ciphertext)",
        ],
        "conclusion": {"obligation_id": "ChaCha20.C003"},
    },
})

(out / "targets.json").write_text(json.dumps(targets, indent=2) + "\n")
print(f"wrote {len(targets)} draft responses to {out}")
