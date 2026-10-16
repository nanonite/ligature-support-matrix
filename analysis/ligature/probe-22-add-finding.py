#!/usr/bin/env python3
"""Append the chainlink #22 probe finding to findings/limitations.jsonl, append-only.

Verifies before writing: 17 schema fields, unique id, and that every pre-existing
line is byte-identical afterwards.
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEDGER = os.path.join(PILOT, "findings", "limitations.jsonl")

FIELDS = [
    "id", "pilot", "stage", "command", "tool", "chain", "symptom", "repro_cmd",
    "exit_code", "expected", "actual", "workaround", "severity", "revisit_trigger",
    "pyz_sha256", "tool_path", "tool_version",
]

ENTRY = {
    "id": "date-creusot-056",
    "pilot": "date-creusot",
    "stage": "probe-22-cg3-generic-callees",
    "command": "cd date-creusot && python3 tools/ligature/ligature.pyz gate-g14",
    "tool": "ligature",
    "chain": "new",
    "symptom": (
        "PROBE #22 ANSWER. CG3 generic_callees_type_universal_or_creusot_owned is NOT "
        "declared-not-verified on this pilot under 1.1.1 -- it prints 'VERIFIED from artifact "
        "data, not taken on declaration', and that VERIFIED verdict is unsound. 19 single-mutation "
        "legs on a scratch rsync copy, each reset to a pristine snapshot first, reduce the whole "
        "condition to a two-part cluster-level proxy: VERIFIED iff (a) every work package NAMED in "
        "the closure profile's work_packages list has at least one achieved-assurance record, and "
        "(b) no achieved record in that closure -- obligation OR bridge -- has "
        "evidence.kind == 'kani-bounded-model-check'. Nothing else is read. Four consequences, each "
        "reproduced at gate-g14 exit 0 with the VERIFIED line printed: "
        "(1) FALSE PREMISE, the gate states the premise it just falsified: deleting 1 of 5 achieved "
        "records blocks the cluster for exactly that gap while CG3 still prints 'every work package in "
        "the closure has a recorded achievement' and 'VERIFIED'. "
        "(2) WRONG DISJUNCT: the condition is 'type_universal_or_CREUSOT_owned', but the derivation "
        "only establishes the negative of 'Kani-owned'. Relabelling all five records "
        "creusot-deductive-check -> verus-deductive-check still prints VERIFIED, so a VERUS-owned "
        "cluster is reported as having verified the 'creusot_owned' disjunct. "
        "(3) BLIND TO DEPENDENCIES: a Kani-owned work package whose only function is a generic "
        "(date::util::generic_helper), schema-valid, with its own Kani assurance report, is missed "
        "unless the closure profile names it. gate-g14 never mentions it (0 occurrences of its id) "
        "and exits 0 with VERIFIED -- and the worst case is a Creusot work package that DECLARES "
        "depends_on that Kani package plus a coupling note saying a Creusot-verified function calls "
        "a generic whose only assurance is a Kani bounded model check over one monomorphization. "
        "The gate then certifies as verified 'no generic callee it rests on is Kani-owned' while a "
        "project artifact states the opposite. "
        "(4) THE FIRST DISJUNCT IS UNREPRESENTABLE: no field in any artifact can declare a generic "
        "callee, its type-universality, or its monomorphizations. Adding "
        "generic_callees: [{callee, type_universal, monomorphizations_proved}] is rejected with "
        "'Additional properties are not allowed' by BOTH the assurance-report schema and the "
        "work-package-manifest schema, and the only occurrence of the string 'generic' anywhere in "
        "specs/, ci/ and project-descriptor.json is the condition key itself. So 'type_universal' is "
        "never evaluated by anything, at any severity -- and the recommended escape route ('releasing "
        "this cluster needs a degradation record naming this condition with a tracking issue') still "
        "has no authoring path. The gate's own other phrasing calls this 'a capability gap, not a "
        "checked condition (plan.md §3)', which its own VERIFIED phrasing contradicts."
    ),
    "repro_cmd": (
        "cd date-creusot && python3 analysis/ligature/probe-22-legs.py && echo '--- the two false-VERIFIED legs, by hand ---' "
        "&& rm -rf /tmp/p22 && mkdir -p /tmp/p22 && rsync -a --exclude upstream/ --exclude target/ ./ /tmp/p22/ && cd /tmp/p22 && "
        "python3 - <<'EOF'\n"
        "import json\n"
        "wp=json.load(open('ci/manifest/WP-DATE-CREUSOT.json'))\n"
        "k=dict(wp, work_package='WP-KANI-OTHER', issue='chainlink:22', functions=['date::util::generic_helper'],\n"
        "       obligations=['Other.C1'], coupling_notes=wp['coupling_notes']+['date::year_month_day::to_days calls date::util::generic_helper, whose only assurance is a Kani bounded model check over the i64 monomorphization.'], depends_on=['WP-DATE-CREUSOT-CORE','WP-KANI-OTHER'])\n"
        "k['definition_of_done']={'provided_guarantees':[{'obligation_id':'Other.C1','required_assurance':{'required_claims':['postcondition-holds'],'accepted_evidence_kinds':['kani-bounded-model-check']},'harness':'kani'}],'required_preconditions_to_establish':[],'required_guarantees':[],'trusted_assumptions':[]}\n"
        "k['report']['emit']='ci/results/kani_other_ledger.json'\n"
        "json.dump(k,open('ci/manifest/WP-KANI-OTHER.json','w'),indent=2)\n"
        "rec={'schema_version':'1.0','claim':{'kind':'postcondition-holds','result':'pass'},'config':{'toolchain':'cargo-kani','target':'x86_64-unknown-linux-gnu','features':['default']},'evidence':{'kind':'kani-bounded-model-check','verifier':'kani','harness':'kani','scope':{'proof_targets':'rust/date-creusot-core/verif/other/proof.json'}},'support':{'status':'supported'},'trust':{'assumptions':[]}}\n"
        "json.dump({'schema_version':'1.0','work_package':'WP-KANI-OTHER','bridge_records':[],'obligation_records':[{'obligation_id':'Other.C1','record':rec}]},open('ci/results/kani_other_ledger.json','w'),indent=2)\n"
        "EOF\n"
        "python3 tools/ligature/ligature.pyz gate-g14; echo \"EXIT=$? (0 expected, CG3 says VERIFIED)\"\n"
        "python3 tools/ligature/ligature.pyz gate-g14 2>&1 | grep -c WP-KANI-OTHER"
    ),
    "exit_code": 0,
    "expected": (
        "Per plan.md §3 the condition should be reported as declared-not-verified -- an explicit "
        "capability gap, since no artifact carries type information. If 1.1.1 instead reports it "
        "verified, the verdict must rest on something that actually bears on the condition: that "
        "every generic callee the closure rests on is shown to be type-universal, or shown to be "
        "owned by a deductive verifier, and a Kani-owned or non-type-universal generic callee must "
        "be caught even when it is reached through a declared dependency or sits in a work package "
        "the closure profile does not name."
    ),
    "actual": (
        "gate-g14 exits 0 and prints, for a closure whose Creusot work package depends on a Kani-owned "
        "generic-callee work package: 'generic_callees_type_universal_or_creusot_owned is VERIFIED from "
        "artifact data, not taken on declaration: every work package in the closure has a recorded "
        "achievement and none of them is a Kani result ([\'creusot-deductive-check\']) -- with no "
        "per-monomorphization assurance anywhere in the closure, no generic callee it rests on is "
        "Kani-owned (CG3, plan.md §3)'. The word Kani-OWNED in the conclusion is the whole condition's "
        "load-bearing content, and the derivation is only 'no record in the closure carries the Kani kind "
        "string'. gate-g14 output contains 0 occurrences of WP-KANI-OTHER. The 'declared-not-verified' "
        "phrasing the issue title expects still exists in 1.1.1 but is reachable only from three other "
        "states (no record at all / a Kani kind inside the closure / no work package in the closure), not "
        "from this pilot's own state."
    ),
    "workaround": (
        "Do not read the CG3 VERIFIED line as evidence about generics. For this cluster it is a "
        "statement that the closure is single-verifier and Creusot-owned, which the CG1/CG17 findings "
        "already say; the generic-callee question is unverified and the Kani-dependency case (C5) is "
        "unreached by any gate. Manual control until the artifact model can carry a generic callee's "
        "type-universality: grep the work-package manifests for depends_on entries and coupling_notes, "
        "and check by hand that no Creusot-verified function calls a generic whose only assurance is a "
        "Kani bounded model check. Relief in-pilot is a degradation record naming this condition -- but "
        "that has no authoring path (already date-ligature-040), so the declared-not-verified route is "
        "not actually available. Cross-reference epic #1 #85, whose 1.1.1 re-verification comment "
        "records VERDICT: FIXED; that verdict does not survive leg C5, B7 or B2."
    ),
    "severity": "blocker",
    "revisit_trigger": (
        "Any ligature release that (a) adds a generic-callee / type-universality / "
        "monomorphization field to the work-package-manifest or assurance-report schema, or (b) "
        "changes the CG3 derivation to walk depends_on and to require a deductive verifier rather "
        "than merely a non-Kani one. Re-run analysis/ligature/probe-22-legs.py; all 19 legs are "
        "expected to keep their exit codes, so a change in the CG3 verdict table is the signal."
    ),
    "pyz_sha256": "3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4",
    "tool_path": "date-creusot/tools/ligature/ligature.pyz",
    "tool_version": "1.1.1 (content hash sha256:172a87a8be8406d625b57b1aa96dc8cb76756e615983d8da70aa298892964558)",
}


def main():
    before = open(LEDGER, "rb").read()
    before_lines = before.decode().splitlines()
    for ln in before_lines:
        if ln.strip():
            json.loads(ln)
    ids = [json.loads(ln)["id"] for ln in before_lines if ln.strip()]
    assert len(ids) == len(set(ids)), "pre-existing duplicate ids"
    assert ENTRY["id"] not in ids, f"{ENTRY['id']} already present"
    missing = [f for f in FIELDS if f not in ENTRY]
    assert not missing, f"missing schema fields: {missing}"
    extra = [k for k in ENTRY if k not in FIELDS]
    assert not extra, f"unknown schema fields: {extra}"
    assert isinstance(ENTRY["exit_code"], int)
    assert ENTRY["severity"] in ("blocker", "scope-cut", "friction")
    assert ENTRY["tool"] in ("ligature", "creusot", "verus", "kani", "nextest", "rdb", "mcp", "oracle")
    assert ENTRY["chain"] in ("A.x", "B.x", "C.n", "new")

    with open(LEDGER, "a") as f:
        f.write(json.dumps(ENTRY, sort_keys=True) + "\n")

    after = open(LEDGER, "rb").read()
    assert after.startswith(before), "APPEND-ONLY VIOLATED: prior bytes changed"
    after_lines = after.decode().splitlines()
    new_ids = [json.loads(ln)["id"] for ln in after_lines if ln.strip()]
    print(f"append-only OK: first {len(before_lines)} lines byte-identical")
    print(f"lines {len(before_lines)} -> {len(after_lines)}")
    print(f"unique ids: {len(set(new_ids))} of {len(new_ids)}")
    print(f"appended id: {ENTRY['id']}  severity={ENTRY['severity']}  fields={len(ENTRY)}/17")
    print(f"ledger sha256 before: {hashlib.sha256(before).hexdigest()[:16]}")
    print(f"ledger sha256 after:  {hashlib.sha256(after).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
