#!/usr/bin/env python3
"""Probe 23 (chainlink #23), part 2: the full evidence for the one release route a
schema-valid degradation record buys, and the authoring path for such a record.

Sets up, on a scratch rsync copy, the ONLY state in which 1.1.1 prints
"released under an accepted degradation record" (leg D2) and dumps the real output of
every command that has an opinion about it. Then walks the degradation record's schema
one probe at a time, so every constraint quoted below is a real error message.

Run:  python3 analysis/ligature/probe-23-release-evidence.py
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = "/tmp/opencode/p23"
PRISTINE = os.path.join(SCRATCH, "pristine")
WORK = os.path.join(SCRATCH, "work2")

CLOSURE = "specs/_closure/date-creusot-core.json"
DEGRADATION = "specs/_closure/date-creusot-core.degradation.json"
LEDGER = "ci/results/feature_ledger.json"
WPMAN = "ci/manifest/WP-DATE-CREUSOT.json"

RECORD = {
    "schema_version": "1.0",
    "cluster": "date-creusot-core",
    "failed_conditions": ["generic_callees_type_universal_or_creusot_owned"],
    "affected_edges": ["date::year_month_day::to_days"],
    "ceiling": "per-instantiation",
    "tracking_issue": "chainlink:23",
    "review": {"reviewer": "chainlink-worker", "reviewed_at": "2026-09-30"},
}


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


def put(rel, obj):
    with open(os.path.join(WORK, rel), "w") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")


def ligature(*args, quiet=False):
    p = subprocess.run(
        [sys.executable, "tools/ligature/ligature.pyz", *args],
        cwd=WORK,
        capture_output=True,
        text=True,
    )
    if not quiet:
        print(f"--- $ ligature.pyz {' '.join(args)}   EXIT={p.returncode}")
        print(p.stdout + p.stderr, end="")
        if not (p.stdout + p.stderr).endswith("\n"):
            print()
    return p.returncode, p.stdout + p.stderr


def section(title):
    print()
    print("=" * 100)
    print(f"## {title}")
    print()


def kani_and_corrected_profile():
    """Kani evidence in the cluster, and the closure profile declaring what the
    artifacts actually say (bounded / kani) instead of `deductive` / `creusot`."""
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
    c = load(CLOSURE)
    c["closure_kind"] = "bounded"
    c["conditions"]["owning_verifier"] = "kani"
    save(CLOSURE, c)


def main():
    # ---------------------------------------------------------------- part 1
    section("PART 1 -- the release state: every command's real opinion of it")
    reset()
    kani_and_corrected_profile()
    put(DEGRADATION, RECORD)
    ligature("validate-closure")
    ligature("gate-g14")
    rc, out = ligature("status", quiet=True)
    print(f"--- $ ligature.pyz status   EXIT={rc}")
    for ln in out.splitlines():
        if "cluster date-creusot-core" in ln:
            print(ln.strip())
    rc, out = ligature("status", "--json", quiet=True)
    print(f"--- $ ligature.pyz status --json   EXIT={rc}")
    try:
        st = json.loads(out)
        print(json.dumps(
            {k: st[k] for k in st if k in ("clusters", "cluster", "open_findings")},
            indent=2)[:2000])
    except json.JSONDecodeError:
        print(out[:2000])
    rc, out = ligature("check", "--json", quiet=True)
    print(f"--- $ ligature.pyz check --json   EXIT={rc}")
    try:
        ck = json.loads(out)
        print(json.dumps(ck.get("result", ck), indent=2)[:1200])
        gates = ck.get("gates") or ck.get("results") or []
        for g in (gates if isinstance(gates, list) else []):
            s = json.dumps(g)
            if "g14" in s or "closure" in s:
                print("  g14-ish: " + s[:600])
    except json.JSONDecodeError:
        print(out[:1200])
    ligature("gate", "g14")
    ligature("doctor")
    ligature("write-set-check")

    # ---------------------------------------------------------------- part 2
    section("PART 2 -- authoring path: what a degradation record must contain, one "
            "error message at a time")
    probes = [
        ("filename is the only accepted one: <cluster>.degradation.json",
         dict(RECORD)),
        ("failed_conditions removed", {k: v for k, v in RECORD.items()
                                       if k != "failed_conditions"}),
        ("failed_conditions names a condition key outside the closed enum",
         dict(RECORD, failed_conditions=["not_a_condition"])),
        ("failed_conditions is an empty array", dict(RECORD, failed_conditions=[])),
        ("affected_edges removed", {k: v for k, v in RECORD.items()
                                    if k != "affected_edges"}),
        ("affected_edges empty", dict(RECORD, affected_edges=[])),
        ("ceiling removed", {k: v for k, v in RECORD.items() if k != "ceiling"}),
        ("ceiling outside the enum", dict(RECORD, ceiling="none")),
        ("every ceiling the enum does allow (each must pass G1a unchanged)",
         dict(RECORD, ceiling="documented")),
        ("tracking_issue removed", {k: v for k, v in RECORD.items()
                                    if k != "tracking_issue"}),
        ("tracking_issue is not <tracker>:<id> (this is the shape check)",
         dict(RECORD, tracking_issue="plain text")),
        ("tracking_issue names an issue that does not exist (never checked)",
         dict(RECORD, tracking_issue="chainlink:999999")),
        ("review.reviewer empty", dict(RECORD,
                                       review={"reviewer": "",
                                               "reviewed_at": "2026-09-30"})),
        ("review.reviewed_at is not a date", dict(RECORD,
                                                  review={"reviewer": "r",
                                                          "reviewed_at": "yesterday"})),
        ("one unexpected key", dict(RECORD, surprise=1)),
        ("cluster disagrees with the filename",
         dict(RECORD, cluster="date-creusot-core-core")),
    ]
    for title, rec in probes:
        reset()
        kani_and_corrected_profile()
        put(DEGRADATION, rec)
        rc, out = ligature("validate-closure", quiet=True)
        findings = [ln.strip() for ln in out.splitlines()
                    if "degradation.json:" in ln]
        print(f"[{title}]")
        print(f"    $ ligature.pyz validate-closure   EXIT={rc}")
        for ln in findings:
            print("    " + ln)
        if not findings:
            print("    (no finding on the record itself)")
        print()

    section("PART 2b -- the profile/record agreement rule, both directions")
    for title, mut in [
        ("record names the condition CG3 itself recomputed as unverifiable -> honoured",
         dict(RECORD)),
        ("record names a condition the profile declares as holding -> stale excuse",
         dict(RECORD, failed_conditions=["transitive_assumptions_within_policy"])),
        ("record names CG3 on the healthy creusot cluster, where it is VERIFIED "
         "(chainlink #86's exception)",
         dict(RECORD)),
    ]:
        reset()
        if "healthy" not in title:
            kani_and_corrected_profile()
        put(DEGRADATION, mut)
        print(f"[{title}]")
        ligature("validate-closure")
        ligature("gate-g14")
        print()

    print("=" * 100)
    print("probe-23 part 2 complete")


if __name__ == "__main__":
    main()