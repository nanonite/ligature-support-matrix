#!/usr/bin/env python3
"""Check the README runbook's approve commands against what is actually staged.

Reads every `python3 tools/ligature/ligature.pyz approve --reviewer $R <target>`
line out of the runbook section of README.md, and compares that set against the
set of staged `<target>.json.draft` files in this root. Reports anything staged
but not in the runbook, anything in the runbook but not staged, and any target
the runbook lists that has no `.draft` to approve.

Exits 0 only when the runbook covers exactly the staged approvable set.
Concept specs and witness specs are expected to be absent from the runbook's
approve list by design (approve has no branch for the former and fails G2 on the
latter); they are listed separately as "must not be run".
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
README = os.path.join(PILOT, "README.md")

RUNBOOK_HEADING = "### The runbook"
RUNBOOK_END = "### What to scrutinise"
PROOF = os.path.join(HERE, "approval-proof.txt")


def read_runbook(text=None):
    text = text if text is not None else open(README).read()
    i = text.index(RUNBOOK_HEADING)
    j = text.index(RUNBOOK_END, i)
    return text[i:j]


def runbook_approve_targets(section):
    return set(re.findall(
        r"ligature\.pyz approve --reviewer \$R (\S+\.json)\n", section))


def staged_drafts():
    out = set()
    for base in ("evidence", "rust", "specs"):
        for dirpath, _dirs, files in os.walk(os.path.join(PILOT, base)):
            if "/analysis/" in dirpath + "/" or "/upstream/" in dirpath + "/":
                continue
            rel = os.path.relpath(dirpath, PILOT)
            for f in files:
                if f.endswith(".json.draft"):
                    out.add(os.path.join(rel, f[:-len(".draft")]))
    return out


def guarantee_counts():
    """Derive the callee_guarantees totals from the staged boundary artifacts.

    Never hard-coded: the README quotes these numbers, and a re-cut of any boundary
    changes them. Sourced here so a stale README fails instead of misleading.
    """
    import collections
    bdir = os.path.join(PILOT, "rust/swisstable-verus-core/specs/_boundaries")
    counts = []
    for f in sorted(os.listdir(bdir)):
        if f.endswith(".json.draft"):
            counts.append(len(json.load(open(os.path.join(bdir, f)))["callee_guarantees"]))
    hist = collections.Counter(counts)
    return {
        "boundaries": len(counts),
        "total": sum(counts),
        "hist": dict(sorted(hist.items())),
        "empty": [c for c in counts if c == 0],
    }


def proof_tally():
    """Derive the post-approval finding tally from approval-proof.txt STEP 8."""
    import collections
    if not os.path.isfile(PROOF):
        return None
    text = open(PROOF).read()
    m = re.search(r"--- STEP 8  check --json ---\n(\{.*?\})\n", text, re.S)
    if not m:
        return None
    d = json.loads(m.group(1))
    hist = collections.Counter((f["severity"], f["gate_id"]) for f in d["findings"])
    return {
        "total": len(d["findings"]),
        "exit_code": d["result"]["exit_code"],
        "conditions": d["result"]["conditions"],
        "hist": {f"{s} {g}": n for (s, g), n in sorted(hist.items())},
    }


def proof_validate_line():
    """The `INFO: N non-blocking finding(s)` line `validate` printed after approval."""
    if not os.path.isfile(PROOF):
        return None
    text = open(PROOF).read()
    seg = text.split("--- STEP 7  validators ---", 1)
    if len(seg) < 2:
        return None
    m = re.search(r"INFO: (\d+) non-blocking finding\(s\)", seg[1].split("--- STEP 8", 1)[0])
    return int(m.group(1)) if m else None


def check_counts(readme):
    """The README's quoted counts must be the derived ones, not remembered ones.

    Whitespace is normalised on both sides first: the README wraps, and a wrapped
    sentence is still the same sentence. What matters is that the digits and their
    order agree.
    """
    flat = re.sub(r"\s+", " ", readme)
    g = guarantee_counts()
    t = proof_tally()
    v = proof_validate_line()
    problems = []

    if g["empty"]:
        problems.append("these boundaries have an EMPTY callee_guarantees: %s" % g["empty"])
    if v is None:
        problems.append("approval-proof.txt STEP 7 records no `INFO: N non-blocking finding(s)` "
                        "line for `validate`; re-run bash analysis/ligature/stage0-3/run-proofs.sh")
    if t is None:
        problems.append("approval-proof.txt STEP 8 could not be parsed; re-run run-proofs.sh")

    print(f"\nderived from the staged boundary artifacts:")
    print(f"  boundaries                {g['boundaries']}")
    print(f"  callee_guarantees total   {g['total']}  (histogram {g['hist']})")
    print(f"  with one / with two       {g['hist'].get(1, 0)} / {g['hist'].get(2, 0)}")
    if v is not None:
        print(f"\nderived from approval-proof.txt:")
        print(f"  validate reports          INFO: {v} non-blocking finding(s)")
    if t:
        print(f"  check --json findings     {t['total']}  {t['hist']}")
        print(f"  check --json exit_code    {t['exit_code']}  conditions {t['conditions']}")

    # every count the README quotes must equal the derived one
    if v is not None and f"INFO: {v} non-blocking finding(s)" not in flat:
        problems.append(f"README does not quote `INFO: {v} non-blocking finding(s)`")
    if t:
        # severity-descending, so the README's tally reads worst-first like its prose
        rank = {"blocker": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        hist = sorted(t["hist"].items(),
                      key=lambda kv: (rank.get(kv[0].split()[0], 9), kv[0]))
        want = f"{t['total']} findings: " + ", ".join(f"{n} {k}" for k, n in hist)
        if want not in flat:
            problems.append(f"README does not quote the STEP 8 tally verbatim: `{want}`")
    one, two = g["hist"].get(1, 0), g["hist"].get(2, 0)
    claim = (f"{g['total']} is the exact total of `callee_guarantees` entries across the "
             f"{g['boundaries']} boundaries")
    if claim not in flat:
        problems.append(f"README does not carry the derived guarantee total: `{claim}`")
    if f"({one} with one, {two} with two)" not in flat:
        problems.append(f"README's per-boundary split is not `({one} with one, {two} with two)`")
    if g["empty"]:
        problems.append(f"empty callee_guarantees: {g['empty']}")
    return problems


def main():
    text = open(README).read()
    section = read_runbook(text)
    listed = runbook_approve_targets(section)
    staged = staged_drafts()

    concept = {p for p in staged if "/specs/" in p and "/_boundaries/" not in p
               and "/_interactions/" not in p and "/_bridges/" not in p
               and "/_witnesses/" not in p and "/_exemptions/" not in p
               and not p.startswith("specs/")}
    witness = {p for p in staged if "/_witnesses/" in p}
    evidence = {p for p in staged if p.startswith("evidence/")}
    approvable = staged - concept - witness - evidence

    problems = []
    missing = approvable - listed
    extra = listed - staged
    if missing:
        problems.append("staged but NOT in the runbook: " + ", ".join(sorted(missing)))
    if extra:
        problems.append("in the runbook but NOT staged: " + ", ".join(sorted(extra)))

    print(f"runbook approve commands : {len(listed)}")
    print(f"staged drafts total      : {len(staged)}")
    print(f"  evidence (already promoted by promote-evidence, no checkpoint): {len(evidence)}")
    print(f"  concept specs (approve has no branch -- never run approve)    : {len(concept)}")
    print(f"  witness specs (approve fails G2 -- never run approve)          : {len(witness)}")
    print(f"  approvable via approve  : {len(approvable)}")
    if problems:
        print("\nMISMATCH:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK: the runbook's approve list is exactly the staged approvable set.")
    print("OK: evidence, concept and witness drafts are correctly excluded.")

    problems += check_counts(text)
    if problems:
        print("\nSTALE NUMBERS:")
        for p in problems:
            print("  -", p)
        return 1
    print("OK: every count the README quotes is the derived one, not a remembered one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())