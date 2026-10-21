#!/usr/bin/env python3
"""Append this issue's two findings to findings/limitations.jsonl. Idempotent.

Same discipline as analysis/ligature/write-findings-27.py: every pre-existing line is
preserved byte-for-byte, and re-running appends nothing. Run from swisstable-verus/:

    python3 analysis/ligature/write-findings-29.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "stage4-7"))
from path_root import pilot_root

ROOT = pilot_root()  # walks up to the dir holding project-descriptor.json
assert os.path.isfile(os.path.join(ROOT, "project-descriptor.json")), ROOT
os.chdir(ROOT)

PATH = "findings/limitations.jsonl"
PYZ_SHA = "30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd"
TOOL_PATH = "/home/goya/storage/full-ligature-port-workspace/swisstable-verus/tools/ligature/ligature.pyz"
TOOL_VERSION = ("ligature 1.2.1 (content hash "
                "sha256:2f607615543ca2670829989d5654f73b95a2474ca7763d4e644ce9af73218cd3, "
                "adjudicator zipapp attested)")

COMMON = {
    "pilot": "swisstable-verus",
    "tool": "ligature",
    "pyz_sha256": PYZ_SHA,
    "tool_path": TOOL_PATH,
    "tool_version": TOOL_VERSION,
}

FINDINGS = [
    {
        "id": "swisstable-ligature-010",
        "stage": "stage-4",
        "chain": "C.1",
        "command": ("cd swisstable-verus && python3 tools/ligature/ligature.pyz gate-g9   "
                    "# after approving the 6 staged bridges"),
        "symptom": (
            "G9 rejects every bridge the installed Stage 3 template can produce, and no "
            "pre-approval gate or template line warns about it. Two G9-only rules: "
            "`bridge_logic.premises` must be predicate application only ('no operators, "
            "literals, quantifiers or negation'), and `bridge_logic.bindings` keys must be "
            "snake_case ('it becomes a harness parameter name'). "
            "`.ligature/prompts/stage-3-bridge-drafting.md` states neither: its line 40 says "
            "`\"premises\": [\"<premise expression>\"]` and lines 112-114 describe a premise as "
            "'at least one premise expression ... imply the conclusion', and its only snake_case "
            "note is about the different field `required_local_facts[].fact_id` (line 33). "
            "Measured on an rsync scratch copy with all 36 approvable artifacts approved first "
            "(reviewer scratch-approval-proof): all 6 bridges staged at "
            "`OK: generated draft passes G1a/G1b immediate checks` exit 0, passed "
            "`validate-bridge` -> `OK: all bridges pass G1a/G1b (incl. conclusion consistency) "
            "and G2 boundary cross-reference (6 discovered)` exit 0, and were each written "
            "`approved: <path> (new) by scratch-approval-proof at 2026-10-02` exit 0 -- and then "
            "gate-g9 exited 1 with 6 [G9/error] findings: "
            "BR-CONTROLBYTES-CLEARDEAD-001 'unexpected character '=' at offset 27 in "
            "'self.ctrl(self.capacity()) == SENTINEL'', "
            "BR-CONTROLBYTES-SETDEAD-001 'unexpected character '<' at offset 5 in "
            "'slot < self.capacity()'', "
            "BR-GROUPPROBE-FREE-WINDOW-001 and BR-GROUPPROBE-WINDOW-001 both \"binding name "
            "'GROUP_WIDTH' is not snake_case\", "
            "BR-PROBESEQ-MASK-001 \"unexpected character '+' at offset 14 in 'capacity_mask + 1 "
            "== (1usize << capacity_bits)'\", "
            "BR-RAWINSERT-NONFULL-001 \"unexpected character '>' at offset 16 in "
            "'self.capacity() >= GROUP_WIDTH'\". `check-bridges` reports the identical 6. This is "
            "the tool's own template suggesting the shape its own gate rejects, so it is escalated "
            "as epic #1 #113. Re-checked while filing: #96 is genuinely fixed in 1.2.0 -- "
            "`gate-g9` and `check-bridges` both produce the correct 6 findings with a RELATIVE "
            "`--workspace .`, no ValueError -- so the 1.1.1 crash note on issue #29 is stale and "
            "an absolute `--workspace` is no longer needed."
        ),
        "repro_cmd": ("cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
                      "bash analysis/ligature/stage4-7/stage45-scratch-proof.sh && "
                      "sed -n '/post-approval gates/,$p' "
                      "analysis/ligature/stage4-7/stage45-scratch-proof.txt | head -40"),
        "exit_code": 1,
        "expected": ("the Stage 3 template states both G9 rules, or a pre-approval gate enforces "
                     "them, so an artifact G9 will certainly reject is never staged and promoted."),
        "actual": ("`draft`, `validate-bridge` and `approve` all pass at exit 0; the 6 G9 errors "
                   "appear only afterwards, against bridges a human has already approved, and only "
                   "when G9 is actually invoked -- `validate-bridge` alone never shows them."),
        "workaround": ("Do not treat `validate-bridge` exit 0 as G9. Run `gate-g9` (and "
                       "`check-bridges`) after approving the bridges, and re-cut any premise into "
                       "predicate application and any binding into snake_case before trusting the "
                       "promotion. The bridges in this pilot are approved-but-G9-failing and must "
                       "be re-drafted before the operator batch promotes them for real."),
        "severity": "blocker",
        "revisit_trigger": ("When the Stage 3 bridge template documents the two G9 rules or a "
                            "pre-approval gate enforces them, re-run "
                            "`bash analysis/ligature/stage4-7/stage45-scratch-proof.sh` and confirm "
                            "gate-g9 exits 0 with the 6 bridges approved."),
    },
    {
        "id": "swisstable-ligature-011",
        "stage": "stage-4.5",
        "chain": "C.1",
        "command": ("cd swisstable-verus && python3 tools/ligature/ligature.pyz accept-promotion "
                    "swisstable-verus-core --reviewer <human> --artifact docs/reliance-policy.md "
                    "--artifact evidence/E-001.json ... (48 artifacts)"),
        "symptom": (
            "Stage 4.5 is unreachable out of the box, and `accept-policy` cannot unblock it. "
            "`init` installs `docs/reliance-policy.md` as the pipeline template with its "
            "placeholders intact -- `Policy version: `<policy-name>@<major>.<minor>`` -- while the "
            "descriptor points `compatibility_policy.reliance_policy_path` at that same file, so it "
            "is automatically both an `--artifact` and the `--policy-path` of every "
            "`accept-promotion`. Measured on an rsync scratch copy after all 36 approvable "
            "artifacts approved at exit 0: `accept-promotion` exits 1 with `error: "
            "'docs/reliance-policy.md' must have exactly one 'Policy version: <name>@<major>.<minor>' "
            "marker line (docs/reliance-policy.template.md's own convention) -- found 0`. This "
            "fires BEFORE the human-ruling gate, so a completely correct Stage 4.5 sequence dies "
            "here regardless of rulings. `accept-policy --reviewer <name>`, the command documented "
            "as the sanctioned advance for ratifying that policy, fails the same way (exit 2, same "
            "message), because it needs the very marker line it exists to establish. And the file "
            "cannot be fixed by an agent: `docs/reliance-policy.md` is in "
            "`write_set.protected_roots` and the hash-pinned SKILL.md authority boundary 5 forbids "
            "writing into `protected_roots`. The template's project-specific section is also "
            "unfilled, so `policy_version` is one of four things a human must author. Escalated as "
            "epic #1 #114."
        ),
        "repro_cmd": ("cd /home/goya/storage/full-ligature-port-workspace/swisstable-verus && "
                      "bash analysis/ligature/stage4-7/stage45-scratch-proof.sh && "
                      "sed -n '/STAGE 4.5 BLOCKER/,/post-approval gates/p' "
                      "analysis/ligature/stage4-7/stage45-scratch-proof.txt | head -20"),
        "exit_code": 1,
        "expected": ("`accept-policy --reviewer <human>` puts an as-shipped policy template into "
                     "its accepted state, including stamping or validating `policy_version`; or "
                     "`doctor` reports the unfilled placeholder as a blocking condition."),
        "actual": ("both `accept-promotion` and `accept-policy` refuse the placeholder, the only "
                   "remedy is a hand edit to a protected root, and `doctor` lists "
                   "`docs/reliance-policy.md` as no problem at all (exit 0)."),
        "workaround": (
            "Do not edit the live-root policy file -- it is a protected root and a governance "
            "document. For proof purposes the Stage 4.5 scratch script fills the 4 placeholder "
            "lines ON THE SCRATCH COPY ONLY and then runs `accept-policy`; that is what proved "
            "Stage 4.5 succeeds end to end (`accepted: specs/_promotions/swisstable-verus-core.json` "
            "exit 0, `validate-promotion` exit 0). On the live root, filling the file and naming a "
            "real `Owner:` and `Policy version:` is a human authority step that must happen BEFORE "
            "the operator's approval batch, or the batch stops at the same error."),
        "severity": "blocker",
        "revisit_trigger": ("When `accept-policy` can accept a template whose `Policy version:` is "
                            "still a placeholder (or `init`/`doctor` refuses the placeholder), re-run "
                            "`bash analysis/ligature/stage4-7/stage45-scratch-proof.sh` and confirm "
                            "the STAGE 4.5 BLOCKER step exits 0 without any scratch edit."),
    },
]

existing = [json.loads(l) for l in open(PATH) if l.strip()]
have = {f["id"] for f in existing}
added = [f for f in FINDINGS if f["id"] not in have]
with open(PATH, "a") as fh:
    for f in added:
        fh.write(json.dumps({**COMMON, **f}) + "\n")
print(f"pre-existing lines: {len(existing)} (preserved byte-for-byte)")
print(f"appended: {[f['id'] for f in added] or 'nothing -- already present'}")
print(f"total now: {len(existing) + len(added)}")
