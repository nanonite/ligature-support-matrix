#!/usr/bin/env python3
"""Append the chainlink #27 (ligature init + descriptor) findings.

Idempotent: a finding whose `id` is already present in
findings/limitations.jsonl is left alone, so re-running after a hand edit
does not duplicate or clobber a line.

Run from the pilot root:
    python3 analysis/ligature/write-findings-27.py

Evidence for every claim below is in analysis/ligature/init-check.txt
(probes P1, P4, P4b, P7, P8).
"""
import json
import pathlib

PYZ = "tools/ligature/ligature.pyz"
SHA = "9c921eeb1bbb858c0041e49f07cf5d06988eb798ba60b9207f7576cba430637c"
VERSION = "ligature 1.2.0"

FINDINGS = [
    {
        "id": "swisstable-ligature-002",
        "pilot": "swisstable-verus",
        "stage": "phase-0-init",
        "command": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "./tools/ligature/ligature.pyz --descriptor /tmp/opencode/probe-closure-kind.json doctor"
        ),
        "tool": "ligature",
        "chain": "A.1",
        "symptom": (
            "`doctor` is the only ligature command that ignores the global `--descriptor` flag. "
            "Given an invalid descriptor named by `--descriptor`, it reads the ownership "
            "manifest's own `descriptor_path` instead, prints "
            "`user-owned  project-descriptor.json  schema: valid` and exits 0 -- a clean verdict "
            "about a file it never opened. `status`, `check --json` and `write-set-check` all "
            "honour the same flag on the same file (present-invalid / exit 5 / exit 2), so the "
            "four commands disagree about which descriptor is in force. Anyone using `doctor` as "
            "a pre-flight gate on a non-default descriptor gets a false pass."
        ),
        "repro_cmd": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "cp project-descriptor.json /tmp/opencode/d.bak && "
            "python3 -c \"import json,pathlib;p=pathlib.Path('project-descriptor.json');"
            "d=json.loads(p.read_text());d['closure_kind']='full';p.write_text(json.dumps(d,indent=2))\" && "
            "./tools/ligature/ligature.pyz doctor; echo \"doctor exit=$?\"; "
            "cp /tmp/opencode/d.bak project-descriptor.json && "
            "for c in status \"check --json\" \"write-set-check --json\" doctor; do "
            "./tools/ligature/ligature.pyz --descriptor /tmp/opencode/d.bak $c >/dev/null 2>&1; "
            "echo \"$c exit=$?\"; done"
        ),
        "exit_code": 0,
        "expected": (
            "`doctor` validates the descriptor `--descriptor` names, and exits 2 with "
            "`schema: invalid` for an invalid one -- the behaviour it does exhibit for the "
            "workspace's own project-descriptor.json, and the behaviour status/check/"
            "write-set-check already give."
        ),
        "actual": (
            "With `--descriptor <invalid file>`: doctor exits 0 and reports "
            "`user-owned  project-descriptor.json  schema: valid`. With the workspace file "
            "itself invalid (restored byte-for-byte afterwards, sha256 verified identical): "
            "doctor exits 2 and reports `schema: invalid (see check for detail)`. On the same "
            "invalid file: status exits 0 reporting present-invalid, check --json exits 5, "
            "write-set-check --json exits 2."
        ),
        "workaround": (
            "Validate a non-default descriptor with `ligature.pyz --descriptor <path> check "
            "--json` (exit 5 + a `next_action` naming the property) or `... write-set-check "
            "--json` (exit 2 + the property list on stderr); treat `doctor` as a check of the "
            "installation manifest only. Transcript at analysis/ligature/init-check.txt, probe "
            "P4b. Escalated to epic #1."
        ),
        "severity": "friction",
        "revisit_trigger": "Re-run probe P4b whenever `--descriptor` is expected to be honoured uniformly, and after any ligature release.",
        "pyz_sha256": SHA,
        "tool_path": "/home/goya/storage/full-ligature-port-workspace/swisstable-verus/" + PYZ,
        "tool_version": VERSION,
    },
    {
        "id": "swisstable-ligature-003",
        "pilot": "swisstable-verus",
        "stage": "phase-0-init",
        "command": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "./tools/ligature/ligature.pyz --descriptor <copy with '**/Cargo.toml' in "
            "write_set.protected_roots> write-set-check --json"
        ),
        "tool": "ligature",
        "chain": "A.1",
        "symptom": (
            "The `init --mode port` template seeds write_set.protected_roots with "
            "`**/Cargo.toml` and `**/build.rs`, which overlap the crate sources the same "
            "template's allowed_roots are meant to permit (`crates/*/src/`, and in this "
            "pilot `rust/*/src/`). Nothing at P0 rejects the overlap: the descriptor is "
            "`present-valid`, `write-set-check` reports no violation from it, and `check "
            "--json` exits 0. The overlap is only caught three stages later, by Stage 7's "
            "`validate-work-package` G13 -- which is how P1 hit it (chainlink #105, "
            "date-ligature-034). A pilot that copies the template verbatim therefore gets a "
            "descriptor that looks entirely healthy at every pre-flight gate and then fails at "
            "G13."
        ),
        "repro_cmd": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "python3 -c \"import json,pathlib;d=json.loads(pathlib.Path('project-descriptor.json').read_text());"
            "d['write_set']['protected_roots'][5]='**/Cargo.toml';"
            "pathlib.Path('/tmp/opencode/p.json').write_text(json.dumps(d,indent=2))\" && "
            "./tools/ligature/ligature.pyz --descriptor /tmp/opencode/p.json status | head -2"
        ),
        "exit_code": 0,
        "expected": (
            "A protected_roots pattern that also matches an allowed_roots path is reported as "
            "a violation (or at least a non-blocking finding) at P0, where the rest of the "
            "write-set boundary is validated."
        ),
        "actual": (
            "`descriptor: present-valid`; `write-set-check --json` exit 1 with the only "
            "violation being the out-of-tree probe file itself, not the overlap; `status "
            "--json` exit 0."
        ),
        "workaround": (
            "Use crate-scoped globs in protected_roots -- `rust/*/Cargo.toml`, "
            "`rust/*/build.rs` -- which is what this root's descriptor now carries. Transcript "
            "at analysis/ligature/init-check.txt, probe P7."
        ),
        "severity": "friction",
        "revisit_trigger": "Stage 7 (#29), where validate-work-package G13 first evaluates the overlap; and after any ligature release.",
        "pyz_sha256": SHA,
        "tool_path": "/home/goya/storage/full-ligature-port-workspace/swisstable-verus/" + PYZ,
        "tool_version": VERSION,
    },
    {
        "id": "swisstable-ligature-004",
        "pilot": "swisstable-verus",
        "stage": "phase-0-init",
        "command": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "./tools/ligature/ligature.pyz --descriptor <copy with verifier_policy "
            "{'default':'verus','defualt':'kani'}> status --json"
        ),
        "tool": "ligature",
        "chain": "A.1",
        "symptom": (
            "An unknown key inside `verifier_policy` is still accepted silently: "
            "`{\"default\": \"verus\", \"defualt\": \"kani\"}` is `present-valid`, and `check "
            "--json` exits 0 with zero findings. It is not inert either -- because "
            "verifier_policy's `additionalProperties` is a per-cluster override map, the typo "
            "is read back by `status --json` as a phantom cluster named `defualt`. So a "
            "misspelled verifier key does not fail, does not warn, and installs a policy entry "
            "for a cluster that does not exist. The only defence is reading the effective "
            "policy back out of `status --json`."
        ),
        "repro_cmd": (
            "cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
            "python3 -c \"import json,pathlib;d=json.loads(pathlib.Path('project-descriptor.json').read_text());"
            "d['verifier_policy']['defualt']='kani';"
            "pathlib.Path('/tmp/opencode/p.json').write_text(json.dumps(d,indent=2))\" && "
            "./tools/ligature/ligature.pyz --descriptor /tmp/opencode/p.json status --json | "
            "python3 -c 'import sys,json;print(json.load(sys.stdin)[\"descriptor\"][\"verifier_policy\"])'"
        ),
        "exit_code": 0,
        "expected": (
            "An unrecognised key inside verifier_policy is rejected at property level, as every "
            "other unknown descriptor key is (`$: unexpected property 'x'; permitted: ...`), "
            "or at minimum reported as a finding."
        ),
        "actual": (
            "`descriptor.state = present-valid`, exit 0, `verifier_policy` read back as "
            "{clusters: {defualt: kani}, default: verus, supporting: []}."
        ),
        "workaround": (
            "Always read `status --json`'s `descriptor.verifier_policy` back after editing the "
            "descriptor and assert it equals what was intended; this root's read-back is "
            "recorded in analysis/ligature/init-check.txt. Transcript, probe P8."
        ),
        "severity": "friction",
        "revisit_trigger": "Any edit to verifier_policy, and re-check after any ligature release (related to epic #1 #75).",
        "pyz_sha256": SHA,
        "tool_path": "/home/goya/storage/full-ligature-port-workspace/swisstable-verus/" + PYZ,
        "tool_version": VERSION,
    },
]


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[2]
    path = root / "findings" / "limitations.jsonl"
    # Existing lines are rewritten byte-for-byte: this issue appends, it
    # does not reformat records authored by #25/#26.
    kept = [l for l in path.read_text().splitlines() if l.strip()]
    have = {json.loads(l)["id"] for l in kept}
    added = []
    for f in FINDINGS:
        if f["id"] in have:
            continue
        kept.append(json.dumps(f))
        added.append(f["id"])
    path.write_text("\n".join(kept) + "\n")
    print("already present:", sorted(have) or "(none)")
    print("added:", added or "(none)")
    print("total:", len(kept))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())