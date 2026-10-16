#!/usr/bin/env python3
"""Probe #19: is Creusot evidence recognized as ACHIEVED assurance, or ASSUMED?

Each leg resets the scratch from a pristine snapshot, mutates exactly one
artifact, and re-runs the gates. Read-only apart from the scratch copy.
"""
import json, os, shutil, subprocess, sys

SCRATCH = "/tmp/opencode/p19/scratch"
PRISTINE = "/tmp/opencode/p19/pristine"
PYZ = "tools/ligature/ligature.pyz"


def reset():
    shutil.rmtree(SCRATCH)
    shutil.copytree(PRISTINE, SCRATCH, symlinks=True)


def lig(*args):
    p = subprocess.run([sys.executable, PYZ, *args], cwd=SCRATCH,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).rstrip()


def edit_json(rel, fn):
    path = os.path.join(SCRATCH, rel)
    with open(path) as f:
        d = json.load(f)
    fn(d)
    with open(path, "w") as f:
        json.dump(d, f, indent=2)
        f.write("\n")


def banner(t):
    print("\n" + "=" * 78)
    print("## " + t)
    print("=" * 78)


def show(title, rc, out, keep=None):
    print(f"--- {title}  EXIT={rc}")
    if keep:
        out = "\n".join(l for l in out.splitlines() if keep in l)
    print(out)


# ---------------------------------------------------------------- baseline
banner("LEG 0 -- pristine scratch, baseline (nothing mutated)")
for cmd in (["validate"], ["validate-interaction"], ["validate-work-package"],
            ["validate-evidence"], ["validate-closure"], ["gate-g14"],
            ["gate", "g18"], ["gate", "g19"], ["gate", "g20"],
            ["gate", "r1-g16"], ["doctor"], ["write-set-check"]):
    rc, out = lig(*cmd)
    print(f"$ ligature {' '.join(cmd):24s} EXIT={rc}")
    if rc != 0:
        print(out)

# ---------------------------------------------------------------- LEG A
banner("LEG A -- delete ALL recorded assurance from the ledger "
       "(obligation_records: [])")
reset()
edit_json("ci/results/feature_ledger.json",
          lambda d: d.__setitem__("obligation_records", []))
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14   EXIT={rc}")
print(out)
rc, out = lig("status")
print(f"$ ligature status     EXIT={rc}")
print("\n".join(l for l in out.splitlines() if "obligation" in l or "cluster" in l))
rc, out = lig("check", "--json")
print(f"$ ligature check --json EXIT={rc}")

# ---------------------------------------------------------------- LEG B
banner("LEG B -- keep the records but flip claim.result pass -> fail")


def flip_result(d):
    for r in d["obligation_records"]:
        r["record"]["claim"]["result"] = "fail"


reset()
edit_json("ci/results/feature_ledger.json", flip_result)
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14   EXIT={rc}")
print(out)

# ---------------------------------------------------------------- LEG C
banner("LEG C -- keep the records but relabel the verifier creusot -> kani")


def flip_verifier(d):
    for r in d["obligation_records"]:
        r["record"]["evidence"]["verifier"] = "kani"
        r["record"]["evidence"]["harness"] = "kani"
        r["record"]["evidence"]["kind"] = "kani-bounded-model-check"


reset()
edit_json("ci/results/feature_ledger.json", flip_verifier)
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14   EXIT={rc}")
print(out)

# ---------------------------------------------------------------- LEG D
banner("LEG D -- repoint every proof_targets at a proof.json that does NOT exist")


def ghost_path(d):
    for r in d["obligation_records"]:
        r["record"]["evidence"]["scope"]["proof_targets"] = \
            "rust/date-creusot-core/verif/date_creusot_core_rlib/NOPE/proof.json"


reset()
edit_json("ci/results/feature_ledger.json", ghost_path)
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14   EXIT={rc}")
print(out)

# ---------------------------------------------------------------- LEG E
banner("LEG E -- repoint every proof_targets at a REAL proof.json whose "
       "proofs map is EMPTY (no goal discharged)")


def empty_proof(d):
    src = "rust/date-creusot-core/verif/date_creusot_core_rlib/day/impl_Day/ok"
    with open(os.path.join(SCRATCH, src, "proof.json")) as f:
        empty = json.load(f)
    empty["proofs"] = {}
    os.makedirs(os.path.join(SCRATCH, src), exist_ok=True)
    with open(os.path.join(SCRATCH, src, "proof.json"), "w") as f:
        json.dump(empty, f, indent=2)
    for r in d["obligation_records"]:
        r["record"]["evidence"]["scope"]["proof_targets"] = src + "/proof.json"


reset()
edit_json("ci/results/feature_ledger.json", empty_proof)
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14   EXIT={rc}")
print(out)

# ---------------------------------------------------------------- LEG F
banner("LEG F -- verifier_policy.default creusot -> kani (is the DEFAULT "
       "verifier load-bearing for G14?)")


def default_kani(d):
    d["verifier_policy"]["default"] = "kani"


reset()
edit_json("project-descriptor.json", default_kani)
for cmd in (["validate"], ["validate-interaction"], ["validate-work-package"],
            ["validate-closure"], ["gate-g14"], ["doctor"]):
    rc, out = lig(*cmd)
    print(f"$ ligature {' '.join(cmd):22s} EXIT={rc}")
    print(out)
rc, out = lig("status")
print(f"$ ligature status EXIT={rc}")
print("\n".join(l for l in out.splitlines()
                if "cluster" in l or "obligations" in l))

# ---------------------------------------------------------------- LEG G
banner("LEG G -- verifier_policy.default creusot -> verus")


def default_verus(d):
    d["verifier_policy"]["default"] = "verus"


reset()
edit_json("project-descriptor.json", default_verus)
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14 EXIT={rc}")
print(out)

# ---------------------------------------------------------------- LEG H
banner("LEG H -- drop the creusot achievement for ONE obligation only "
       "(Weekday.C2)")
reset()
edit_json("ci/results/feature_ledger.json",
          lambda d: d["obligation_records"].pop(1))
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14 EXIT={rc}")
print(out)
rc, out = lig("status")
print(f"$ ligature status EXIT={rc}")
print("\n".join(l for l in out.splitlines()
                if "obligation" in l or "cluster" in l))

# ---------------------------------------------------------------- LEG I
banner("LEG I -- OWNING VERIFIER: closure profile conditions.owning_verifier "
       "creusot -> kani, leaving the recorded creusot assurance in place")
reset()
edit_json("specs/_closure/date-creusot-core.json",
          lambda d: d["conditions"].__setitem__("owning_verifier", "kani"))
for cmd in (["validate-closure"], ["gate-g14"]):
    rc, out = lig(*cmd)
    print(f"$ ligature {' '.join(cmd):18s} EXIT={rc}")
    print(out)

# ---------------------------------------------------------------- reset
banner("reset scratch to pristine")
reset()
rc, out = lig("gate-g14")
print(f"$ ligature gate-g14 EXIT={rc}")
print(out)