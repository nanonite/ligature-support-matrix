#!/usr/bin/env python3
"""Rewrite README.md's quoted `check-runbook-29.py` block from that script's real output.

    python3 analysis/ligature/stage4-7/refresh-quoted-block-29.py

check-runbook-29.py ends with a SELF_QUOTE check that fails unless the block README
presents as its output matches, line for line, what it just printed. That check makes
this script necessary rather than optional: any edit to the checker -- a reworded
message, one more or one fewer assertion -- invalidates the quote, and the fix is to
run this, never to retype the block.

The block is located by the same regex the checker uses, so the two cannot drift apart
in how they find it. Everything between the `; echo $?` command line and the echoed `0`
is replaced wholesale; the surrounding prose is untouched.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from path_root import pilot_root

ROOT = pilot_root()  # walks up to the dir holding project-descriptor.json
assert os.path.isfile(os.path.join(ROOT, "project-descriptor.json")), ROOT
os.chdir(ROOT)

CHECKER = "analysis/ligature/stage4-7/check-runbook-29.py"
README = "README.md"
# Must match the command line check-runbook-29.py looks for, `python3` included.
QUOTE_CMD = "$ python3 " + CHECKER + " ; echo $?"
QUOTE_RE = re.compile(
    r"(### Keeping this section honest.*?```\n"
    + re.escape(QUOTE_CMD) + r"\n).*?(\n0\n```)",
    re.S,
)

# `--block` gives exactly the text README's quoted block must contain, with SELF_QUOTE
# already in its OK form -- the fixed point a normal run would print. Its exit status is
# expected to be 1 on the very first refresh (the quote is stale by definition then), so
# the status is reported rather than treated as fatal; a FAIL on anything *else* means the
# refresh would bake a wrong block into the README, and that is refused.
proc = subprocess.run([sys.executable, CHECKER, "--block"], capture_output=True, text=True)
out = proc.stdout.rstrip("\n")
if proc.returncode != 0:
    other = [l for l in out.splitlines()
             if l.startswith("FAIL ") and "quoted check-runbook-29.py output" not in l]
    if other:
        print("refusing to refresh: the checker fails on something other than the quote:")
        for l in other:
            print(f"  {l}")
        sys.exit(1)
    print("checker exit=1 (the SELF_QUOTE check only) -- that is what this script fixes")
if not out.splitlines() or not out.splitlines()[0].startswith("derived from the staged"):
    sys.exit("unexpected --block output; check-runbook-29.py and this script have drifted")

readme = open(README).read()
m = QUOTE_RE.search(readme)
if m is None:
    sys.exit(f"could not find the quoted block under '### Keeping this section honest' in {README}")

new = readme[:m.start()] + m.group(1) + out + m.group(2) + readme[m.end():]
if new == readme:
    print(f"{README} already quotes this run's output verbatim; nothing to do")
else:
    open(README, "w").write(new)
    print(f"{README}: quoted block refreshed from {len(out.splitlines())} lines of real output")