#!/usr/bin/env python3
"""Append the chainlink #23 probe finding to findings/limitations.jsonl, append-only.

Verifies before writing: 17 schema fields, unique id, enum membership, and that every
pre-existing line is byte-identical afterwards. The `repro_cmd` it writes was run
verbatim in the same session -- see the "run this" block below.

Run:  python3 analysis/ligature/probe-23-add-finding.py          # append
      python3 analysis/ligature/probe-23-add-finding.py --show   # print, don't write
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEDGER = os.path.join(PILOT, "findings", "limitations.jsonl")

FIELDS = [
    "id", "pilot", "stage", "command", "tool", "chain", "symptom", "repro_cmd",
    "exit_code", "expected", "actual", "workaround", "severity", "revisit_trigger",
    "pyz_sha256", "tool_path", "tool_version",
]

_REPRO = """cd date-creusot && rm -rf /tmp/p23r && mkdir -p /tmp/p23r && rsync -a --exclude upstream/ --exclude target/ ./ /tmp/p23r/ && cd /tmp/p23r && python3 - <<'EOF'
import json
# 1. put a genuine kani-bounded-model-check inside the cluster
wp=json.load(open('ci/manifest/WP-DATE-CREUSOT.json'))
for g in wp['definition_of_done']['provided_guarantees']:
    g['required_assurance']['accepted_evidence_kinds']=['kani-bounded-model-check']; g['harness']='kani'
json.dump(wp,open('ci/manifest/WP-DATE-CREUSOT.json','w'),indent=2)
led=json.load(open('ci/results/feature_ledger.json'))
for r in led['obligation_records']:
    r['record']['evidence']['kind']='kani-bounded-model-check'
    r['record']['evidence']['verifier']='kani'; r['record']['evidence']['harness']='kani'
json.dump(led,open('ci/results/feature_ledger.json','w'),indent=2)
# 2. declare what the artifacts actually say instead of `deductive`/`creusot`
c=json.load(open('specs/_closure/date-creusot-core.json'))
c['closure_kind']='bounded'; c['conditions']['owning_verifier']='kani'
json.dump(c,open('specs/_closure/date-creusot-core.json','w'),indent=2)
EOF
echo '=== D0: still declared deductive (no re-declaration), NO degradation record ==='
python3 - <<'EOF'
import json
c=json.load(open('specs/_closure/date-creusot-core.json'))
c['closure_kind']='deductive'; c['conditions']['owning_verifier']='creusot'
json.dump(c,open('specs/_closure/date-creusot-core.json','w'),indent=2)
EOF
python3 tools/ligature/ligature.pyz gate-g14; echo \"EXIT=$? (1 expected: G17 closure_kind + owning_verifier + CG3 error)\"
echo '=== D1: same, PLUS a schema-valid CG3 degradation record ==='
cat > specs/_closure/date-creusot-core.degradation.json <<'EOF2'
{"schema_version":"1.0","cluster":"date-creusot-core",
 "failed_conditions":["generic_callees_type_universal_or_creusot_owned"],
 "affected_edges":["date::year_month_day::to_days"],"ceiling":"per-instantiation",
 "tracking_issue":"chainlink:23","review":{"reviewer":"nobody-reviewed-this","reviewed_at":"1999-01-01"}}
EOF2
python3 tools/ligature/ligature.pyz gate-g14; echo \"EXIT=$? (1 expected: CG3 -> G14/degraded, G17 x2 SURVIVE, cluster still BLOCKED)\"
echo '=== D2: re-declare the profile bounded/kani, keep the record ==='
python3 - <<'EOF'
import json
c=json.load(open('specs/_closure/date-creusot-core.json'))
c['closure_kind']='bounded'; c['conditions']['owning_verifier']='kani'
json.dump(c,open('specs/_closure/date-creusot-core.json','w'),indent=2)
EOF
python3 tools/ligature/ligature.pyz validate-closure; echo \"EXIT=$? (0 expected)\"
python3 tools/ligature/ligature.pyz gate-g14; echo \"EXIT=$? (0 expected: 1 released under an accepted degradation record)\"
python3 tools/ligature/ligature.pyz status | grep 'cluster date-creusot-core'
echo '=== G1: every unverifiable field of that record is deliberately false ==='
python3 - <<'EOF'
import json
d=json.load(open('specs/_closure/date-creusot-core.degradation.json'))
d['affected_edges']=['invented-edge-that-does-not-exist']; d['ceiling']='documented'
d['tracking_issue']='chainlink:999999'
json.dump(d,open('specs/_closure/date-creusot-core.degradation.json','w'),indent=2)
EOF
python3 tools/ligature/ligature.pyz validate-closure; echo \"EXIT=$? (0: the record is 'accepted')\"
python3 tools/ligature/ligature.pyz gate-g14; echo \"EXIT=$? (0: released under ceiling 'documented' (chainlink:999999))\""""

ENTRY = {
    "id": "date-creusot-057",
    "pilot": "date-creusot",
    "stage": "probe-23-kani-deductive-degradation",
    "command": "cd date-creusot && python3 tools/ligature/ligature.pyz gate-g14",
    "tool": "ligature",
    "chain": "new",
    "symptom": (
        "PROBE #23 ANSWER, and the issue title's premise is false for 1.1.1. Kani evidence inside a "
        "cluster still declared `deductive` CANNOT be released under a degradation record: the record "
        "downgrades the CG3 finding from [G14/error] to [G14/degraded] and nothing else, while G17's two "
        "recompute findings (closure_kind 'deductive' but the closure contains "
        "['kani-bounded-model-check']; conditions.owning_verifier declared 'creusot' but computed "
        "'kani') survive it untouched and keep the cluster BLOCKED at exit 1. 29 single-mutation legs on a "
        "scratch rsync copy, each reset to a pristine snapshot first, plus 16 field-by-field probes of the "
        "record's own schema. The release DOES exist but is not a deductive release: re-declaring the "
        "profile closure_kind='bounded' + conditions.owning_verifier='kani' -- accepting a strictly weaker "
        "claim -- and adding the record makes gate-g14 exit 0 and print "
        "'cluster ... does NOT close: degraded under an accepted degradation record (declared "
        "closure_kind=bounded)' and 'OK: 0 cluster(s) close under their declared profile, 1 released under "
        "an accepted degradation record', with status reporting state=degraded. The gate's own remedy text "
        "('releasing this cluster needs a degradation record naming this condition with a tracking issue') "
        "is therefore insufficient on its own and silent about the re-declaration actually required. "
        "Authoring path: still none in the tool (no draft/approve template for either closure artifact) -- "
        "hand-write specs/_closure/<cluster>.degradation.json, which is the ONLY accepted filename "
        "(G1b binds the record's `cluster` field to the stem), and validate it with `validate-closure`, "
        "which under 1.1.1 validates it as a first-class artifact with G1a schema + G1b filename binding + "
        "G17 profile/record agreement in both directions; that largely retires date-ligature-040's "
        "'schemas only discoverable by probing' half. Required fields, all confirmed by real messages: "
        "schema_version, cluster, failed_conditions (array, minItems 1, closed 7-value condition-key enum), "
        "affected_edges (array of strings, minItems 1), ceiling (enum "
        "['documented','tested','harness-tested','assumed','per-instantiation','human-risk-acceptance']), "
        "tracking_issue (string matching ^[a-z]+:[A-Za-z0-9_.-]+$), review {reviewer non-empty, reviewed_at "
        "YYYY-MM-DD}, additionalProperties false. The rule the 29 legs reduce to: a record excuses exactly "
        "one class of finding -- a [G14/...] finding KEYED BY A CONDITION NAME whose condition the profile "
        "declares as holding -- and never a G17/error (a declaration that contradicts the recomputation) nor "
        "a G14/error about an obligation's provided guarantee; legs E2 and D21 confirm this away from Kani "
        "with a wrong count and a wrong boolean. AND THE RECORD'S OWN FIELDS ARE WORTH NOTHING AS "
        "EVIDENCE: ceiling is enum-only, so the weakest value 'documented' ('we wrote it down') releases "
        "the cluster exactly as human-risk-acceptance does; affected_edges is never resolved, "
        "['not-a-real-call-edge','also-invented'] releases it; tracking_issue is regex-only, "
        "'chainlink:999999' (no such issue) releases it; and review is FREE TEXT -- a record with "
        "review.reviewer='nobody-reviewed-this' and reviewed_at='1999-01-01' releases the cluster at exit 0 "
        "under a record the tool prints as 'accepted'. That last one is materially weaker than the sibling "
        "mechanism one command away: accept-promotion's own --help says it runs two guards before writing "
        "anything, a review-provenance check against ci/results/review_log.jsonl and a human-ruling gate "
        "over ci/results/human_rulings.jsonl, and ci/results/ on this pilot has no human_rulings.jsonl at "
        "all. gate-g14's release route has neither. Two further reproductions: gate-g14 honours a record "
        "naming single_verifier_system that validate-closure simultaneously rejects as 'a stale excuse "
        "keeps a closed gap reading as degraded' (only CG3 has chainlink #86's documented exemption, so the "
        "exempt set is one condition out of seven and is not derivable from anything the tool states), and "
        "status ingests the failed_conditions of a record both gates refused as invalid -- iterating a "
        "string character by character, 'limitations=[\"n\",\"o\",\"t\",...]' -- while gate-g14 prints "
        "'ignored as invalid and excluded from closure computation' for that same file."
    ),
    "repro_cmd": _REPRO,
    "exit_code": 0,
    "expected": (
        "Per the gate's own remedy text and issue #23's title, a schema-valid degradation record naming the "
        "unverifiable condition with a tracking issue should let a cluster containing Kani evidence be "
        "released, reported as 'released under an accepted degradation record'. 'Accepted' should mean the "
        "same class of acceptance accept-promotion enforces: the record's `review` block cross-checked "
        "against ci/results/review_log.jsonl and a ratified human ruling over its exact content in "
        "ci/results/human_rulings.jsonl, so that a fabricated reviewer, an affected_edges list naming no "
        "real edge, a tracking_issue naming no real issue, or the weakest possible ceiling cannot produce a "
        "release. It should also be stated, in the remedy text itself, when the record alone is not enough "
        "-- here the profile must be re-declared bounded/kani, which is a weaker claim than the one the "
        "operator started with, and the tool says nothing about that."
    ),
    "actual": (
        "D0 (Kani in the closure, no record): gate-g14 exit 1, 'cluster is BLOCKED', [G17/error] x2 + "
        "[G14/error] CG3; validate-closure exits 0. D1 (+ schema-valid CG3 record): the CG3 line becomes "
        "'- [G14/degraded] [generic_callees_type_universal_or_creusot_owned] ... -- accepted as degradation "
        "under ceiling 'per-instantiation' (chainlink:23)' but both [G17/error] lines are unchanged and the "
        "cluster is still BLOCKED, exit 1. D2 (re-declare closure_kind=bounded + owning_verifier=kani, "
        "record kept): validate-closure exit 0 'OK: all closure artifacts pass G1a/G1b and G17 "
        "profile/record consistency (2 discovered)', gate-g14 exit 0 'cluster date-creusot-core does NOT "
        "close: degraded under an accepted degradation record (declared closure_kind=bounded)' + 'OK: 0 "
        "cluster(s) close under their declared profile, 1 released under an accepted degradation record', "
        "status 'cluster date-creusot-core: degraded (closure_kind=bounded) "
        "limitations=[generic_callees_type_universal_or_creusot_owned]', status --json "
        "state=degraded, check --json result byte-identical to baseline with the finding at severity "
        "medium (baseline info), `gate g14` agreeing. Control D3 (same profile, no record): exit 1 BLOCKED. "
        "D9/D10: ceiling human-risk-acceptance and ceiling documented BOTH release. D11: invented "
        "affected_edges release. E6: tracking_issue chainlink:999999 releases. Leg G1: affected_edges="
        "['invented-edge-that-does-not-exist'], ceiling='documented', tracking_issue='chainlink:999999', "
        "review={'reviewer':'nobody-reviewed-this','reviewed_at':'1999-01-01'} -> validate-closure exit 0 "
        "and gate-g14 exit 0 'OK: 0 cluster(s) close under their declared profile, 1 released under an "
        "accepted degradation record', deterministic over 3 runs, with no human_rulings.jsonl present. "
        "D15: a CG3 record left on the healthy Creusot cluster is caught by gate-g14 ('a stale tracking "
        "record keeps a closed gap reading as degraded; remove it and shut the tracking issue') while "
        "validate-closure accepts it -- chainlink #86's exception working as documented. D4: a record naming "
        "a condition the profile declares holding is caught by validate-closure ('a stale excuse keeps a "
        "closed gap reading as degraded') while gate-g14 honours it for single_verifier_system, downgrading "
        "CG1's [G14/error] to [G14/degraded]. D13/D14: record content under any other filename in "
        "specs/_closure/ is validated against the CLOSURE-PROFILE schema and makes status print two cluster "
        "rows, one closure_kind=unknown. D18: status prints limitations=['n','o','t','-','a','n','-','a',"
        "'r','r','a','y'] from a record gate-g14 refused as invalid. The G17 recompute guard itself is sound "
        "and is what makes the issue's premise false -- no record excuses a wrong closure_kind, a wrong "
        "owning_verifier, a wrong boolean or a wrong count."
    ),
    "workaround": (
        "Treat 'released under an accepted degradation record' as 'schema-valid and consistent with the "
        "profile', never as 'accepted'. Read the ceiling out of the finding text, not out of any "
        "machine-readable surface -- it appears in no project-state or check field. Do not rely on "
        "affected_edges, tracking_issue or review for provenance: they are self-asserted, so a human must "
        "verify the reviewer, the edges and the issue by hand. For this pilot, do not author a degradation "
        "record at all: the live Creusot closure genuinely satisfies CG3, and adding a CG3 record there is "
        "caught by gate-g14 as a stale tracking record. If a Kani-owned closure really must be released, "
        "declare closure_kind='bounded' and owning_verifier='kani' first and record that the claim is "
        "weaker, because the tool will not say so. Escalated as epic #1 #101 (no review-provenance or "
        "human-ruling gate on this release route) and #102 (gate-g14 honours a record validate-closure "
        "rejects; status ingests a record both gates refused)."
    ),
    "severity": "blocker",
    "revisit_trigger": (
        "Any ligature release that (a) adds a draft/approve template or promotion step for closure profiles "
        "or degradation records, (b) requires the record's `review` block to match "
        "ci/results/review_log.jsonl and/or a ratified ruling in ci/results/human_rulings.jsonl the way "
        "accept-promotion does, (c) validates ceiling/affected_edges/tracking_issue against real artifacts, "
        "or (d) makes gate-g14's G17 recompute findings excusable by a record. Re-run "
        "analysis/ligature/probe-23-legs.py and probe-23-release-evidence.py; all 29 legs are expected to "
        "keep their exit codes, so any change to the D0/D1/D2 verdict triple or to the release is the signal."
    ),
    "pyz_sha256": "3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4",
    "tool_path": "date-creusot/tools/ligature/ligature.pyz",
    "tool_version": "1.1.1 (content hash sha256:172a87a8be8406d625b57b1aa96dc8cb76756e615983d8da70aa298892964558)",
}


def main():
    raw = open(LEDGER, "rb").read()
    before = raw.decode()
    before_lines = before.splitlines()

    missing = [f for f in FIELDS if f not in ENTRY]
    extra = [k for k in ENTRY if k not in FIELDS]
    assert not missing, f"MISSING schema fields: {missing}"
    assert not extra, f"UNEXPECTED fields: {extra}"
    assert ENTRY["tool"] in {"ligature", "creusot", "verus", "kani", "nextest", "rdb",
                             "mcp", "oracle"}, ENTRY["tool"]
    assert ENTRY["severity"] in {"blocker", "scope-cut", "friction"}, ENTRY["severity"]
    assert ENTRY["chain"] in {"A.x", "B.x", "C.n", "new"}, ENTRY["chain"]
    assert isinstance(ENTRY["exit_code"], int)

    ids = [json.loads(ln)["id"] for ln in before_lines if ln.strip()]
    assert len(set(ids)) == len(ids), "pre-existing ids are not unique"
    assert ENTRY["id"] not in ids, f"{ENTRY['id']} already present"

    print(f"ledger sha256 before: {hashlib.sha256(raw).hexdigest()[:16]}")
    print(f"lines before: {len(before_lines)}  unique ids: {len(ids)}")

    if "--show" in sys.argv:
        print(json.dumps(ENTRY, indent=2))
        return

    with open(LEDGER, "a") as f:
        f.write(json.dumps(ENTRY, sort_keys=True) + "\n")

    after = open(LEDGER, "rb").read()
    assert after.startswith(raw), "APPEND-ONLY VIOLATED: prior bytes changed"
    after_lines = after.decode().splitlines()
    new_ids = [json.loads(ln)["id"] for ln in after_lines if ln.strip()]
    assert len(set(new_ids)) == len(new_ids), "ids no longer unique"
    print(f"append-only OK: first {len(before_lines)} lines byte-identical")
    print(f"lines {len(before_lines)} -> {len(after_lines)}")
    print(f"unique ids: {len(set(new_ids))} of {len(new_ids)}")
    print(f"appended id: {ENTRY['id']}  severity={ENTRY['severity']}  "
          f"fields={len(ENTRY)}/17")
    print(f"ledger sha256 after:  {hashlib.sha256(after).hexdigest()[:16]}")
    print()
    print("repro_cmd, run verbatim from the workspace root:")
    print(_REPRO)


if __name__ == "__main__":
    main()