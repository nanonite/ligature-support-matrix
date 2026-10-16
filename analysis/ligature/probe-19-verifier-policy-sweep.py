#!/usr/bin/env python3
"""Probe #19, part 2: is verifier_policy.default load-bearing anywhere?

Runs every read-only ligature command against three descriptor variants
(default=creusot / kani / verus) and byte-diffs the outputs.
"""
import json, os, shutil, subprocess, sys

PRISTINE = "/tmp/opencode/p19/pristine"
SCRATCH = "/tmp/opencode/p19/scratch2"
PYZ = "tools/ligature/ligature.pyz"

CMDS = [
    ["validate"], ["validate-interaction"], ["validate-evidence"],
    ["validate-work-package", "ci/manifest/WP-DATE-CREUSOT.json"],
    ["validate-closure"], ["gate-g14"], ["gate", "g18"], ["gate", "g19"],
    ["gate", "g20"], ["gate", "r1-g16"], ["doctor"], ["write-set-check"],
    ["status"], ["check", "--json"],
]


def build(variant):
    shutil.rmtree(SCRATCH, ignore_errors=True)
    shutil.copytree(PRISTINE, SCRATCH, symlinks=True)
    if variant != "creusot":
        p = os.path.join(SCRATCH, "project-descriptor.json")
        d = json.load(open(p))
        d["verifier_policy"]["default"] = variant
        json.dump(d, open(p, "w"), indent=2)
        open(p, "a").write("\n")


def run(*args):
    p = subprocess.run([sys.executable, PYZ, *args], cwd=SCRATCH,
                       capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


results = {}
for variant in ("creusot", "kani", "verus"):
    build(variant)
    results[variant] = {tuple(c): run(*c) for c in CMDS}

print("exit codes: default=creusot (baseline) | kani | verus")
print(f"{'command':46s} {'creusot':>8s} {'kani':>6s} {'verus':>6s}  output")
for c in CMDS:
    rc = [results[v][tuple(c)][0] for v in ("creusot", "kani", "verus")]
    same = (results["creusot"][tuple(c)][1] == results["kani"][tuple(c)][1]
            == results["verus"][tuple(c)][1])
    print(f"{' '.join(c):46s} {rc[0]:>8d} {rc[1]:>6d} {rc[2]:>6d}  "
          f"{'IDENTICAL' if same else '*** DIFFERS ***'}")

shutil.rmtree(SCRATCH, ignore_errors=True)