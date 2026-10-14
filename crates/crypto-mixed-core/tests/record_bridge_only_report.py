#!/usr/bin/env python3
"""Assemble the AEAD package report from Ligature's verified bridge records.

The package provides no local obligation guarantee, so Ligature 1.3.10's
record-assurance command has no obligation proof with which to seed its report.
This adapter performs only the report handoff G14 requires: it validates the
current manifest and G9 records, then copies those records without changing
their verifier-produced contents or inventing an obligation result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_REL = Path("ci/manifest/WP-CRYPTO-MIXED-AEAD-001.json")
REPORT_REL = Path("ci/results/WP-CRYPTO-MIXED-AEAD-001.json")
BRIDGE_IDS = {
    "BR-CRYPTO-MIXED-001": (
        "the bounded model encoded by Kani harness "
        "bridge_001_passes_a_fixed_thirty_two_byte_poly1305_key"
    ),
    "BR-CRYPTO-MIXED-002": (
        "the bounded model encoded by Kani harness "
        "kani_chacha20_c003_aead_counter_one_stream_capacity"
    ),
}


class ReportError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReportError(f"required regular file is missing or unsafe: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReportError(f"cannot read valid JSON from {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReportError(f"expected a JSON object in {path.relative_to(ROOT)}")
    return data


def require_gates() -> None:
    ligature = ROOT / "tools/ligature/ligature.pyz"
    for args in (
        ["validate-work-package", str(MANIFEST_REL), "--specs-search-root", "crates"],
        ["gate-g9"],
    ):
        result = subprocess.run(
            [sys.executable, str(ligature), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip()[-1800:]
            raise ReportError(f"Ligature {' '.join(args)} failed: {detail}")


def verified_bridge_record(bridge_id: str, required_scope: str) -> dict[str, Any]:
    path = ROOT / "ci/results/bridge_checks" / f"{bridge_id}.json"
    data = load_json(path)
    if data.get("schema_version") != "1.0" or data.get("bridge_id") != bridge_id:
        raise ReportError(f"bridge result identity mismatch for {bridge_id}")
    if data.get("verifier") != "kani":
        raise ReportError(f"{bridge_id} was not dispatched to Kani")
    harness = data.get("harness")
    if not isinstance(harness, dict) or not isinstance(harness.get("sha256"), str):
        raise ReportError(f"{bridge_id} has no generated-harness hash")
    record = data.get("record")
    if not isinstance(record, dict):
        raise ReportError(f"{bridge_id} has no achieved record")
    claim = record.get("claim")
    evidence = record.get("evidence")
    scope = evidence.get("scope") if isinstance(evidence, dict) else None
    config = record.get("config")
    if not isinstance(claim, dict) or claim.get("kind") != "callee-precondition-established" or claim.get("result") != "pass":
        raise ReportError(f"{bridge_id} is not a passing callee-precondition record")
    if not isinstance(evidence, dict) or evidence.get("kind") != "kani-bounded-model-check" or evidence.get("verifier") != "kani":
        raise ReportError(f"{bridge_id} does not identify Kani bounded evidence")
    if evidence.get("harness") != harness.get("name"):
        raise ReportError(f"{bridge_id} record does not bind to its generated harness")
    if not isinstance(scope, dict) or scope.get("input_domain") != required_scope:
        raise ReportError(f"{bridge_id} scope does not match its reviewed minimum scope")
    if scope.get("harness_hash") != harness.get("sha256"):
        raise ReportError(f"{bridge_id} record has a stale generated-harness hash")
    if not isinstance(record.get("trust"), dict) or record["trust"].get("assumptions") != []:
        raise ReportError(f"{bridge_id} has an unsupported trusted assumption")
    if not isinstance(config, dict) or config.get("toolchain") != "1.95.0-x86_64-unknown-linux-gnu" or config.get("target") != "x86_64-unknown-linux-gnu" or config.get("features") != ["default"]:
        raise ReportError(f"{bridge_id} was not checked with the pilot's pinned Kani configuration")
    return {"bridge_id": bridge_id, "record": record}


def assemble() -> Path:
    manifest = load_json(ROOT / MANIFEST_REL)
    if manifest.get("work_package") != "WP-CRYPTO-MIXED-AEAD-001":
        raise ReportError("AEAD manifest work-package identity changed")
    done = manifest.get("definition_of_done")
    if not isinstance(done, dict) or done.get("provided_guarantees"):
        raise ReportError("bridge-only report is valid only for a package with no provided guarantees")
    required = done.get("required_preconditions_to_establish")
    if not isinstance(required, list) or {entry.get("bridge_id") for entry in required if isinstance(entry, dict)} != set(BRIDGE_IDS):
        raise ReportError("AEAD manifest no longer requires exactly the two reviewed bridges")
    report_cfg = manifest.get("report")
    if not isinstance(report_cfg, dict) or report_cfg.get("emit") != REPORT_REL.as_posix():
        raise ReportError("AEAD manifest report path is not the canonical package report path")
    require_gates()
    by_id = {entry["bridge_id"]: entry for entry in required}
    bridge_records = []
    for bridge_id, input_domain in BRIDGE_IDS.items():
        profile = by_id[bridge_id].get("required_assurance", {}).get("minimum_scope", {}).get("input_domain")
        if profile != input_domain:
            raise ReportError(f"{bridge_id} manifest scope differs from the reviewed mapping")
        bridge_records.append(verified_bridge_record(bridge_id, input_domain))
    report = {
        "schema_version": "1.0",
        "work_package": manifest["work_package"],
        "obligation_records": [],
        "bridge_records": bridge_records,
    }
    target = ROOT / REPORT_REL
    if target.is_symlink():
        raise ReportError("canonical report path must not be a symlink")
    encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if target.exists():
        if target.read_bytes() == encoded:
            return target
        raise ReportError("existing AEAD report differs; refusing to replace it")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".WP-CRYPTO-MIXED-AEAD-001.", dir=target.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    return target


def main() -> int:
    try:
        output = assemble()
    except (ReportError, OSError) as exc:
        print(f"bridge-only report refused: {exc}", file=sys.stderr)
        return 1
    print(f"recorded bridge-only assurance: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
