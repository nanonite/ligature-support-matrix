#!/usr/bin/env python3
"""Stage the #47 drafts through `ligature draft` (manual backend: response on stdin).

Usage: run_47_drafts.py <pilot-root> <responses-dir> <log-dir> [--only PREFIX]
Runs from the pilot root with its pinned tools/ligature/ligature.pyz.
"""
import json
import subprocess
import sys
from pathlib import Path

pilot = Path(sys.argv[1]).resolve()
responses = Path(sys.argv[2]).resolve()
logs = Path(sys.argv[3]).resolve()
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else ""
logs.mkdir(parents=True, exist_ok=True)
targets = json.loads((responses / "targets.json").read_text())
specs = pilot / "crates/crypto-mixed-core/specs"
TRIPLE = "x86_64-unknown-linux-gnu"
SPEC_FILE = {"ChaCha20Poly1305": "cha_cha20_poly1305.json", "ChaCha20": "cha_cha20.json", "Poly1305": "poly1305.json"}
SNAKE = {"ChaCha20Poly1305": "cha_cha20_poly1305", "ChaCha20": "cha_cha20", "Poly1305": "poly1305"}
FINDING = ("chainlink #47 (2026-10-19): gate-r1-g16 reports definite cross-concept calls absent from I after the "
           "call sites were made resolvable; see crypto-mixed findings crypto-ligature-010/011.")
if "--finding" in sys.argv:
    FINDING = sys.argv[sys.argv.index("--finding") + 1]


def prior(target):
    path = pilot / target
    return path.read_text() if path.exists() else ""


def spec_text(concept):
    return (specs / SPEC_FILE[concept]).read_text()


def run(target, template, variables):
    response = (responses / targets[target]).read_text()
    cmd = ["python3", "-I", "tools/ligature/ligature.pyz", "draft", "3", template, target]
    for key, value in variables.items():
        cmd += ["--var", f"{key}={value}"]
    proc = subprocess.run(cmd, cwd=pilot, input=response, capture_output=True, text=True)
    name = Path(target).name
    (logs / f"draft-{name}.out").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    tail = [l for l in (proc.stdout + proc.stderr).splitlines() if l.strip()][-3:]
    print(f"{proc.returncode}  {target}\n     " + "\n     ".join(tail))
    return proc.returncode


rc_all = 0
for target in targets:
    if only and only not in target:
        continue
    doc = json.loads((responses / targets[target]).read_text())
    if "/_boundaries/" in target:
        caller, callee = doc["caller"]["concept"], doc["callee"]["concept"]
        rc = run(target, "boundary-drafting", {
            "caller_concept": caller, "caller_method": doc["caller"]["method"],
            "callee_concept": callee, "callee_method": doc["callee"]["method"],
            "caller_spec": spec_text(caller), "callee_spec": spec_text(callee),
            "reliance_policy": (pilot / "docs/reliance-policy.md").read_text() if (pilot / "docs/reliance-policy.md").exists() else "",
            "prior_artifact": "", "finding": FINDING,
            "caller_concept_snake": SNAKE[caller], "callee_concept_snake": SNAKE[callee],
        })
    elif "/_interactions/" in target:
        caller, callee = doc["caller"]["concept"], doc["callee"]["concept"]
        rc = run(target, "interaction-drafting", {
            "interaction_id": doc["interaction_id"], "target_triple": TRIPLE,
            "caller_concept": caller, "caller_method": doc["caller"]["method"],
            "callee_concept": callee, "callee_method": doc["callee"]["method"],
            "caller_spec": spec_text(caller), "callee_spec": spec_text(callee),
            "prior_artifact": prior(target), "finding": FINDING,
        })
    elif "/_bridges/" in target:
        boundary = specs / "_boundaries" / f"{doc['boundary_id']}.json"
        boundary_text = boundary.read_text() if boundary.exists() else (specs / "_boundaries" / f"{doc['boundary_id']}.json.draft").read_text()
        rc = run(target, "bridge-drafting", {
            "bridge_id": doc["bridge_id"], "boundary_id": doc["boundary_id"],
            "caller_spec": spec_text("ChaCha20Poly1305"), "callee_spec": spec_text("ChaCha20"),
            "boundary_contract": boundary_text, "prior_artifact": "", "finding": FINDING,
            "callee_requirement": doc["callee_requirement"],
        })
    else:
        concept = doc["concept"]
        rc = run(target, "concept-to-code", {
            "concept": concept, "cluster": doc["cluster"], "verifier": doc["verifier"],
            "source_material": "crates/crypto-mixed-core/src (chainlink #47 respelling and Poly1305 fold)",
            "prior_artifact": spec_text(concept), "finding": FINDING,
        })
    rc_all |= rc
sys.exit(rc_all)
