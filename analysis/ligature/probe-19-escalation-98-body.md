Found while answering chainlink #19 ("[p1 probe] creusot default + deductive accepted through G14; Creusot evidence recognized"), pilot root `date-creusot/`.

## Commands run, exit codes

Repro (copy-paste runnable from the workspace root):

```
cd date-creusot && rm -rf /tmp/p19-crash && rsync -a --delete --exclude upstream/ --exclude .git . /tmp/p19-crash/ && cd /tmp/p19-crash && python3 -c "
import json
p='ci/results/feature_ledger.json'
d=json.load(open(p))
for r in d['obligation_records']:
    r['record']['trust']['assumptions']=[{'assumption_id':'A-SMOKE','statement':'unproved','justification':'probe'}]
json.dump(d,open(p,'w'),indent=2)
" && python3 tools/ligature/ligature.pyz gate-g14
```

exit code: **1**

Actual output (tail):

```
  File "/tmp/p19-crash/tools/ligature/ligature.pyz/pipeline.py", line 1280, in cmd_gate_g14
  File "/tmp/p19-crash/tools/ligature/ligature.pyz/gate_g14.py", line 1329, in gate_workspace
  File "/tmp/p19-crash/tools/ligature/ligature.pyz/gate_g14.py", line 1129, in gate_cluster
  File "/tmp/p19-crash/tools/ligature/ligature.pyz/gate_g14.py", line 590, in check_transitive_assumptions
TypeError: unhashable type: 'dict'
```

## Expected vs actual

**Expected.** `gate-g14` either accepts or reports a finding naming the offending
field. The control case proves the gate has the diagnostic it needs: with
`trust.assumptions` holding the *same* value as an assumption-id **string**
(`["A-SMOKE"]`), the identical edit produces four clean, specific findings and no
traceback:

```
  - [G14/error] YearMonthDayLast.C1: WP-DATE-CREUSOT's own provided guarantee is not met by what it achieved: trust.assumptions includes 'A-SMOKE', not in required_profile.trust_policy.assumptions_allowed [] (required_profile declares no trust_policy at all)
  - [G14/error] [transitive_assumptions_within_policy] A-SMOKE: assumption is relied on at WP-DATE-CREUSOT:Weekday.C1, ... but is not in the trust policy of this cluster's entry requirement Weekday.C1 ([]) -- trust policy applies across the whole closure, not only the edge that carries it
  - [G17/error] date-creusot-core: conditions.transitive_assumptions_within_policy is declared as True but the computed closure says False -- conditions are recomputed, never stored-and-trusted
FAIL: 1 cluster(s) blocked, 0 not blocked
```

**Actual.** An object-shaped entry in `trust.assumptions` makes
`check_transitive_assumptions` put the entry in a set, and the gate dies with an
unhandled `TypeError: unhashable type: 'dict'`. The exit code happens to be 1, so
it is fail-closed by accident, but the operator gets a Python traceback instead of
a finding, and there is no way to tell this apart from a genuine block without
reading the traceback.

## Why this is a defect and not a bad input

`trust.assumptions` on an achieved-assurance record is an **id list**, and the
sibling field on a promoted interaction is too — `reliances[].required_assurance.trust_policy.assumptions_allowed: []`
is a list of strings in every promoted interaction in this pilot, and
`check_transitive_assumptions` compares against it by value. Nothing in the tool
says "strings only" for the achieved side: the tool never validates the achieved
record's `trust.assumptions` shape before hashing it, so a value that is
structurally plausible is enough to crash the release gate.

**Reachability caveat, stated honestly:** I could **not** demonstrate this from the
sanctioned producer. `record-assurance` copies the work-package manifest's
`definition_of_done.trusted_assumptions` into the record, and I could not get a
non-empty `trusted_assumptions` past the manifest schema at all — every
`assumption_ref` shape I tried is rejected before `record-assurance` runs:

- `{"assumption_ref":"A-SMOKE","risk":"low","mitigations":[]}` -> `manifest ... is not schema-valid ('A-SMOKE' is not valid under any of the given schemas)`
- `{"assumption_ref":{"assumption_id":"A-SMOKE","statement":"...","justification":"..."},"risk":"low","mitigations":[]}` -> same rejection

So today the crash is reachable by editing `ci/results/feature_ledger.json` directly
— which `write-set-check` reports as `write set: clean`, exit 0, because
`ci/results/**` is in neither `allowed_roots` nor `protected_roots`. That second
half may itself be the more interesting bug: a manifest that *wants* to declare a
trusted assumption cannot, and the artifact that would carry one is unpoliced.

## Environment

- pilot: `date-creusot/`
- binary: `tools/ligature/ligature.pyz`, `ligature version` -> `1.1.1`
- sha256 (`date-creusot/tools/ligature/SHA256SUMS`): `3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4`
  (`sha256sum -c SHA256SUMS` -> `ligature.pyz: OK`)
- python: 3.12.3, Linux/x86_64

Found by chainlink #19, attempt 1/20, 2026-09-30. Recorded as
`date-creusot-055` in `date-creusot/findings/limitations.jsonl`; that entry covers
the same leg (gate-g14 not re-opening the certificate) and carries the full
one-liner repro.