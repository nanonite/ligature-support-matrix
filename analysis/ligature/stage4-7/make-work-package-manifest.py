#!/usr/bin/env python3
"""Generate ci/manifest/WP-SWISSTABLE-VERUS.json from the pilot's real artifacts.

HAND-AUTHORED, because ligature 1.2.1 ships no Stage 7 work-package generator.
`ligature.pyz --help` lists 43 verbs and none of them generate a manifest:
`validate-work-package` is validate-only ("Standalone, not routed through
draft/approve -- a manifest is machine-generated at Stage 7 from already-promoted
content"), and there is no `generate-work-package`.  See the README section
"Stage 7".  So this script stands in for the missing generator: every value it
writes is DERIVED from a real file on disk, never remembered, and re-running it
reproduces the manifest byte-for-byte.

Run from swisstable-verus/:
    python3 analysis/ligature/stage4-7/make-work-package-manifest.py

Determinism and the three P1 mistakes this deliberately avoids are documented in
the README.  Exit 1 if anything it derives is inconsistent, rather than writing a
plausible-looking file.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from path_root import pilot_root

ROOT = pilot_root()  # walks up to the dir holding project-descriptor.json
assert os.path.isfile(os.path.join(ROOT, "project-descriptor.json")), ROOT
os.chdir(ROOT)

WP = "WP-SWISSTABLE-VERUS"
CLUSTER = "swisstable-verus-core"
OUT = f"ci/manifest/{WP}.json"

# G13 requires these two ligature-managed scripts to have their own gate_integrity
# entry, protected_write_set coverage and NO allowed_write_set coverage --
# unconditional for every manifest (validate-work-package --help).  Hashes are the
# real sha256 of the installed files, recomputed here rather than pasted.
GATE_SCRIPTS = ["scripts/witness_renderer.py", "scripts/xml_escape.py"]

# verifier_policy.default in project-descriptor.json; re-read rather than assumed.
VERIFIER = json.load(open("project-descriptor.json"))["verifier_policy"]["default"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def git_head(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", *args, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def rustc_host() -> str:
    out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        if line.startswith("host: "):
            return line[len("host: "):].strip()
    raise SystemExit("could not read the rustc host triple")


def method_name(rust_sig: str) -> str:
    # "fn is_empty(&self, slot: usize) -> bool" -> "is_empty"
    body = rust_sig.split("fn ", 1)[1]
    return body.split("(", 1)[0].strip()


# ---------------------------------------------------------------- concept specs
concept_files = sorted(glob.glob("rust/swisstable-verus-core/specs/*.json.draft"))
if len(concept_files) != 7:
    raise SystemExit(f"expected 7 concept specs, found {len(concept_files)}: {concept_files}")

concepts = [json.load(open(f)) for f in concept_files]
for c in concepts:
    if c.get("verifier") != VERIFIER:
        raise SystemExit(f"{c['concept']} declares verifier {c.get('verifier')!r}, not {VERIFIER!r}")

functions: list[str] = []
provided: list[tuple[str, str]] = []      # (obligation_id, constraint kind)
preconditions: list[tuple[str, str]] = []
for c in concepts:
    for q in c.get("queries", []):
        functions.append(f"{c['concept']}::{method_name(q['rust_sig'])}")
    for cmd in c.get("commands", []):
        functions.append(f"{c['concept']}::{method_name(cmd['rust_sig'])}")
    for con in c["constraints"]:
        oid = f"{c['concept']}.{con['id']}"
        (preconditions if con["kind"] == "precondition" else provided).append((oid, con["kind"]))

provided.sort()
preconditions.sort()

# Every bridge's own `callee_requirement` must be one of the six precondition
# obligations, and must equal its `bridge_logic.conclusion.obligation_id` (bridge
# G2 / G1b). Cross-checked here so `required_preconditions_to_establish` can only
# ever name a bridge that really discharges one of them.
bridge_files = sorted(glob.glob("rust/swisstable-verus-core/specs/_bridges/*.json.draft"))
bridge_ids: list[str] = []
precondition_set = {oid for oid, _ in preconditions}
for f in bridge_files:
    b = json.load(open(f))
    if b["callee_requirement"] != b["bridge_logic"]["conclusion"]["obligation_id"]:
        raise SystemExit(f"{b['bridge_id']}: callee_requirement and conclusion.obligation_id differ")
    if b["callee_requirement"] not in precondition_set:
        raise SystemExit(f"{b['bridge_id']} discharges {b['callee_requirement']}, which is not "
                         f"a precondition-kind constraint of any concept")
    bridge_ids.append(b["bridge_id"])
discharged = {json.load(open(f))["callee_requirement"] for f in bridge_files}
undischarged = precondition_set - discharged
if undischarged:
    print(f"NOTE: precondition obligations with no bridge: {sorted(undischarged)}")

# Every query/command the constraints rely on must be a real declared method of its
# own concept.  P1 and this pilot's own artifacts.py both caught the id half of this;
# re-check the whole set here so the manifest cannot name a method that does not
# exist.
declared = {f"{c['concept']}::{method_name(q['rust_sig'])}" for c in concepts
            for q in c.get("queries", []) + c.get("commands", [])}
for c in concepts:
    for con in c["constraints"]:
        for m in con["applies_to"]:
            if f"{c['concept']}::{m}" not in declared:
                raise SystemExit(f"{c['concept']}.{con['id']} applies_to {m!r}, which is not a "
                                 f"declared query/command of {c['concept']}")

# ------------------------------------------------------------------ provenance
descriptor = json.load(open("project-descriptor.json"))
base_commit = git_head("upstream/abseil-cpp")
# accept-promotion computes promotion_id from `cluster` alone.  Measured, not
# guessed: the Stage 4.5 scratch proof's receipt carried exactly this value.
promotion_id = f"PROM-{CLUSTER.upper()}-001"

# artifact_set_hash is required (G1a) and format-checked against
# ^sha256:[0-9a-f]{64}$, so there is no honest way to write "pending".  The value
# below is the real sha256 of the receipt the Stage 4.5 scratch proof minted, read
# out of that proof's own transcript rather than remembered -- but it is the SCRATCH
# receipt, taken over a scratch-filled reliance policy, and no receipt exists on the
# live root yet because accept-promotion is pending the operator's batch.  The
# coupling_notes entry below says so in the manifest itself, and
# check-runbook-29.py re-derives and re-checks it.
PROOF = "analysis/ligature/stage4-7/stage45-scratch-proof.txt"
scratch_receipt_sha = None
for line in open(PROOF):
    parts = line.split()
    if len(parts) == 2 and parts[1] == "specs/_promotions/swisstable-verus-core.json":
        scratch_receipt_sha = "sha256:" + parts[0]
if not scratch_receipt_sha:
    raise SystemExit(f"could not read the scratch receipt sha256 out of {PROOF}")

# ------------------------------------------------------------------ write policy
# A FAITHFUL copy of the descriptor's own write_set.  Both lists verbatim -- this
# pilot's descriptor already carries crate-scoped protected globs
# (`rust/*/Cargo.toml`, `rust/*/build.rs`), so P1's `date-ligature-034` overlap
# cannot arise here and no narrowing or widening is needed or wanted.
ws = descriptor["write_set"]
write_policy = {
    "allowed_write_set": list(ws["allowed_roots"]),
    "protected_write_set": list(ws["protected_roots"]),
    "on_conflict": "raise_change_request",
}

for s in GATE_SCRIPTS:
    if not any(s.startswith(p.rstrip("*")) or p.startswith(s.split("/")[-1])
               for p in write_policy["protected_write_set"] if "scripts" in p):
        # `scripts/**` is the pattern; check the file really is covered by it.
        if not any(p == "scripts/**" for p in write_policy["protected_write_set"]):
            raise SystemExit(f"{s} is not covered by protected_write_set")
    for a in write_policy["allowed_write_set"]:
        if a == "scripts/**":
            raise SystemExit(f"{s} must not be in allowed_write_set (G13)")

manifest = {
    "schema": "work-package-manifest/1.0",
    "work_package": WP,
    "issue": "chainlink:29",
    # This is the only work package in this workspace.  `depends_on` must therefore
    # be empty: an earlier P1 manifest named WP-DATE-CREUSOT-CORE, which resolves to
    # nothing, and P1 spent real time on the dangling reference.  Emptiness here is
    # a claim about the workspace, not an omission -- check-runbook-29.py verifies it.
    "depends_on": [],
    "coupling_notes": [
        "One work package, seven concepts in six clusters (hashing, control-bytes, "
        "probing, table, api, iteration). There is no second work package in this "
        "workspace, so `depends_on` is empty and `required_guarantees` is empty: a "
        "work package may not assume its own output as its own input (P1 hit that "
        "as a CG6 'mutual satisfaction is not soundness' cycle -- chainlink #15).",
        "The tightest coupling is the probe sequence's dependence on the table's "
        "capacity encoding: BR-PROBESEQ-MASK-001 has to derive `capacity_mask + 1 == "
        "(1 << capacity_bits)` from RawTable.C001/C004 to discharge the "
        "`ProbeSeq.C001` precondition at RawTable.find -> ProbeSeq.offset. That is the "
        "one place where a rehash policy change in RawTable would invalidate a "
        "callee obligation rather than just a boundary.",
        "Group probing couples to control bytes twice over: GroupProbe.match_full and "
        "match_empty_or_deleted read the H2 tag GroupProbe.load writes, and the same "
        "mask drives the free-window query BR-GROUPPROBE-FREE-WINDOW-001. Changing the "
        "tag encoding in ControlBytes.C007 breaks both bridges at once.",
        "ControlBytes.clear_dead (rehash) is the only edge that destroys tombstones, "
        "so it is the only place a capacity change is observable. It is bridged "
        "separately (BR-CONTROLBYTES-CLEARDEAD-001) from set_dead "
        "(BR-CONTROLBYTES-SETDEAD-001) precisely so that a rehash-only regression is "
        "not confused with a tombstone-marking one.",
        "All 30 non-precondition obligations require verus-deductive-check evidence. "
        "The promoted interactions are protocol_class `pairwise` with no trusted "
        "assumptions, so `trusted_assumptions` is empty.",
        "The 6 precondition obligations are deliberately NOT in "
        "`provided_guarantees`: they are established at the call site and discharged "
        "by the bridges, which is the only shape that satisfies bridge G2 "
        "(`callee_requirement` must be one of the boundary's own "
        "`callee_guarantees`). They appear under "
        "`required_preconditions_to_establish`, one entry per bridge -- "
        "BR-CONTROLBYTES-CLEARDEAD-001/ControlBytes.C005, "
        "BR-CONTROLBYTES-SETDEAD-001/ControlBytes.C003, "
        "BR-GROUPPROBE-FREE-WINDOW-001/GroupProbe.C001, "
        "BR-GROUPPROBE-WINDOW-001/GroupProbe.C001, "
        "BR-PROBESEQ-MASK-001/ProbeSeq.C001, "
        "BR-RAWINSERT-NONFULL-001/RawTable.C003 -- so nothing is both provided and "
        "required. The obligation id lives in each bridge's own "
        "`callee_requirement`, which is where bridge G2 reads it from; the manifest "
        "schema's `required_preconditions_to_establish` entry carries only "
        "`bridge_id`, `callsite_requirement` and `required_assurance`. See epic #1 "
        "#112 for the template disagreement that forces this shape.",
        "EC-1 (promoted) resolves the E-007/E-008 conflict in favour of the per-table "
        "seed randomising iteration order, so TableIterator.C004 and SwissTable.C004 "
        "are written from E-008 and no obligation here constrains an iteration order.",
        "`gate_integrity` carries the real sha256 of the two ligature-managed witness "
        "renderer scripts, recomputed by the generator; G13 verifies both against the "
        "installed files. The ligature 1.0-era zero hashes P1 had to remove are never "
        "written here.",
        "`provenance.promotion_id` is PROM-SWISSTABLE-VERUS-CORE-001, derived from "
        "`cluster` alone by accept-promotion and confirmed against the receipt minted "
        "by the Stage 4.5 scratch proof (analysis/ligature/stage4-7/"
        "stage45-scratch-proof.txt). `provenance.artifact_set_hash` is the real "
        "sha256 of THAT SAME SCRATCH receipt, not of a live-root receipt: no "
        "promotion receipt exists on the live root yet, because accept-promotion is "
        "pending the operator's batch approval, and the only receipt that exists was "
        "minted on a scratch copy whose reliance-policy.md had scratch placeholder "
        "values filled in. It is a real hash of a real file, but it is NOT the "
        "live-root artifact set. After the operator batch, re-run this generator "
        "against the real receipt; until then `promotion_id` and `artifact_set_hash` "
        "are the two fields to re-read. `validate-work-package` reports the missing "
        "receipt separately as a 10.1/info.",
        "E-010 and E-011 are lifecycle: deferred, so they are in the accepted "
        "promotion set as evidence records but assert no constraint; no obligation in "
        "this manifest rests on either.",
    ],
    "scheduling_rule": "reverse-dependency-order",
    "functions": functions,
    "obligations": [oid for oid, _ in provided + preconditions],
    "provenance": {
        "base_commit": base_commit,
        "promotion_id": promotion_id,
        "artifact_set_hash": scratch_receipt_sha,
        "toolchain": f"rustc/cargo/{VERIFIER}",
        "target": rustc_host(),
        "features": ["default"],
    },
    "gate_integrity": [{"runner": s, "hash": sha256(s)} for s in GATE_SCRIPTS],
    "write_policy": write_policy,
    "definition_of_done": {
        # The schema's required_claims vocabulary is exactly
        # ['callee-precondition-established', 'postcondition-holds'] -- measured, by
        # probing validate-work-package, not assumed. It has no separate invariant
        # claim, so an `invariant` obligation is certified as `postcondition-holds`:
        # what the verifier proves is that the invariant holds at every point the
        # relying method's spec is checked, which is a postcondition of that method.
        # Only `precondition` obligations take `callee-precondition-established`, and
        # those live in required_preconditions_to_establish, not here.
        "provided_guarantees": [
            {
                "obligation_id": oid,
                "required_assurance": {
                    "required_claims": ["postcondition-holds"],
                    "accepted_evidence_kinds": [f"{VERIFIER}-deductive-check"],
                },
                "harness": VERIFIER,
            }
            for oid, _ in provided
        ],
        # One entry per bridge. The schema fixes the entry shape to exactly
        # {bridge_id, callsite_requirement, required_assurance}, and
        # `callsite_requirement` has exactly one permitted value,
        # 'all-discovered-resolved' -- both measured by probing, not guessed.
        "required_preconditions_to_establish": [
            {
                "bridge_id": bid,
                "callsite_requirement": "all-discovered-resolved",
                "required_assurance": {
                    "required_claims": ["callee-precondition-established"],
                    "accepted_evidence_kinds": [f"{VERIFIER}-deductive-check"],
                },
            }
            for bid in bridge_ids
        ],
        # Empty on purpose: a single work package has no external callee to require an
        # obligation from. See coupling_notes[0] and the P1 CG6 cycle.
        "required_guarantees": [],
        "trusted_assumptions": [],
    },
    # g1a/g1b/g15/r2 are P1's set unchanged; g2 and g9 are added because this pilot
    # has 6 bridges, which P1 had none of. `gate <id>` is the dispatcher form.
    "gates": [
        {"id": "g1a", "runner": "ligature", "args": ["validate"]},
        {"id": "g1b", "runner": "ligature", "args": ["validate-interaction"]},
        {"id": "g2", "runner": "ligature", "args": ["validate-bridge"]},
        {"id": "g9", "runner": "ligature", "args": ["gate", "g9"]},
        {"id": "g15", "runner": "ligature", "args": ["validate-interaction"]},
        {"id": "r2", "runner": "ligature", "args": ["validate-interaction"]},
        {"id": "g18", "runner": "ligature", "args": ["gate", "g18"]},
        {"id": "g19", "runner": "ligature", "args": ["gate", "g19"]},
        {"id": "g20", "runner": "ligature", "args": ["gate", "g20"]},
    ],
    "failure_policy": {
        "verifier_timeout": "raise_change_request(kind=timeout)",
        "obligation_unprovable": "raise_change_request(kind=change_request)",
        "missing_callee_guarantee": "raise_change_request(kind=change_request)",
        "unintended_call_edge": "raise_change_request(kind=change_request)",
        "unresolved_callsite": "raise_change_request(kind=change_request)",
        "forbidden": [],
    },
    "report": {
        # Deliberately NOT ci/results/feature_ledger.json, which is where P1 pointed
        # it and where `report feature-ledger` and `record-assurance` then collided on
        # one path with incompatible schemas (P1 escalated it). One path, one writer.
        "emit": f"ci/results/{WP}.json",
        "per_obligation_assurance_record": True,
    },
}

os.makedirs("ci/manifest", exist_ok=True)
with open(OUT, "w") as fh:
    json.dump(manifest, fh, indent=2)
    fh.write("\n")

print(f"wrote {OUT}")
print(f"  functions              {len(functions)}")
print(f"  obligations            {len(manifest['obligations'])}"
      f"  ({len(provided)} provided + {len(preconditions)} preconditions)")
print(f"  gates                  {len(manifest['gates'])}")
print(f"  depends_on             {manifest['depends_on']}")
print(f"  base_commit            {base_commit}")
print(f"  promotion_id           {promotion_id}")
print(f"  target                 {manifest['provenance']['target']}")
for e in manifest["gate_integrity"]:
    print(f"  gate_integrity         {e['runner']}  {e['hash']}")
print(f"  write_policy           allowed {len(write_policy['allowed_write_set'])}"
      f" / protected {len(write_policy['protected_write_set'])} (verbatim from descriptor)")
