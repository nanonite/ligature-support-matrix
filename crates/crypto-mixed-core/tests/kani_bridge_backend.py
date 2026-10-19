#!/usr/bin/env python3
"""Fail-closed Kani adapter for this pilot's generated bridge contracts.

Ligature 1.3.10 dispatches the generated bridge harness path to this program.
The generated DSL is not standalone Rust, so this adapter checks its exact
current bridge body against an explicit mapping and then runs the corresponding
source-level Kani proof. Any change to the generated claim or premise is refused.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CRATE = ROOT / "crates/crypto-mixed-core"
KANI_TOOLCHAIN = "1.95.0-x86_64-unknown-linux-gnu"
KANI_VERSION = "0.67.0"
KANI_TIMEOUT_SECONDS = 180


def compact_body(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("//"):
            lines.append(" ".join(line.split()))
    return "\n".join(lines)


BRIDGES: dict[str, dict[str, Any]] = {
    "BR-CRYPTO-MIXED-001": {
        "boundary": "cha_cha20_poly1305_encrypt__to__poly1305_set_key",
        "conclusion": "Poly1305.C001",
        "function": "bridge_br_crypto_mixed_001",
        "body": """#[kani::proof]
pub fn bridge_br_crypto_mixed_001() {
let key: &[u8; 32] = kani::any();
let poly1305_state: Poly1305 = kani::any();
kani::assume(key_is_32_bytes(key));
assert!(Poly1305::C001(key, poly1305_state), \"BR-CRYPTO-MIXED-001: Poly1305.C001\");
}""",
        "source_harness": "bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key",
        "scope": "the bounded model encoded by Kani harness bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key",
    },
    "BR-CRYPTO-MIXED-002": {
        "boundary": "cha_cha20_poly1305_encrypt__to__cha_cha20_apply_keystream",
        "conclusion": "ChaCha20.C003",
        "function": "bridge_br_crypto_mixed_002",
        "body": """#[kani::proof]
pub fn bridge_br_crypto_mixed_002() {
let caller_self: ChaCha20Poly1305 = kani::any();
let chacha: ChaCha20 = kani::any();
let plaintext: &[u8] = kani::any();
kani::assume(ChaCha20Poly1305::C001(caller_self, plaintext));
kani::assume(input_fits_remaining_stream(chacha, plaintext));
assert!(ChaCha20::C003(caller_self, chacha, plaintext), \"BR-CRYPTO-MIXED-002: ChaCha20.C003\");
}""",
        "source_harness": "kani_chacha20_c003_aead_counter_one_stream_capacity",
        "scope": "the bounded model encoded by Kani harness kani_chacha20_c003_aead_counter_one_stream_capacity",
    },
    "BR-CRYPTO-MIXED-003": {
        "boundary": "cha_cha20_poly1305_decrypt__to__cha_cha20_apply_keystream",
        "conclusion": "ChaCha20.C003",
        "function": "bridge_br_crypto_mixed_003",
        "body": """#[kani::proof]
pub fn bridge_br_crypto_mixed_003() {
let caller_self: ChaCha20Poly1305 = kani::any();
let chacha: ChaCha20 = kani::any();
let ciphertext: &[u8] = kani::any();
kani::assume(ChaCha20Poly1305::C002(caller_self, ciphertext));
kani::assume(fresh_counter_one_stream(chacha, ciphertext));
assert!(ChaCha20::C003(caller_self, chacha, ciphertext), \"BR-CRYPTO-MIXED-003: ChaCha20.C003\");
}""",
        "source_harness": "kani_chacha20_c003_aead_counter_one_stream_capacity",
        "scope": "the bounded model encoded by Kani harness kani_chacha20_c003_aead_counter_one_stream_capacity",
    },
}


class BackendError(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_file(path_text: str) -> Path:
    candidate = Path(path_text)
    unresolved = candidate if candidate.is_absolute() else ROOT / candidate
    if unresolved.is_symlink():
        raise BackendError("bridge harness path must not be a symlink")
    path = unresolved.resolve(strict=True)
    if ROOT not in path.parents or not path.is_file():
        raise BackendError("bridge harness must be a regular file inside the pilot workspace")
    return path


def validate_generated_harness(path: Path) -> tuple[str, dict[str, Any]]:
    if path.stat().st_size > 32_768:
        raise BackendError("generated bridge harness exceeds the adapter's size limit")
    text = path.read_text(encoding="utf-8")
    bridge_ids = re.findall(r"(?m)^// bridge_id: (BR-[A-Z0-9-]+)$", text)
    if len(bridge_ids) != 1 or bridge_ids[0] not in BRIDGES:
        raise BackendError("generated harness has an unknown or ambiguous bridge ID")
    bridge_id = bridge_ids[0]
    spec = BRIDGES[bridge_id]
    if path.relative_to(ROOT).as_posix() != f"ci/harness/{bridge_id}.kani.rs":
        raise BackendError("bridge harness path is not Ligature's canonical generated path")
    headers = {
        "boundary_id": re.findall(r"(?m)^// boundary_id: ([a-z0-9_]+)$", text),
        "verifier": re.findall(r"(?m)^// verifier: ([a-z]+)$", text),
        "conclusion": re.findall(r"(?m)^// conclusion: ([A-Za-z0-9.]+)$", text),
    }
    expected = {
        "boundary_id": spec["boundary"],
        "verifier": "kani",
        "conclusion": spec["conclusion"],
    }
    for key, value in expected.items():
        if headers[key] != [value]:
            raise BackendError(f"{bridge_id} generated {key} does not match its reviewed mapping")
    if path.name != f"{bridge_id}.kani.rs":
        raise BackendError("generated harness filename does not match its bridge ID")
    if compact_body(text) != compact_body(spec["body"]):
        raise BackendError(f"{bridge_id} generated bridge premises or conclusion changed")
    return bridge_id, spec


def run(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise BackendError(f"command timed out after {timeout}s: {' '.join(command)}") from exc
    except OSError as exc:
        raise BackendError(f"cannot run {' '.join(command)}: {exc}") from exc


def rust_host(cargo: str) -> str:
    rustc = shutil.which("rustc")
    if rustc is None:
        raise BackendError("rustc is unavailable")
    result = run([rustc, f"+{KANI_TOOLCHAIN}", "-vV"], cwd=CRATE, timeout=30)
    if result.returncode != 0:
        raise BackendError(f"pinned rustc version query failed: {result.stderr.strip()}")
    host = re.findall(r"(?m)^host: (\S+)$", result.stdout)
    if host != ["x86_64-unknown-linux-gnu"]:
        raise BackendError(f"Kani host does not match the pilot target: {host!r}")
    version = re.findall(r"(?m)^release: (\S+)$", result.stdout)
    if version != ["1.95.0"]:
        raise BackendError(f"pinned Rust toolchain version mismatch: {version!r}")
    return host[0]


def require_locked_metadata(cargo: str) -> None:
    result = run(
        [
            cargo,
            f"+{KANI_TOOLCHAIN}",
            "metadata",
            "--format-version",
            "1",
            "--locked",
            "--manifest-path",
            str(CRATE / "Cargo.toml"),
        ],
        cwd=CRATE,
        timeout=30,
    )
    if result.returncode != 0:
        raise BackendError(
            "cargo metadata --locked failed before bridge verification: "
            + (result.stderr or result.stdout).strip()[-1200:]
        )


def resolve_source_harness(cargo: str, source_harness: str) -> str:
    with tempfile.TemporaryDirectory(prefix="crypto-mixed-kani-discovery-") as target_dir:
        command = [
            cargo,
            f"+{KANI_TOOLCHAIN}",
            "kani",
            "-Z",
            "unstable-options",
            "--manifest-path",
            str(CRATE / "Cargo.toml"),
            "--only-codegen",
            "--target-dir",
            target_dir,
        ]
        result = run(command, cwd=CRATE, timeout=KANI_TIMEOUT_SECONDS)
        if result.returncode != 0:
            raise BackendError(
                "Kani compile-only harness discovery failed: "
                + ((result.stderr or result.stdout).strip()[-1800:])
            )
        matches: list[str] = []
        root = Path(target_dir).resolve()
        for metadata_path in sorted(root.rglob("*.kani-metadata.json")):
            if metadata_path.is_symlink() or not metadata_path.is_file() or root not in metadata_path.resolve().parents:
                raise BackendError("Kani emitted an unsafe metadata path")
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BackendError(f"invalid Kani metadata: {metadata_path.name}: {exc}") from exc
            if not isinstance(metadata, dict) or metadata.get("crate_name") != "crypto_mixed_core":
                continue
            proofs = metadata.get("proof_harnesses")
            if not isinstance(proofs, list):
                raise BackendError("Kani metadata has no proof_harnesses list")
            for proof in proofs:
                identity = proof.get("pretty_name") if isinstance(proof, dict) else None
                if isinstance(identity, str) and identity.rsplit("::", 1)[-1] == source_harness:
                    matches.append(identity)
        if len(matches) != 1:
            raise BackendError(
                f"expected one Kani identity for {source_harness}, found {matches!r}"
            )
        return matches[0]


def parse_kani_result(
    result_text: str, driver_output: str, returncode: int, identity: str
) -> tuple[int, int, int]:
    headers = re.findall(r"(?m)^Checking harness (.+)\.\.\.\s*$", driver_output)
    if headers != [identity]:
        raise BackendError(f"Kani did not identify exactly the requested harness: {headers!r}")
    results = list(re.finditer(r"(?m)^RESULTS:\s*$", result_text))
    summaries = list(re.finditer(r"(?m)^SUMMARY:\s*$", result_text))
    if len(results) != 1 or len(summaries) != 1 or summaries[0].start() <= results[0].end():
        raise BackendError("Kani per-harness output is incomplete")
    checks_text = result_text[results[0].end():summaries[0].start()]
    check_headers = list(re.finditer(r"(?m)^Check ([0-9]+): (.+)$", checks_text))
    if not check_headers:
        raise BackendError("Kani produced no per-check results")
    statuses: list[str] = []
    successful_assertions = 0
    for index, header in enumerate(check_headers):
        end = check_headers[index + 1].start() if index + 1 < len(check_headers) else len(checks_text)
        block = checks_text[header.end():end]
        status = re.findall(r"(?m)^\s+- Status: ([A-Z_]+)\s*$", block)
        description = re.findall(r'(?m)^\s+- Description: (".*")\s*$', block)
        if len(status) != 1 or len(description) != 1:
            raise BackendError("Kani has a malformed or incomplete check record")
        desc = description[0][1:-1]
        name = header.group(2).strip()
        if ".cover." in name or name.endswith(".cover") or desc.startswith("cover condition:"):
            raise BackendError("Kani cover properties are not accepted as bridge proofs")
        if status[0] not in {"SUCCESS", "UNREACHABLE"}:
            raise BackendError(f"Kani check {header.group(1)} has status {status[0]}")
        if status[0] == "UNREACHABLE" and desc.startswith("assertion failed:"):
            raise BackendError("Kani obligation assertion is unreachable (vacuous)")
        if name.startswith(identity + ".assertion.") and desc.startswith("assertion failed:"):
            if status[0] != "SUCCESS":
                raise BackendError("Kani obligation assertion did not succeed")
            successful_assertions += 1
        statuses.append(status[0])
    if [int(h.group(1)) for h in check_headers] != list(range(1, len(check_headers) + 1)):
        raise BackendError("Kani check list is not complete and sequential")
    aggregate = re.findall(
        r"(?m)^\s*\*\* ([0-9]+) of ([0-9]+) failed(?: \(([0-9]+) unreachable\))?\s*$",
        result_text,
    )
    manual = re.findall(
        r"(?m)^Manual Harness Summary:\s*Complete - ([0-9]+) successfully verified "
        r"harnesses, ([0-9]+) failures, ([0-9]+) total\.\s*$",
        driver_output,
    )
    if len(aggregate) != 1 or len(manual) != 1:
        raise BackendError("Kani output has no unique complete run summary")
    failed, total, unreachable_text = aggregate[0]
    unreachable = int(unreachable_text or 0)
    if int(total) != len(statuses) or unreachable != sum(s == "UNREACHABLE" for s in statuses):
        raise BackendError("Kani aggregate counts do not match per-check results")
    if returncode != 0 or int(failed) != 0 or manual[0] != ("1", "0", "1"):
        raise BackendError("Kani did not completely verify exactly one harness")
    if successful_assertions < 1:
        raise BackendError("Kani run has no reachable successful harness assertion")
    if result_text.count("VERIFICATION:- SUCCESSFUL") != 1:
        raise BackendError("Kani output has no unique successful verification verdict")
    return len(statuses) - unreachable, unreachable, len(statuses)


def execute_bridge(path_text: str) -> dict[str, Any]:
    bridge_path = workspace_file(path_text)
    bridge_id, spec = validate_generated_harness(bridge_path)
    proof_source = CRATE / "src/kani_proofs.rs"
    lockfile = CRATE / "Cargo.lock"
    if lockfile.is_symlink() or not lockfile.is_file():
        raise BackendError("the crate's approved Cargo.lock is required for locked Kani runs")
    if not proof_source.is_file() or proof_source.is_symlink():
        raise BackendError("Kani proof source is missing or unsafe")
    source_text = proof_source.read_text(encoding="utf-8")
    if len(re.findall(rf"(?m)^fn {re.escape(spec['source_harness'])}\s*\(", source_text)) != 1:
        raise BackendError("mapped source harness is missing or ambiguous")
    source_hash = sha256(proof_source)
    cargo = shutil.which("cargo")
    if cargo is None:
        raise BackendError("cargo is unavailable")
    require_locked_metadata(cargo)
    kani_version = run([cargo, f"+{KANI_TOOLCHAIN}", "kani", "--version"], cwd=CRATE, timeout=30)
    if kani_version.returncode != 0 or KANI_VERSION not in (kani_version.stdout + kani_version.stderr):
        raise BackendError("the configured Kani runner is not version 0.67.0")
    target = rust_host(cargo)
    identity = resolve_source_harness(cargo, spec["source_harness"])
    with tempfile.TemporaryDirectory(prefix="crypto-mixed-kani-bridge-") as target_dir:
        command = [
            cargo,
            f"+{KANI_TOOLCHAIN}",
            "kani",
            "-Z",
            "unstable-options",
            "--manifest-path",
            str(CRATE / "Cargo.toml"),
            "--harness",
            identity,
            "--exact",
            "--output-format",
            "regular",
            "--output-into-files",
            "--target-dir",
            target_dir,
        ]
        result = run(command, cwd=CRATE, timeout=KANI_TIMEOUT_SECONDS)
        driver_output = (result.stdout or "") + (result.stderr or "")
        result_path = Path(target_dir) / "result_output_dir" / identity
        if result_path.is_symlink() or not result_path.is_file():
            raise BackendError("Kani did not produce the expected per-harness result file")
        checks, unreachable, total = parse_kani_result(
            result_path.read_text(encoding="utf-8"), driver_output, result.returncode, identity
        )
    if sha256(proof_source) != source_hash:
        raise BackendError("Kani proof source changed while the bridge was being verified")
    return {
        "result": "pass",
        "scope": {
            "input_domain": spec["scope"],
            "source_harness": spec["source_harness"],
            "source_harness_sha256": source_hash,
            "kani_version": KANI_VERSION,
        },
        "assumptions": [],
        "config": {
            "toolchain": KANI_TOOLCHAIN,
            "target": target,
            "features": ["default"],
        },
        "detail": (
            f"source harness {spec['source_harness']} verified: "
            f"{checks} successful checks, {unreachable} unreachable, {total} total"
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: kani_bridge_backend.py GENERATED_BRIDGE_HARNESS", file=sys.stderr)
        return 2
    try:
        verdict = execute_bridge(argv[0])
    except (BackendError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"Kani bridge backend refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
