#!/usr/bin/env python3
"""Replay the historical 96 IDs using the installed pilot bundle.

Keep the existing harness's documented repairs and per-command captures.
Reset scratch with checksum-based rsync instead of recopying unchanged
files; verify that reset restores same-size, same-mtime edits and deletes
new files before trusting it. Nix commands use shell quoting, not JSON
quoting. Set XDG_CACHE_HOME outside the read-only home when needed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    pilot = here.parents[2]
    ids = [row["id"] for row in json.loads((here / "baseline-replay/results.json").read_text())]
    assert len(ids) == len(set(ids)) == 96
    os.environ["REVERIFY_ROOT"] = str(args.scratch.resolve())
    spec = importlib.util.spec_from_file_location("historical_replay", pilot / "analysis/ligature/reverify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TIMEOUT = args.timeout

    def reset() -> None:
        module.WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "rsync", "-a", "--checksum", "--delete",
            str(module.BASELINE) + "/", str(module.WORK) + "/",
        ], check=True)
        module.link_venvs()

    original_baseline = module.make_baseline

    def checked_baseline() -> None:
        original_baseline()
        reset()
        path = module.WORK / "date-creusot/README.md"
        original = path.read_bytes()
        info = path.stat()
        path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        extra = module.WORK / "date-creusot/analysis/replay-reset-probe.txt"
        extra.write_text("must be removed by reset\n")
        reset()
        assert path.read_bytes() == original and not extra.exists()
        args.scratch.mkdir(parents=True, exist_ok=True)
        (args.scratch / "run.json").write_text(json.dumps({
            "ids": ids,
            "timeout_seconds": args.timeout,
            "bundle_sha256": hashlib.sha256((pilot / "tools/ligature/ligature.pyz").read_bytes()).hexdigest(),
            "ledger_sha256": hashlib.sha256(module.LEDGER.read_bytes()).hexdigest(),
            "reset": "rsync -a --checksum --delete; same-size/same-mtime corruption and extra-file self-check passed",
            "nix_quoting": "shlex.quote instead of JSON string quoting",
            "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME"),
        }, indent=2) + "\n")

    def wrap_nix(command: str) -> str:
        ref = shlex.quote("path:" + str(module.WORK) + "#date-creusot")
        match = re.search(r"nix develop\s+(\S+)#date-creusot", command)
        if match:
            return command.replace(match.group(0), "nix develop " + ref)
        return "nix develop " + ref + " -c bash -lc " + shlex.quote(command)

    module.reset = reset
    module.make_baseline = checked_baseline
    module.wrap_nix = wrap_nix
    sys.argv = ["reverify.py", "--slow", *ids]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
