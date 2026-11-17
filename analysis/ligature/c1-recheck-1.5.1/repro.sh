#!/usr/bin/env bash
# C.1 re-check (chainlink #55): does status misclassify its own ownership
# manifest (ci/manifest/installation.json) as an invalid work package?
#
# Runs the original 1.0.0 repro -- `init --mode port` then `status --json` --
# in a throwaway root outside every pilot tree, using this pilot's pinned
# binary. Exit 0 means the 1.5.1 behaviour is correct (no such artifact).
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
pyz="$repo_root/tools/ligature/ligature.pyz"
tmp="${TMPDIR:-/tmp}/opencode/c1-recheck.$$"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

python3 "$pyz" init --mode port --name c1-recheck > init.stdout.txt
python3 "$pyz" status --json > status.json

python3 - "$tmp/status.json" <<'PY'
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
artifacts = d.get("artifacts", [])
install = [a for a in artifacts if a.get("path") == "ci/manifest/installation.json"]
work_packages = [a for a in artifacts if a.get("kind") == "work-package"]
state = d.get("installation_manifest", {}).get("state")

print("ligature:", d.get("product", {}).get("version"))
print("installation_manifest.state:", state)
print("ci/manifest/installation.json artifacts:", json.dumps(install))
print("work-package artifacts:", json.dumps(work_packages))

if install or state != "current":
    print("FAIL: the ownership manifest is still reported as an artifact, or installation is not current")
    raise SystemExit(1)
if work_packages:
    print("FAIL: a fresh init should have no work-package artifacts")
    raise SystemExit(1)
print("PASS: ci/manifest/installation.json is ownership metadata, not a work-package artifact")
PY
