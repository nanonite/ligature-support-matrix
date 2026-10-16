#!/usr/bin/env python3
"""Probe 23 (chainlink #23): Kani evidence inside a deductive cluster -> G17 + the
degradation-record route.

Every leg resets a scratch rsync copy to pristine, applies exactly one mutation, and
reports the real exit code plus every closure-relevant line the binary prints. Nothing
here touches the live pilot root, and no `draft` / `approve` / `promote-evidence` /
`record-assurance` / `record-ruling` / `accept-promotion` / `init` is ever invoked.

Run:  python3 analysis/ligature/probe-23-legs.py            # every leg
      python3 analysis/ligature/probe-23-legs.py D0 D2     # only these legs
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRATCH = "/tmp/opencode/p23"
PRISTINE = os.path.join(SCRATCH, "pristine")
WORK = os.path.join(SCRATCH, "work")

CLOSURE = "specs/_closure/date-creusot-core.json"
DEGRADATION = "specs/_closure/date-creusot-core.degradation.json"
LEDGER = "ci/results/feature_ledger.json"
WPMAN = "ci/manifest/WP-DATE-CREUSOT.json"


def _chmod_writable(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            try:
                os.chmod(os.path.join(dirpath, d), 0o777)
            except OSError:
                pass
        for f in filenames:
            try:
                os.chmod(os.path.join(dirpath, f), 0o666)
            except OSError:
                pass


def reset():
    if os.path.exists(WORK):
        _chmod_writable(WORK)
        shutil.rmtree(WORK)
    shutil.copytree(PRISTINE, WORK)
    _chmod_writable(WORK)


def load(rel):
    with open(os.path.join(WORK, rel)) as f:
        return json.load(f)


def save(rel, obj):
    with open(os.path.join(WORK, rel), "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def put(rel, text):
    with open(os.path.join(WORK, rel), "w") as f:
        f.write(text)


def ligature(*args):
    p = subprocess.run(
        [sys.executable, "tools/ligature/ligature.pyz", *args],
        cwd=WORK,
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------
def kani_evidence(w):
    """Put a genuine `kani-bounded-model-check` inside the cluster: the work package's
    own required_profile accepts it and every achieved record carries it."""
    m = load(WPMAN)
    for g in m["definition_of_done"]["provided_guarantees"]:
        g["required_assurance"]["accepted_evidence_kinds"] = ["kani-bounded-model-check"]
        g["harness"] = "kani"
    save(WPMAN, m)
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "kani-bounded-model-check"
        r["record"]["evidence"]["verifier"] = "kani"
        r["record"]["evidence"]["harness"] = "kani"
    save(LEDGER, d)


def profile_matches_artifacts(w):
    """Declare what the artifacts actually say: a Kani cluster is `bounded`, owned by
    kani.  (The issue's premise is `deductive`; this is the corrected profile.)"""
    c = load(CLOSURE)
    c["closure_kind"] = "bounded"
    c["conditions"]["owning_verifier"] = "kani"
    save(CLOSURE, c)


def record(**over):
    rec = {
        "schema_version": "1.0",
        "cluster": "date-creusot-core",
        "failed_conditions": ["generic_callees_type_universal_or_creusot_owned"],
        "affected_edges": ["date::year_month_day::to_days"],
        "ceiling": "per-instantiation",
        "tracking_issue": "chainlink:23",
        "review": {"reviewer": "chainlink-worker", "reviewed_at": "2026-09-30"},
    }
    rec.update(over)
    return json.dumps(rec, indent=2) + "\n"


# --------------------------------------------------------------------------
# legs
# --------------------------------------------------------------------------
def m_none(w):
    pass


def m_kani_no_record(w):
    """THE ISSUE'S CASE: Kani evidence inside a cluster still declared `deductive`."""
    kani_evidence(w)


def m_kani_deductive_plus_record(w):
    kani_evidence(w)
    put(DEGRADATION, record())


def m_kani_bounded_plus_record(w):
    """Kani evidence + the profile corrected to what the artifacts say + the record."""
    kani_evidence(w)
    profile_matches_artifacts(w)
    put(DEGRADATION, record())


def m_kani_bounded_no_record(w):
    kani_evidence(w)
    profile_matches_artifacts(w)


def m_kani_bounded_record_other_condition(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(failed_conditions=["transitive_assumptions_within_policy"]))


def m_kani_bounded_record_empty_failed(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(failed_conditions=[]))


def m_kani_bounded_record_unknown_condition(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(failed_conditions=["no_such_condition"]))


def m_kani_bounded_record_no_tracking_issue(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(tracking_issue=""))


def m_kani_bounded_record_other_cluster(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(cluster="some-other-cluster"))


def m_kani_bounded_record_top_ceiling(w):
    """Is `ceiling` checked for plausibility, or is any enum value accepted?"""
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(ceiling="human-risk-acceptance"))


def m_kani_bounded_record_lowest_ceiling(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(ceiling="documented"))


def m_kani_bounded_record_invented_edges(w):
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(affected_edges=["not-a-real-call-edge", "also-invented"]))


def m_kani_bounded_two_records(w):
    m_kani_bounded_plus_record(w)
    put(
        "specs/_closure/date-creusot-core.2.degradation.json",
        record(failed_conditions=["transitive_assumptions_within_policy"]),
    )


def m_kani_bounded_wrong_filename(w):
    """Which filenames dispatch to the degradation-record schema?"""
    m_kani_bounded_plus_record(w)
    os.remove(os.path.join(WORK, DEGRADATION))
    put("specs/_closure/degradation-date-creusot-core.json", record())


def m_kani_bounded_alt_filename_degradation(w):
    m_kani_bounded_plus_record(w)
    os.remove(os.path.join(WORK, DEGRADATION))
    put("specs/_closure/zzz.json", record())


def m_stale_excuse_creusot_cluster(w):
    """The live Creusot cluster, where CG3 is VERIFIED. Is a CG3 record a stale
    excuse here? (chainlink #86 calls the CG3 record a 'tracking record'.)"""
    put(DEGRADATION, record())


def m_invalid_record_plus_mismatch(w):
    """A schema-INVALID degradation record beside a declared/computed mismatch."""
    c = load(CLOSURE)
    c["conditions"]["unresolved_indirect_calls_at_or_above_medium"] = 3
    save(CLOSURE, c)
    put(DEGRADATION, '{"failed_conditions": "not-an-array"}\n')


def m_invalid_record_only(w):
    """A schema-INVALID degradation record on the healthy live cluster."""
    put(DEGRADATION, '{"failed_conditions": "not-an-array"}\n')


def m_kani_deductive_invalid_record(w):
    kani_evidence(w)
    put(DEGRADATION, '{"failed_conditions": "not-an-array"}\n')


def m_kani_bounded_invalid_record(w):
    kani_evidence(w)
    profile_matches_artifacts(w)
    put(DEGRADATION, '{"failed_conditions": "not-an-array"}\n')


def m_declared_count_mismatch_no_record(w):
    """Control for m_invalid_record_plus_mismatch: same mismatch, NO record file."""
    c = load(CLOSURE)
    c["conditions"]["unresolved_indirect_calls_at_or_above_medium"] = 3
    save(CLOSURE, c)


def m_declared_bool_false_plus_record(w):
    """A boolean condition declared false where the computation says true, plus a
    matching record. Can a record excuse a recompute mismatch?"""
    c = load(CLOSURE)
    c["conditions"]["single_verifier_system"] = False
    save(CLOSURE, c)
    put(DEGRADATION, record(failed_conditions=["single_verifier_system"]))


def _mismatch(w):
    """The only blocking finding on this pilot that G17 raises: a declared count the
    computation contradicts."""
    c = load(CLOSURE)
    c["conditions"]["unresolved_indirect_calls_at_or_above_medium"] = 3
    save(CLOSURE, c)


def m_e2_valid_record(w):
    """E2: mismatch + a FULLY VALID, matching record -> G17 still blocks."""
    _mismatch(w)
    put(DEGRADATION, record(failed_conditions=["unresolved_indirect_calls_at_or_above_medium"]))


def m_e3_invalid_one_field(w):
    """E3: mismatch + a record that is invalid in exactly ONE field (failed_conditions
    is a string, so it names nothing at all) but still carries `cluster`."""
    _mismatch(w)
    r = json.loads(record())
    r["failed_conditions"] = "x"
    put(DEGRADATION, json.dumps(r, indent=2) + "\n")


def m_e4_invalid_extra_key(w):
    """E4: mismatch + an otherwise-valid record carrying one unexpected key."""
    _mismatch(w)
    r = json.loads(record())
    r["failed_conditions"] = ["unresolved_indirect_calls_at_or_above_medium"]
    r["surprise"] = 1
    put(DEGRADATION, json.dumps(r, indent=2) + "\n")


def m_e5_invalid_no_cluster_key(w):
    """E5: mismatch + a record missing `cluster`, so it cannot be associated."""
    _mismatch(w)
    put(DEGRADATION, '{"schema_version": "1.0", "failed_conditions": ["x"]}\n')


def m_e6_invented_tracking_issue(w):
    """E6: a syntactically valid tracking_issue that names nothing."""
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(tracking_issue="chainlink:999999"))


def m_e7_record_review_self_signed(w):
    """E7: `review` is a plain free-text block -- is any provenance checked?"""
    m_kani_bounded_plus_record(w)
    put(DEGRADATION, record(review={"reviewer": "", "reviewed_at": "not-a-date"}))


LEG_DEFS = [
    ("A0", "baseline, live Creusot state, no mutation", m_none),
    ("D0", "Kani evidence inside the DEDUCTIVE cluster, no degradation record",
     m_kani_no_record),
    ("D1", "Kani-in-deductive + schema-valid CG3 record w/ tracking issue",
     m_kani_deductive_plus_record),
    ("D2", "Kani-in-boundEd (profile corrected) + CG3 record  <- the release route",
     m_kani_bounded_plus_record),
    ("D3", "control: corrected profile, NO record", m_kani_bounded_no_record),
    ("D4", "record names a different condition than the one that failed",
     m_kani_bounded_record_other_condition),
    ("D5", "record with failed_conditions: [] (nothing declared failed)",
     m_kani_bounded_record_empty_failed),
    ("D6", "record names a condition key that does not exist",
     m_kani_bounded_record_unknown_condition),
    ("D7", "record with tracking_issue: \"\"", m_kani_bounded_record_no_tracking_issue),
    ("D8", "record whose cluster is some-other-cluster",
     m_kani_bounded_record_other_cluster),
    ("D9", "record ceiling=human-risk-acceptance (top of the enum)",
     m_kani_bounded_record_top_ceiling),
    ("D10", "record ceiling=documented (bottom of the enum)",
     m_kani_bounded_record_lowest_ceiling),
    ("D11", "record affected_edges are invented strings",
     m_kani_bounded_record_invented_edges),
    ("D12", "two degradation records for the same cluster", m_kani_bounded_two_records),
    ("D13", "same record content at degradation-date-creusot-core.json",
     m_kani_bounded_wrong_filename),
    ("D14", "same record content at zzz.json", m_kani_bounded_alt_filename_degradation),
    ("D15", "CG3 record on the HEALTHY Creusot cluster (stale excuse?)",
     m_stale_excuse_creusot_cluster),
    ("D16", "declared/computed count mismatch + schema-INVALID record",
     m_invalid_record_plus_mismatch),
    ("D17", "control: same mismatch, NO record file", m_declared_count_mismatch_no_record),
    ("D18", "schema-INVALID record on the healthy cluster", m_invalid_record_only),
    ("D19", "Kani-in-deductive + schema-INVALID record",
     m_kani_deductive_invalid_record),
    ("D20", "Kani-in-boundEd + schema-INVALID record", m_kani_bounded_invalid_record),
    ("D21", "bool condition declared false + matching record (recompute mismatch)",
     m_declared_bool_false_plus_record),
    ("E2", "recompute mismatch + FULLY VALID matching record", m_e2_valid_record),
    ("E3", "recompute mismatch + record invalid in ONE field, still carries cluster",
     m_e3_invalid_one_field),
    ("E4", "recompute mismatch + record invalid on one extra key, matching condition",
     m_e4_invalid_extra_key),
    ("E5", "recompute mismatch + record with no cluster key at all",
     m_e5_invalid_no_cluster_key),
    ("E6", "tracking_issue names a chainlink issue that does not exist",
     m_e6_invented_tracking_issue),
    ("E7", "review block is empty/self-asserted (reviewer '', reviewed_at 'not-a-date')",
     m_e7_record_review_self_signed),
]

CMDS = [("validate-closure",), ("gate-g14",), ("status",)]


def main():
    only = sys.argv[1:]
    for lid, desc, fn in LEG_DEFS:
        if only and lid not in only:
            continue
        reset()
        fn(WORK)
        print("=" * 100)
        print(f"### {lid}: {desc}")
        for cmd in CMDS:
            rc, out = ligature(*cmd)
            print(f"--- $ ligature.pyz {' '.join(cmd)}   EXIT={rc}")
            for ln in out.splitlines():
                s = ln.strip()
                if not s:
                    continue
                keep = False
                if cmd[0] == "status":
                    keep = "cluster date-creusot-core" in s
                elif (
                    s.startswith("cluster ")
                    or s.startswith("OK:")
                    or s.startswith("FAIL:")
                    or "G17/" in s
                    or "G14/" in s
                    or "G1a/" in s
                    or "G1b/" in s
                    or s.startswith("closure is a per-cluster")
                ):
                    keep = True
                if keep:
                    tag = {"validate-closure": "vc", "gate-g14": "g14", "status": "st"}[cmd[0]]
                    print(f"    {tag}> {s}")
            print()
    print("=" * 100)
    print("all legs complete")


if __name__ == "__main__":
    main()