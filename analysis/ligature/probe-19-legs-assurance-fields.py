#!/usr/bin/env python3
"""Probe #19, part 3: which FIELDS of the recorded creusot achievement does
gate-g14 actually recompute, and which does it take on trust?"""
import json, os, shutil, subprocess, sys

PRISTINE = "/tmp/opencode/p19/pristine"
SCRATCH = "/tmp/opencode/p19/scratch3"
PYZ = "tools/ligature/ligature.pyz"


def reset():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    shutil.copytree(PRISTINE, SCRATCH, symlinks=True)


def lig(*a):
    p = subprocess.run([sys.executable, PYZ, *a], cwd=SCRATCH,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).rstrip()


def mutate(fn):
    p = os.path.join(SCRATCH, "ci/results/feature_ledger.json")
    d = json.load(open(p))
    fn(d)
    json.dump(d, open(p, "w"), indent=2)
    open(p, "a").write("\n")


LEGS = [
    ("N1", "evidence.verifier creusot -> kani ONLY (kind stays "
           "creusot-deductive-check, harness stays creusot)",
     lambda d: [r["record"]["evidence"].__setitem__("verifier", "kani")
                for r in d["obligation_records"]]),
    ("N2", "evidence.harness creusot -> kani ONLY",
     lambda d: [r["record"]["evidence"].__setitem__("harness", "kani")
                for r in d["obligation_records"]]),
    ("N3", "config.toolchain rustc/cargo-creusot/why3 -> 'handwritten'",
     lambda d: [r["record"]["config"].__setitem__("toolchain", "handwritten")
                for r in d["obligation_records"]]),
    ("N4", "config.target x86_64-unknown-linux-gnu -> 'aarch64-unknown-none'",
     lambda d: [r["record"]["config"].__setitem__(
                "target", "aarch64-unknown-none")
                for r in d["obligation_records"]]),
    ("N5", "support.status supported -> unsupported (all five)",
     lambda d: [r["record"]["support"].__setitem__("status", "unsupported")
                for r in d["obligation_records"]]),
    ("N6", "trust.assumptions [] -> one entry on every record",
     lambda d: [r["record"]["trust"]["assumptions"].append(
                {"assumption_id": "A-SMOKE", "statement": "unproved",
                 "justification": "probe"}) for r in d["obligation_records"]]),
    ("N7", "claim.kind postcondition-holds -> precondition-holds",
     lambda d: [r["record"]["claim"].__setitem__("kind", "precondition-holds")
                for r in d["obligation_records"]]),
    ("N8", "drop the last obligation record (YearMonthDayLast.C1) only",
     lambda d: d["obligation_records"].pop()),
]

for tag, desc, fn in LEGS:
    reset()
    mutate(fn)
    rc, out = lig("gate-g14")
    first = out.splitlines()
    verdict = "PASSES (exit 0) -- mutation NOT detected" if rc == 0 else \
              f"BLOCKED (exit {rc}) -- mutation detected"
    errs = [l.strip() for l in first if "[G14/error]" in l]
    g17 = [l.strip() for l in first if "[G17" in l]
    print("=" * 78)
    print(f"## {tag}: {desc}")
    print(f"$ ligature gate-g14   EXIT={rc}   ->  {verdict}")
    for l in (errs + g17)[:3]:
        print("   " + l[:300])
    if rc == 0:
        print("   " + [l for l in first if "OK: 1 cluster" in l][0])

reset()
print("=" * 78)
print("scratch3 reset to pristine")