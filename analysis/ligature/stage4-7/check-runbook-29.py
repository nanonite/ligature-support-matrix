#!/usr/bin/env python3
"""Fail (exit 1) if this README's Stage 4 / 4.5 / 7 claims are not the derived ones.

Same discipline as analysis/ligature/stage0-3/check-runbook.py: every number the
README quotes in "Stage 4 / 4.5 / 7" is derived here from a real file, and the
script exits 1 on any disagreement. Run from swisstable-verus/:

    python3 analysis/ligature/stage4-7/check-runbook-29.py

The last assertion also checks the block README quotes as this script's output, so
adding or rewording an assertion invalidates that quote. Regenerate it with:

    python3 analysis/ligature/stage4-7/refresh-quoted-block-29.py

`--block` prints the text that quote must contain and nothing else; the refresher
script consumes it.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from path_root import pilot_root

ROOT = pilot_root()  # walks up to the dir holding project-descriptor.json
assert os.path.isfile(os.path.join(ROOT, "project-descriptor.json")), ROOT
os.chdir(ROOT)

failures: list[str] = []
# Every line this script prints is accumulated here as well, so the block the README
# presents as this script's output can be compared against it line-for-line (the
# SELF_QUOTE check at the bottom). Printing directly would make that impossible.
report: list[str] = []


def emit(line: str = "") -> None:
    report.append(line)


def check(ok: bool, msg: str) -> None:
    emit(("OK   " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


readme = open("README.md").read()

# ------------------------------------------------------------------- artifact set
n_bound = len(glob.glob("rust/swisstable-verus-core/specs/_boundaries/*.json.draft"))
n_inter = len(glob.glob("rust/swisstable-verus-core/specs/_interactions/*.json.draft"))
n_bridg = len(glob.glob("rust/swisstable-verus-core/specs/_bridges/*.json.draft"))
n_wit = len(glob.glob("rust/swisstable-verus-core/specs/_witnesses/*.json.draft"))
n_conc = len(glob.glob("rust/swisstable-verus-core/specs/*.json.draft"))
n_ev = len(glob.glob("evidence/*.json"))
n_conf = len(glob.glob("specs/_conflicts/*.json.draft"))
accepted = 1 + n_ev + n_conf + n_bound + n_inter + n_bridg   # policy doc + the rest
emit(f"derived from the staged artifacts:\n"
     f"  boundaries              {n_bound}\n"
     f"  interactions            {n_inter}\n"
     f"  bridges                 {n_bridg}\n"
     f"  witnesses               {n_wit}\n"
     f"  concept specs           {n_conc}\n"
     f"  evidence (promoted)     {n_ev}\n"
     f"  conflict resolutions    {n_conf}\n"
     f"  accepted set size       {accepted}\n"
     f"      = docs/reliance-policy.md + {n_ev} evidence + {n_conf} conflict"
     f" + {n_bound} boundaries + {n_inter} interactions + {n_bridg} bridges\n")
check(accepted == 48, f"accepted set is 48 artifacts (derived {accepted})")

# ------------------------------------------------------- Stage 4.5 proof transcript
proof = open("analysis/ligature/stage4-7/stage45-scratch-proof.txt").read()
check("accepted: specs/_promotions/swisstable-verus-core.json" in proof
      and "OK: promotion receipt passes G1a and §7.1 checks" in proof,
      "Stage 4.5 is PROVEN in the scratch proof: accept-promotion exit 0 + validate-promotion exit 0")
m = re.search(r'promotion_id: "([^"]+)"', proof)
check(m is not None and m.group(1) == "PROM-SWISSTABLE-VERUS-CORE-001",
      f"promotion_id is PROM-SWISSTABLE-VERUS-CORE-001 (proof: {m and m.group(1)})")
m = re.search(r'^[0-9a-f]{64}  specs/_promotions/swisstable-verus-core\.json$', proof, re.M)
check(m is not None, "the scratch receipt's own sha256 is in the proof transcript")

n_g9 = len(re.findall(r'\[G9/error\] BR-', proof))
check(n_g9 >= 6, f"the proof records {n_g9} G9 findings (all 6 bridges fail G9)")

# `status`'s artifact tally is the one line in this section that has no independent
# derivation -- it is a property of the scratch copy's own pipeline state, so it can
# only be read out of the transcript. Added after a review found this README still
# quoting `artifacts (48): ... validated=1` from a superseded transcript, taken before
# ci/manifest/WP-SWISSTABLE-VERUS.json existed on the live root and was therefore
# rsynced into the scratch copy. That second `validated` artifact IS the manifest, so
# the count moves whenever this issue's own deliverable lands. Quote the transcript.
status_lines = re.findall(r"^artifacts \((\d+)\): promoted=(\d+), validated=(\d+)$", proof, re.M)
check(bool(status_lines), "the proof transcript records a `status` artifact tally")
if status_lines:
    total, promoted, validated = status_lines[-1]
    tally = f"artifacts ({total}): promoted={promoted}, validated={validated}"
    check(tally in readme, f"README's status tally is the transcript's own: {tally!r}")
    # 47 promoted = 36 approve()able artifacts + the 11 evidence records, which are
    # promoted by promote-evidence rather than approve(). Guard the invariant so a
    # future edit cannot quietly reconcile the two numbers to each other.
    n_approvable = n_bound + n_inter + n_bridg + n_conf
    check(int(promoted) == n_approvable + n_ev,
          f"promoted={promoted} = {n_approvable} approvable + {n_ev} promoted evidence")
    check(int(total) == int(promoted) + int(validated),
          f"total {total} = promoted {promoted} + validated {validated}")

# --------------------------------------------------------------- Stage 7 manifest
wp = json.load(open("ci/manifest/WP-SWISSTABLE-VERUS.json"))
check(wp["work_package"] == "WP-SWISSTABLE-VERUS", "manifest is WP-SWISSTABLE-VERUS")
check(wp["depends_on"] == [], "depends_on is empty (no other work package exists)")
check(wp["definition_of_done"]["required_guarantees"] == [],
      "required_guarantees is empty (single-WP crate; avoids P1's CG6 cycle)")

others = [p for p in glob.glob("ci/manifest/WP-*.json") if not p.endswith("WP-SWISSTABLE-VERUS.json")]
check(not others, f"no other work package manifest exists to depend on ({others})")

descriptor = json.load(open("project-descriptor.json"))
check(wp["write_policy"]["allowed_write_set"] == descriptor["write_set"]["allowed_roots"],
      "write_policy.allowed_write_set is a verbatim copy of the descriptor's allowed_roots")
check(wp["write_policy"]["protected_write_set"] == descriptor["write_set"]["protected_roots"],
      "write_policy.protected_write_set is a verbatim copy of the descriptor's protected_roots")

gi = {e["runner"]: e["hash"] for e in wp["gate_integrity"]}
for s in ("scripts/witness_renderer.py", "scripts/xml_escape.py"):
    real = sha256(s)
    check(gi.get(s) == real, f"gate_integrity[{s}] carries the REAL installed sha256 ({real})")
    check(s not in wp["write_policy"]["allowed_write_set"],
          f"{s} is not in allowed_write_set (G13)")

provided = [g["obligation_id"] for g in wp["definition_of_done"]["provided_guarantees"]]
precond = [g["bridge_id"] for g in wp["definition_of_done"]["required_preconditions_to_establish"]]
check(len(provided) + len(precond) == len(wp["obligations"]) == 36,
      f"36 obligations = {len(provided)} provided + {len(precond)} bridge-discharged")
check(len(set(provided)) == len(provided), "no obligation is listed twice in provided_guarantees")

# every precondition-kind constraint is either provided or bridge-discharged, never both
concepts = [json.load(open(f)) for f in glob.glob("rust/swisstable-verus-core/specs/*.json.draft")]
pre_ids = {f"{c['concept']}.{con['id']}" for c in concepts
           for con in c["constraints"] if con["kind"] == "precondition"}
bridge_files = sorted(glob.glob("rust/swisstable-verus-core/specs/_bridges/*.json.draft"))
bridged = {json.load(open(f))["callee_requirement"] for f in bridge_files}
bridge_ids = [json.load(open(f))["bridge_id"] for f in bridge_files]
check(not (pre_ids & set(provided)),
      f"no precondition-kind obligation is in provided_guarantees ({sorted(pre_ids & set(provided))})")
check(pre_ids - bridged == {"HashMix.C001"},
      f"the only precondition with no bridge is HashMix.C001 (derived {sorted(pre_ids - bridged)})")
# One entry per BRIDGE, not per distinct callee_requirement: BR-GROUPPROBE-FREE-WINDOW-001
# and BR-GROUPPROBE-WINDOW-001 both discharge GroupProbe.C001, so there are 6 bridges
# but only 5 distinct bridged obligations.
check(len(precond) == len(bridge_ids) == 6,
      f"one required_preconditions_to_establish entry per bridge: {len(precond)} entries, {len(bridge_ids)} bridges")
check(sorted(precond) == sorted(bridge_ids) == sorted(set(bridge_ids)),
      "the 6 entry bridge_ids are exactly the 6 promoted bridge ids, each once")
check(len(bridged) == 5 and "GroupProbe.C001" in bridged,
      f"5 distinct bridged obligations (GroupProbe.C001 has two bridges): derived {len(bridged)}")

# every obligation named really is declared by its own concept spec
declared = {f"{c['concept']}.{con['id']}" for c in concepts for con in c["constraints"]}
check(set(wp["obligations"]) <= declared,
      f"every manifest obligation is declared by a concept spec ({sorted(set(wp['obligations']) - declared)})")

# ------------------------------------------------------------ README text agreement
for claim, label in [
    ("accept-promotion swisstable-verus-core --reviewer", "README quotes the real accept-promotion command"),
    ("record-ruling --reviewer $R --verdict ratified", "README quotes the real record-ruling command"),
    ("scratch-approval-proof", "README names the scratch reviewer used in the proof"),
    ("PROM-SWISSTABLE-VERUS-CORE-001", "README quotes the real promotion_id"),
    ("ci/manifest/WP-SWISSTABLE-VERUS.json", "README names the Stage 7 manifest"),
    ("predicate application only", "README records the G9 failure mode"),
]:
    check(claim in readme, f"{label} ({claim!r})")

# The two command blocks the operator will actually run must each carry the whole
# 48-artifact set, one --artifact per line, and the ruling must cover exactly the
# same paths as the promotion. Counted here rather than trusted to the splice.
def command_block(verb: str) -> list[str]:
    """The --artifact paths of the README fenced code block that RUNS `verb`.

    Anchored on the opening fence, not on the verb alone: the section also quotes
    the command inline while describing the failures it used to produce, and that
    prose is not a runnable block.
    """
    fence = "\n```\npython3 tools/ligature/ligature.pyz " + verb + " "
    start = readme.index(fence) + len("\n```\n")
    return re.findall(r"^  --artifact (\S+)", readme[start:readme.index("\n```", start)], re.M)


ruled = command_block("record-ruling")
promoted = command_block("accept-promotion")
check(len(ruled) == accepted, f"README's record-ruling block lists all {accepted} artifacts ({len(ruled)})")
check(len(promoted) == accepted, f"README's accept-promotion block lists all {accepted} artifacts ({len(promoted)})")
check(ruled == promoted, "the ruling covers exactly the artifacts the promotion accepts")
check(sorted(ruled) == sorted(set(ruled)), "no artifact is listed twice in the ruling")

# ------------------------------------------------------------------- SELF_QUOTE
# README quotes this script's output verbatim in "Keeping this section honest".
# Two reviews in a row caught that quote going stale -- first the status tally, then
# this very block -- so it is verified instead of trusted. The block is generated by
# refresh-quoted-block-29.py; add or reword a check and you must run that, or this fails.
QUOTE_CMD = "$ python3 analysis/ligature/stage4-7/check-runbook-29.py ; echo $?"
QUOTE_RE = re.compile(
    r"### Keeping this section honest.*?```\n"
    + re.escape(QUOTE_CMD) + r"\n(.*?)\n0\n```", re.S)

SELF_MSG = "README's quoted check-runbook-29.py output is this run's own output"
TRAILER = "OK: every count and hash this README quotes is the derived one, not a remembered one."
# The expected block has to contain this very line, so build it with the OK form in
# place before deciding whether the README's quote matched. It is exactly what `--block`
# prints: the report, the blank separator, and the trailer.
m = QUOTE_RE.search(readme)
n_checks = sum(1 for l in report if l.startswith(("OK   ", "FAIL ")))
expected_block = "\n".join(report + [f"OK   {SELF_MSG} ({n_checks + 1} checks)", "", TRAILER])
if m is None:
    detail = "-- no quoted block found under 'Keeping this section honest'"
elif m.group(1) == expected_block:
    detail = ""
else:
    detail = "-- it differs; run refresh-quoted-block-29.py"
check(m is not None and m.group(1) == expected_block,
      f"{SELF_MSG} ({n_checks + 1} checks){detail}")

emit()
# `--block` prints exactly what README's quoted block must contain, i.e. expected_block:
# the report with SELF_QUOTE in its OK form, the blank separator, and the trailer. It is
# the fixed point a passing run prints, so it is what refresh-quoted-block-29.py writes.
# Printing `report` here instead would echo the FAIL form on the run that needs fixing,
# and refreshing would never converge. Any other FAIL line still shows up verbatim in it,
# which is how the refresher knows to refuse.
if "--block" in sys.argv:
    print(expected_block)
    sys.exit(1 if failures else 0)
for line in report:
    print(line)
if failures:
    print(f"FAIL: {len(failures)} disagreement(s) between this README and the derived facts:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(TRAILER)
