#!/usr/bin/env python3
"""Probe 22 (chainlink #22): what does CG3
`generic_callees_type_universal_or_creusot_owned` actually check under ligature 1.1.1?

Every leg resets a scratch rsync copy to pristine, applies exactly one mutation, and
reports the CG3 line(s) plus the command's real exit code. Nothing here touches the
real pilot root.

Run:  python3 analysis/ligature/probe-22-legs.py
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRATCH = "/tmp/opencode/p22"
PRISTINE = os.path.join(SCRATCH, "pristine")
WORK = os.path.join(SCRATCH, "work")

CLOSURE = "specs/_closure/date-creusot-core.json"
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


def ligature(*args, cwd=None):
    p = subprocess.run(
        [sys.executable, "tools/ligature/ligature.pyz", *args],
        cwd=cwd or WORK,
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


def cg3_lines(out):
    return [ln.strip() for ln in out.splitlines() if "generic_callees" in ln]


# --------------------------------------------------------------------------
# mutations
# --------------------------------------------------------------------------
def m_none(w):
    pass


def m_del_all_records(w):
    d = load(LEDGER)
    d["obligation_records"] = []
    save(LEDGER, d)


def m_del_one_record(w):
    d = load(LEDGER)
    d["obligation_records"] = [r for r in d["obligation_records"] if r["obligation_id"] != "Weekday.C1"]
    save(LEDGER, d)


def m_cond_false(w):
    d = load(CLOSURE)
    d["conditions"]["generic_callees_type_universal_or_creusot_owned"] = False
    save(CLOSURE, d)


def m_cond_removed(w):
    d = load(CLOSURE)
    del d["conditions"]["generic_callees_type_universal_or_creusot_owned"]
    save(CLOSURE, d)


def m_cond_string(w):
    d = load(CLOSURE)
    d["conditions"]["generic_callees_type_universal_or_creusot_owned"] = "yes"
    save(CLOSURE, d)


def m_all_kani(w):
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "kani-bounded-model-check"
    save(LEDGER, d)


def m_all_verus(w):
    """A Verus-owned cluster. Is 'Verus' a Kani result?  Is a Verus-owned
    generic callee covered by CG3's 'creusot_owned' disjunct?"""
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "verus-deductive-check"
        r["record"]["evidence"]["verifier"] = "verus"
        r["record"]["evidence"]["harness"] = "verus"
    save(LEDGER, d)


def m_bounded_kani(w):
    """A genuinely Kani-owned bounded cluster -- the case CG3 exists for:
    Kani can only prove enumerated monomorphizations."""
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "kani-bounded-model-check"
        r["record"]["evidence"]["verifier"] = "kani"
        r["record"]["evidence"]["harness"] = "kani"
    save(LEDGER, d)
    c = load(CLOSURE)
    c["closure_kind"] = "bounded"
    c["conditions"]["owning_verifier"] = "kani"
    save(CLOSURE, c)
    m = load(WPMAN)
    for g in m["definition_of_done"]["provided_guarantees"]:
        g["required_assurance"]["accepted_evidence_kinds"] = ["kani-bounded-model-check"]
        g["harness"] = "kani"
    save(WPMAN, m)


def m_mixed_one_kani(w):
    """One obligation in five is Kani-owned; the rest Creusot-owned.  The
    cluster stays deductive, so G17 blocks -- but does CG3 name WHICH
    obligation/callee is Kani-owned, or only that 'a Kani result' exists?"""
    d = load(LEDGER)
    d["obligation_records"][3]["record"]["evidence"]["kind"] = "kani-bounded-model-check"
    save(LEDGER, d)


def m_generic_field_in_ledger(w):
    """Attempt 1: declare a generic callee and its type-universality in the
    ledger, the natural home for per-obligation genericity."""
    d = load(LEDGER)
    d["generic_callees"] = [
        {
            "callee": "date::util::generic_helper",
            "type_universal": False,
            "monomorphizations_proved": ["i64"],
        }
    ]
    save(LEDGER, d)


def m_generic_field_in_wpm(w):
    """Attempt 2: declare the same thing in the work-package manifest."""
    m = load(WPMAN)
    m["generic_callees"] = [
        {
            "callee": "date::util::generic_helper",
            "type_universal": False,
            "monomorphizations_proved": ["i64"],
        }
    ]
    save(WPMAN, m)


def _kani_other_wp(w):
    """A second, schema-valid, Kani-owned work package whose only function is a
    generic one.  It is NOT named by the closure profile's work_packages list."""
    wp = load(WPMAN)
    wp["work_package"] = "WP-KANI-OTHER"
    wp["issue"] = "chainlink:22"
    wp["functions"] = ["date::util::generic_helper"]
    wp["obligations"] = ["Other.C1"]
    wp["definition_of_done"]["provided_guarantees"] = [
        {
            "obligation_id": "Other.C1",
            "required_assurance": {
                "required_claims": ["postcondition-holds"],
                "accepted_evidence_kinds": ["kani-bounded-model-check"],
            },
            "harness": "kani",
        }
    ]
    wp["report"]["emit"] = "ci/results/kani_other_ledger.json"
    save("ci/manifest/WP-KANI-OTHER.json", wp)
    other = {
        "schema_version": "1.0",
        "work_package": "WP-KANI-OTHER",
        "bridge_records": [],
        "obligation_records": [
            {
                "obligation_id": "Other.C1",
                "record": {
                    "schema_version": "1.0",
                    "claim": {"kind": "postcondition-holds", "result": "pass"},
                    "config": {
                        "toolchain": "cargo-kani",
                        "target": "x86_64-unknown-linux-gnu",
                        "features": ["default"],
                    },
                    "evidence": {
                        "kind": "kani-bounded-model-check",
                        "verifier": "kani",
                        "harness": "kani",
                        "scope": {
                            "proof_targets": "rust/date-creusot-core/verif/other/proof.json"
                        },
                    },
                    "support": {"status": "supported"},
                    "trust": {"assumptions": []},
                },
            }
        ],
    }
    save("ci/results/kani_other_ledger.json", other)


def m_kani_owned_outside_closure(w):
    """A Kani-owned generic-callee work package that the closure profile does
    not name.  Caught, or is CG3's scan limited to the cluster?"""
    _kani_other_wp(w)


def m_kani_owned_named_in_closure(w):
    """Control for the leg above: the SAME Kani-owned generic-callee WP, but
    added to the closure profile's work_packages list."""
    _kani_other_wp(w)
    c = load(CLOSURE)
    c["work_packages"] = ["WP-DATE-CREUSOT", "WP-KANI-OTHER"]
    save(CLOSURE, c)


def m_kani_verifier_non_kani_kind(w):
    """Records that say verifier=kani and harness=kani, but whose evidence.kind
    is a non-Kani string.  Does CG3 read `kind` only, or verifier/harness too?"""
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "exhaustive-model-check"
        r["record"]["evidence"]["verifier"] = "kani"
        r["record"]["evidence"]["harness"] = "kani"
        r["record"]["config"]["toolchain"] = "cargo-kani"
    save(LEDGER, d)
    m = load(WPMAN)
    for g in m["definition_of_done"]["provided_guarantees"]:
        g["required_assurance"]["accepted_evidence_kinds"] = ["exhaustive-model-check"]
        g["harness"] = "kani"
    save(WPMAN, m)


def m_kani_kind_unspelled(w):
    """A genuinely Kani-owned BOUNDED cluster whose kind string does not contain
    the word 'kani'.  Shows the test is the literal kind string."""
    d = load(LEDGER)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["kind"] = "bounded-model-checking"
        r["record"]["evidence"]["verifier"] = "kani"
        r["record"]["evidence"]["harness"] = "kani"
    save(LEDGER, d)
    m = load(WPMAN)
    for g in m["definition_of_done"]["provided_guarantees"]:
        g["required_assurance"]["accepted_evidence_kinds"] = ["bounded-model-checking"]
        g["harness"] = "kani"
    save(WPMAN, m)
    c = load(CLOSURE)
    c["closure_kind"] = "bounded"
    c["conditions"]["owning_verifier"] = "kani"
    save(CLOSURE, c)


def m_kani_kind_in_manifest_only(w):
    """The WP's accepted_evidence_kinds permits Kani, but the recorded
    achievement is Creusot.  Does CG3 read the manifest's accepted kinds?"""
    m = load(WPMAN)
    for g in m["definition_of_done"]["provided_guarantees"]:
        g["required_assurance"]["accepted_evidence_kinds"] = [
            "creusot-deductive-check",
            "kani-bounded-model-check",
        ]
    save(WPMAN, m)


def m_kani_owned_as_dependency(w):
    """The realistic shape, and the sharpest result: the Creusot work package
    DECLARES that it depends on a Kani-owned work package whose only function is
    a generic, with a coupling note naming the Kani-owned generic callee.  The
    closure profile names only the Creusot WP, as it must if the cluster is to be
    a single-verifier deductive closure."""
    _kani_other_wp(w)
    m = load(WPMAN)
    m["depends_on"] = ["WP-DATE-CREUSOT-CORE", "WP-KANI-OTHER"]
    m["coupling_notes"] = m["coupling_notes"] + [
        "date::year_month_day::to_days calls date::util::generic_helper, whose "
        "only assurance is a Kani bounded model check over the i64 monomorphization."
    ]
    save(WPMAN, m)


def m_kani_in_bridge_records(w):
    """A Kani-owned generic callee recorded in bridge_records rather than
    obligation_records.  Does CG3 scan bridges at all?"""
    d = load(LEDGER)
    d["bridge_records"] = [
        {
            "bridge_id": "BR-1",
            "record": {
                "schema_version": "1.0",
                "claim": {"kind": "postcondition-holds", "result": "pass"},
                "config": {"toolchain": "cargo-kani", "target": "x86_64-unknown-linux-gnu", "features": ["default"]},
                "evidence": {
                    "kind": "kani-bounded-model-check",
                    "verifier": "kani",
                    "harness": "kani",
                    "scope": {"proof_targets": "rust/date-creusot-core/verif/other/proof.json"},
                },
                "support": {"status": "supported"},
                "trust": {"assumptions": []},
            },
        }
    ]
    save(LEDGER, d)


LEGS = [
    ("A0", "baseline (no mutation)", m_none),
    ("B1", "delete ALL 5 achieved-assurance records", m_del_all_records),
    ("B2", "delete 1 of 5 achieved-assurance records (Weekday.C1)", m_del_one_record),
    ("B3", "conditions.CG3 declared false", m_cond_false),
    ("B4", "conditions.CG3 key removed from the profile", m_cond_removed),
    ("B5", "conditions.CG3 declared as the string \"yes\"", m_cond_string),
    ("B6", "all 5 records relabelled kani-bounded-model-check (deductive)", m_all_kani),
    ("B7", "all 5 records relabelled verus-deductive-check", m_all_verus),
    ("B8", "Kani-owned BOUNDED cluster (5 records kani, closure_kind=bounded)", m_bounded_kani),
    ("B9", "1 of 5 records kani, rest creusot (deductive)", m_mixed_one_kani),
    ("B10", "declare a generic callee in the ledger (type_universal: false)", m_generic_field_in_ledger),
    ("B11", "declare a generic callee in the work-package manifest", m_generic_field_in_wpm),
    ("B12", "WP manifest accepts BOTH creusot and kani kinds; record is creusot", m_kani_kind_in_manifest_only),
    ("C1", "Kani-owned generic-callee WP NOT named by the closure profile", m_kani_owned_outside_closure),
    ("C2", "control: that Kani-owned generic-callee WP IS named by the closure", m_kani_owned_named_in_closure),
    ("C3", "records say verifier=kani/harness=kani, kind=exhaustive-model-check", m_kani_verifier_non_kani_kind),
    ("C4", "Kani-owned BOUNDED cluster, kind string 'bounded-model-checking' (no 'kani')", m_kani_kind_unspelled),
    ("C5", "Creusot WP depends_on a Kani-owned generic-callee WP (not in closure list)", m_kani_owned_as_dependency),
    ("C6", "Kani-owned record in bridge_records instead of obligation_records", m_kani_in_bridge_records),
]

CMDS = [("gate-g14",), ("validate-closure",), ("status",)]


def main():
    only = sys.argv[1:]
    for lid, desc, fn in LEGS:
        if only and lid not in only:
            continue
        reset()
        fn(WORK)
        print("=" * 100)
        print(f"### {lid}: {desc}")
        for cmd in CMDS:
            rc, out = ligature(*cmd)
            print(f"--- $ ligature.pyz {' '.join(cmd)}   EXIT={rc}")
            lines = cg3_lines(out)
            if lines:
                for ln in lines:
                    print("    CG3> " + ln)
            else:
                print("    CG3> (no CG3 line emitted)")
            # also surface the other notable findings
            for ln in out.splitlines():
                s = ln.strip()
                if any(k in s for k in ("G17/", "G14/error", "G14/warn", "Kani result", "declared as", "VERIFIED")):
                    if "generic_callees" not in s:
                        print("    other> " + s)
            if cmd[0] == "status":
                for ln in out.splitlines():
                    if "cluster date-creusot-core" in ln:
                        print("    status> " + ln.strip())
        print()


if __name__ == "__main__":
    main()
