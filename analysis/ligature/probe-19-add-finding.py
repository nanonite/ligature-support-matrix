#!/usr/bin/env python3
"""Append chainlink #19's single finding to date-creusot/findings/limitations.jsonl.

Append-only: opens in 'a', touches no existing line. Refuses to run if the id is
already present, so a re-run cannot silently duplicate a line.
"""
import json, sys, os

ROOT = "/home/goya/storage/full-ligature-port-workspace/date-creusot"
LEDGER = os.path.join(ROOT, "findings/limitations.jsonl")
FID = "date-creusot-055"

REPRO = (
    "cd date-creusot && rm -rf /tmp/p19-forge && rsync -a --delete "
    "--exclude upstream/ --exclude .git . /tmp/p19-forge/ && cd /tmp/p19-forge && python3 -c \"\n"
    "import json\n"
    "p='ci/results/feature_ledger.json'\n"
    "d=json.load(open(p))\n"
    "for r in d['obligation_records']:\n"
    "    r['record']['evidence']['scope']['proof_targets']='rust/date-creusot-core/verif/date_creusot_core_rlib/TOTALLY/FAKE/proof.json'\n"
    "    r['record']['evidence']['verifier']='kani'\n"
    "    r['record']['evidence']['harness']='kani'\n"
    "    r['record']['config']['toolchain']='handwritten'\n"
    "    r['record']['config']['target']='aarch64-unknown-none'\n"
    "json.dump(d,open(p,'w'),indent=2)\n"
    "\" && (ls rust/date-creusot-core/verif/date_creusot_core_rlib/TOTALLY 2>&1 || true) && "
    "python3 tools/ligature/ligature.pyz write-set-check >/dev/null; echo \"write-set-check=$?\"; "
    "python3 tools/ligature/ligature.pyz doctor >/dev/null; echo \"doctor=$?\"; "
    "python3 tools/ligature/ligature.pyz gate-g14; echo \"gate-g14=$?\""
)

SYMPTOM = (
    "PROBE #19 ANSWER, second half. 'gate-g14' does re-derive the DEDUCTIVE closure from the "
    "recorded assurance -- but it re-derives it from the ledger, and it never re-opens the ledger's "
    "own proof certificate. Field-by-field falsification on a scratch rsync copy (each leg resets to "
    "a pristine snapshot and mutates exactly one field of ci/results/feature_ledger.json) splits the "
    "achieved-assurance record into a RECOMPUTED set and a TRUST-ON-DECLARATION set. "
    "RECOMPUTED, each mutation flips gate-g14 from 0 to 1 with a specific finding: deleting every "
    "record -> \"WP-DATE-CREUSOT provides this obligation but recorded no achieved assurance for it\" "
    "x5 plus the generic_callees limitation reverting to \"declared as true, but this closure's "
    "artifacts cannot verify it: no achieved assurance record at all\"; deleting one record -> blocked "
    "for that obligation only; claim.result pass->fail -> blocked x5; support.status "
    "supported->unsupported -> blocked x5; claim.kind -> schema-invalid, blocked x5; evidence.kind "
    "creusot-deductive-check -> kani-bounded-model-check -> blocked x5 PLUS two G17 errors "
    "(\"conditions.owning_verifier is declared as 'creusot' but the computed closure says 'kani' -- "
    "conditions are recomputed, never stored-and-trusted\" and \"closure_kind is 'deductive' but the "
    "transitive closure contains ['kani-bounded-model-check']\"); trust.assumptions -> blocked. "
    "TRUST-ON-DECLARATION, every one of these leaves gate-g14 at exit 0 with the same VERIFIED-from-"
    "artifact-data line: evidence.scope.proof_targets repointed at a path that does not exist; "
    "repointed at a real proof.json whose proofs map is empty (nothing discharged); evidence.verifier "
    "creusot->kani; evidence.harness creusot->kani; config.toolchain "
    "'rustc/cargo-creusot/why3'->'handwritten'; config.target "
    "'x86_64-unknown-linux-gnu'->'aarch64-unknown-none'. So the CG3 line G14 prints -- "
    "\"generic_callees_type_universal_or_creusot_owned is VERIFIED from artifact data, not taken on "
    "declaration: every work package in the closure has a recorded achievement and none of them is a "
    "Kani result (['creusot-deductive-check'])\" -- is true as written (the KIND is recomputed, and a "
    "Kani kind really does block) but it certifies the ledger's own wording, not the certificate it "
    "points at. Nothing available detects the forgery: write-set-check exits 0 ('write set: clean', "
    "because ci/results/** is in neither allowed_roots nor protected_roots), doctor exits 0, and "
    "'report feature-ledger' REFUSES to run at all -- \"refusing to overwrite the assurance report at "
    "ci/results/feature_ledger.json ... must not share one path\" (date-ligature-051/-054/-056) -- so "
    "the ledger can never be re-derived, only re-recorded. The honest positive half, which I confirmed "
    "rather than assumed: the producer is genuinely grounded. 'record-assurance' reads the real "
    "why3find proof.json and prints the proved-goal count per obligation (Weekday.C1 1, Weekday.C2 1, "
    "Weekday.C3 1, YearMonthDay.C2 50, YearMonthDayLast.C1 2), and it is fail-closed three ways "
    "(nonexistent path -> exit 2 'evidence path does not exist'; a certificate not under a directory "
    "named for its concept -> exit 2 \"does not, so it cannot be shown to be about this obligation\"; "
    "a real proof.json with proofs:{} -> exit 2 'carries no `proofs` -- this is not a why3find proof "
    "certificate'). Re-running record-assurance over the five live proof paths regenerates a ledger "
    "byte-identical to the live one (md5 463583d9eda1ed0292800703bf2835cf both ways). So the LIVE "
    "ledger is real; what the gate cannot do is prove it, on its own, at gate time."
)

EXPECTED = (
    "gate-g14, the release gate, resolves each obligation's evidence.scope.proof_targets and confirms "
    "the certificate is present, is a why3find proof.json, and discharges at least one goal -- or says "
    "it did not check. It also either enforces evidence.verifier/harness against "
    "verifier_policy.default and the obligation's owning_verifier, or does not claim to. As it "
    "stands, an assurance report whose certificate pointers are fabricated is indistinguishable, to "
    "every available command, from one record-assurance just produced from a real cargo creusot run."
)

ACTUAL = (
    "gate-g14 reads only ci/results/feature_ledger.json and never touches rust/date-creusot-core/verif/"
    "**. With every proof_targets rewritten to a directory that does not exist: gate-g14 exit 0 "
    "('OK: 1 cluster(s) close under their declared profile'), write-set-check exit 0 ('write set: "
    "clean'), doctor exit 0. Same exit 0 when the pointers name a real proof.json with an empty proofs "
    "map, and when evidence.verifier/evidence.harness say kani and config.toolchain says 'handwritten' "
    "and config.target says 'aarch64-unknown-none'. The gate's own message in that state still says "
    "the condition is 'VERIFIED from artifact data, not taken on declaration'. The gate's remedy text "
    "for a missing record ('record one from this work package's proof certificates with `ligature "
    "record-assurance ...`') is the only place the certificate is ever consulted, and that is at "
    "record time, not gate time."
)

WORKAROUND = (
    "Treat 'record-assurance <wp> --proof ...' as the load-bearing step and re-run it, rather than "
    "reading a clean gate-g14 as proof the creusot certificates are current: the regenerated ledger's "
    "md5 must equal the committed one, and a mismatch is the only in-pilot signal that the committed "
    "ledger is stale or hand-edited. The pilot already does this -- the live ledger is byte-identical "
    "to a fresh regeneration. Separately: never hand-edit ci/results/feature_ledger.json, and treat "
    "the ledger as unpoliced by write-set-check (it is in neither allowed_roots nor protected_roots). "
    "Do NOT edit evidence.verifier/harness/config to 'fix' a mismatch: gate-g14 ignores those fields, "
    "so the edit would be invisible and the record less, not more, truthful."
)

REVISIT = (
    "Any ligature release that makes gate-g14 resolve evidence.scope.proof_targets, that enforces "
    "evidence.verifier against verifier_policy.default / conditions.owning_verifier, or that lets "
    "'report feature-ledger' and record-assurance write distinct paths (the collision named in the "
    "tool's own error text) so the ledger can be re-derived rather than re-recorded. Also re-check "
    "whether ci/results/** should be in write_set.protected_roots -- it currently is in neither list, "
    "which is why a forged ledger is 'write set: clean'."
)

SEVERITY = "blocker"

rec = {
    "id": FID,
    "pilot": "date-creusot",
    "stage": "probe-19-creusot-default-deductive-g14",
    "command": "cd date-creusot && python3 tools/ligature/ligature.pyz gate-g14",
    "tool": "ligature",
    "chain": "new",
    "symptom": SYMPTOM,
    "repro_cmd": REPRO,
    "exit_code": 0,
    "expected": EXPECTED,
    "actual": ACTUAL,
    "workaround": WORKAROUND,
    "severity": SEVERITY,
    "revisit_trigger": REVISIT,
    "pyz_sha256": "3edfd03cd4e6dee30139c48e7921abcf338cb279ff2eb4e4d0bba9a44725deb4",
    "tool_path": ("/home/goya/storage/full-ligature-port-workspace/date-creusot/tools/ligature/"
                  "ligature.pyz"),
    "tool_version": "1.1.1",
}

existing = [json.loads(l) for l in open(LEDGER) if l.strip()]
ids = [r["id"] for r in existing]
if FID in ids:
    print(f"REFUSING: {FID} already present ({len(existing)} lines). Nothing written.")
    sys.exit(1)

before = os.path.getsize(LEDGER)
with open(LEDGER, "a") as f:
    f.write(json.dumps(rec) + "\n")

after = [json.loads(l) for l in open(LEDGER) if l.strip()]
assert len(after) == len(existing) + 1, "line count wrong"
assert after[:len(existing)] == existing, "an existing line changed"
assert len({r["id"] for r in after}) == len(after), "duplicate id"
required = {"id", "pilot", "stage", "command", "tool", "chain", "symptom",
            "repro_cmd", "exit_code", "expected", "actual", "workaround",
            "severity", "revisit_trigger", "pyz_sha256", "tool_path",
            "tool_version"}
missing = required - set(rec)
assert not missing, f"schema fields missing: {missing}"
assert rec["severity"] in {"blocker", "scope-cut", "friction"}, rec["severity"]
assert rec["chain"] in {"A.1", "A.2", "A.3", "B.1", "B.2", "B.3", "C.1",
                        "C.2", "C.3", "new"}, rec["chain"]
assert isinstance(rec["exit_code"], int)

print(f"appended {FID}: {len(existing)} -> {len(after)} lines "
      f"(+{os.path.getsize(LEDGER) - before} bytes), append-only verified, "
      f"{len(after)} unique ids, all findings-schema.md fields present")