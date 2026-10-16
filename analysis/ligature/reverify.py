#!/usr/bin/env python3
"""Re-run every repro_cmd in findings/limitations.jsonl from a clean copy.

chainlink #18's acceptance criterion: "A fresh agent re-runs every repro_cmd in
findings/limitations.jsonl from a clean copy." This is that harness.

Why it exists (see date-creusot-053): five repro_cmds in the findings file are
not runnable as written and two of them MUTATE tracked pipeline artifacts in
place without restoring them -- date-ligature-041 leaves
specs/_closure/date-creusot-core.json with closure_kind: "degraded", and
date-ligature-047 rewrites ci/results/feature_ledger.json. So nothing here ever
touches the live pilot: the workspace is rsync'd to a scratch root, and the
scratch copy is reset to the pristine baseline before EVERY single repro so no
command inherits another's mutation.

Documented substitutions (reported in the output):
  * the literal absolute workspace prefix is rewritten to the scratch root;
  * a repro that names `date-creusot/...` runs with the workspace root as cwd,
    one that uses bare `tools/ligature/...` / `specs/...` / `rust/...` paths runs
    with the pilot root as cwd (that is how each was originally recorded);
  * nix-shell repros (cargo creusot / cargo nextest / cargo build) are run
    separately by --slow, wrapping the bare command in
    `nix develop "path:<scratch>#date-creusot" -c bash -lc '...'` and
    substituting the explicit `path:` ref that #88/#89 documented.
  * only the dead syntax already described in `reverify-VERDICTS.md` is
    repaired in memory: the two `json.dump` typos and the three old
    `work-package.json` paths. The captured output names each repair; the
    append-only ledger is never rewritten.

Usage:
    python3 analysis/ligature/reverify.py --summary     # fast pass + counts
    python3 analysis/ligature/reverify.py --slow        # the nix-shell repros
    python3 analysis/ligature/reverify.py --slow --normalize-descriptor-overlap
                                                      # scratch-only #73 bypass
    python3 analysis/ligature/reverify.py <id> [<id>...]  # named findings only
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
WS = ROOT.parent
LEDGER = ROOT / "findings" / "limitations.jsonl"
SCRATCH = pathlib.Path(os.environ.get("REVERIFY_ROOT", "/tmp/opencode/reverify-8c"))
WORK = SCRATCH / "ws"
BASELINE = SCRATCH / "baseline"
OUTDIR = SCRATCH / "out"
TIMEOUT = 900
NORMALIZE_DESCRIPTOR_OVERLAP = False

# repros that need the nix dev shell; run only with --slow
NIX_SLOW = re.compile(r"cargo (creusot|nextest|build)|nix develop")

# key-behaviour probe: the single literal a finding's `actual` names, used only
# to flag a candidate for manual reading. NOT a verdict -- read the output.
PROBES = {
    "date-mcp-001": "Symbol not found",
    "date-mcp-002": "result_count",
    "date-ligature-001": "installation",
    "date-ligature-002": "unexpected property",
    "date-ligature-003": "closure_kind",
    "date-ligature-004": "doctor exit=",
    "date-ligature-005": "hash drift",
    "date-ligature-006": "skill authority hash",
    "date-ligature-007": "installation_manifest.state =",
    "date-ligature-008": "oracle_build_command",
    "date-ligature-009": "no boundary",
    "date-ligature-010": "is not one of",
    "date-ligature-011": "defualt",
    "date-ligature-012": "present-invalid",
    "date-ligature-013": "allowed_roots pattern",
    "date-ligature-014": "gate_integrity",
    "date-ligature-015": "DRIFTED",
    "date-ligature-016": "outside the project root",
    "date-ligature-017": "check exit=",
    "date-ligature-018": "reliance-policy.template.md",
    "date-ligature-019": "does not belong to any crate",
    "date-ligature-020": "promote-evidence",
    "date-ligature-021": "no template at",
    "date-ligature-022": "specs.search",
    "date-ligature-023": "exit-code",
    "date-ligature-024": "G1a/G1b immediate checks",
    "date-ligature-025": "exit=",
    "date-ligature-026": "rust/*/specs/**",
    "date-ligature-027": "next action",
    "date-ligature-028": "A-bad",
    "date-ligature-029": "stage-3-boundary-drafting.md",
    "date-ligature-030": "manifest not found",
    "date-ligature-031": "reviewer",
    "date-ligature-032": "manifest generation",
    "date-ligature-033": "runner not found",
    "date-ligature-034": "overlaps protected_write_set",
    "date-creusot-001": "Proved (",
    "date-creusot-035": "Goal Coma",
    "date-creusot-036": "Goal Coma",
    "date-creusot-037": "Goal Coma",
    "date-creusot-038": "Proved (",
    "date-creusot-039": "Proved (",
    "date-creusot-040": "creusot",
    "date-creusot-041": "Proved (",
    "date-ligature-035": "OK: all evidence records",
    "date-ligature-036": "absent from I",
    "date-creusot-042": "unresolved",
    "date-creusot-043": "absent from I",
    "date-ligature-037": "FileNotFoundError",
    "date-ligature-038": "FAIL",
    "date-creusot-044": "tests run",
    "date-creusot-045": "unknown case field",
    "date-ligature-039": "OK: 1 cluster",
    "date-ligature-040": "No such file",
    "date-ligature-041": "is not one of",
    "date-ligature-042": "filename says",
    "date-ligature-043": "HUMAN DECLARATION",
    "date-ligature-044": "",  # session-local script; not runnable
    "date-ligature-045": "feature_ledger",
    "date-creusot-047": "",
    "date-creusot-048": "unused import",
    "date-creusot-049": "Proved (",
    "date-creusot-050": "Proved (",
    "date-ligature-046": "",  # literal '...' placeholders; not runnable
    "date-ligature-047": "preserved",
    "date-ligature-048": "OK: 1 cluster",
    "date-creusot-051": "Proved (",
    "date-ligature-049": "violations",
    "date-ligature-050": "absent from I",
    "date-creusot-052": "OK: 1 cluster",
    "date-ligature-051": "is not schema-valid",
    "date-ligature-052": "never write into",
    "date-ligature-053": "RESOLVED",
    "date-creusot-053": "date-ligature-041",
    # chainlink #93: ligature 1.1.1 re-verification of the #92 collision
    "date-ligature-054": "refusing to overwrite the assurance report",
    "date-ligature-055": "refusing to overwrite the assurance report",
    "date-ligature-056": "held a generated feature ledger",
    "date-ligature-057": "adjudicator pin: mismatch",
    # chainlink #94: 1.1.1 authoring-capability refresh. Each probe is the
    # literal that finding's own `actual` names, so the harness can label it
    # -- the verdict itself still has to be read off the output.
    "date-ligature-094": "is not in the subpath of",
    "date-ligature-095": "no validator recognizes target",
    "date-ligature-096": "template_name",
    "date-ligature-097": "no concept spec under the search root",
    "date-ligature-098": "",
    "date-ligature-099": "SUPERSEDED",
    # chainlink #18 (attempt under 1.1.1): the .draft-vs-validator severity split.
    "date-ligature-100": "'review' is a required property",
}


def load():
    out = []
    for i, line in enumerate(LEDGER.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        d["_line"] = i
        out.append(d)
    return out


def make_baseline():
    """Pristine copy of the workspace, target/ and .git/ excluded.

    Two non-obvious choices, both fixed 2026-09-30 (chainlink #18):

    * The codesight index (1.6M) IS copied: the two `tool: mcp` repros
      (date-mcp-001/002) point CODE_INDEX_PATH at it, and with it excluded every
      MCP repro dies with `Repository not indexed` -- a harness artefact, not a
      finding.
    * `.venv/` is excluded and symlinked instead of copied. It is 89M, the
      scratch root is on a shared filesystem that several chainlink loops fill up
      simultaneously, and the harness needs two copies of the workspace at once
      (BASELINE + WORK). Copying it twice is what exhausted the disk on this
      run. The venv is read-only to every repro, so a symlink is equivalent.
    """
    if BASELINE.is_dir():
        shutil.rmtree(BASELINE)
    BASELINE.mkdir(parents=True)
    subprocess.run(
        ["rsync", "-a", "--exclude=target/", "--exclude=.git/", "--exclude=.venv/",
         str(WS) + "/", str(BASELINE) + "/"],
        check=True,
    )
    if NORMALIZE_DESCRIPTOR_OVERLAP:
        # Scratch-only preflight normalization. The live descriptor remains
        # untouched. Replacing the broad docs glob with the exact already
        # allowed evidence-promotion document removes only the known #73
        # allowed/protected overlap, so the behavioral repros can reach their
        # target command. The default pass deliberately does not do this.
        descriptor = BASELINE / "date-creusot" / "project-descriptor.json"
        data = json.loads(descriptor.read_text())
        roots = data["write_set"]["allowed_roots"]
        if "docs/*.md" not in roots:
            raise ValueError("expected docs/*.md overlap not found in scratch descriptor")
        roots.remove("docs/*.md")
        exact = "docs/evidence-promotion-exception.md"
        if exact not in roots:
            roots.append(exact)
        descriptor.write_text(json.dumps(data, indent=2) + "\n")


def link_venvs():
    """Symlink the excluded .venv dirs back into WORK so the mcp repros run."""
    for rel in ("tools/codesight-mcp/.venv",):
        src, dst = WS / rel, WORK / rel
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src)


def reset():
    if WORK.is_dir():
        for attempt in range(3):
            try:
                shutil.rmtree(WORK)
                break
            except OSError:
                time.sleep(2)  # another repro may still be draining the tree
        else:
            subprocess.run(["rsync", "-a", "--delete", str(BASELINE) + "/", str(WORK) + "/"],
                           check=True)
    shutil.copytree(BASELINE, WORK, symlinks=True)
    link_venvs()


def wrap_nix(cmd):
    """Run a bare cargo/nix repro inside the pinned dev shell."""
    ref = '"path:%s#date-creusot"' % WORK
    m = re.search(r"nix develop\s+(\S+)#date-creusot", cmd)
    if m:
        return cmd.replace(m.group(0), "nix develop %s" % ref)
    # no nix in the recorded command: it assumed an already-active shell
    return "nix develop %s -c bash -lc %s" % (ref, json.dumps(cmd))


def pick_cwd(raw):
    """Which directory a repro_cmd was recorded in.

    FIXED 2026-09-30 (chainlink #18, the 1.1.1 re-verification). The old test was
    the bare substring `"date-creusot" in raw`, which also matches the crate name
    `date-creusot-core`, the artifact name `date-creusot-core.json` and the nix ref
    `...#date-creusot`, so it routed those repros to the WORKSPACE root, where
    `rust/`, `tools/ligature/` and `ci/` do not exist. That is `date-creusot-054`
    in the findings file; it made date-ligature-047 die with "can't open file
    .../ws/tools/ligature/ligature.pyz" and four nix-shell repros
    (date-creusot-038/039/047/051) die with "cd: rust/date-creusot-core: No such
    file or directory" -- i.e. the harness silently failed the exact half the task
    asks a fresh agent to re-run.

    The test is now "is `date-creusot` used as a DIRECTORY here?", i.e. followed by
    `/` or by a shell delimiter/EOF -- which is true for `cd date-creusot`,
    `-C date-creusot` and `date-creusot/tools/...`, and false for
    `date-creusot-core`, `date-creusot-core.json` and `date-creusot-core.json.draft`.
    Two non-command forms are neutralised first: the nix flake ref (which is why
    the nix repros 038/039/047/051 must land in the pilot root) and a trailing
    `# ...` shell comment.

    Routing:
      * `date-creusot` used as a directory  -> WORKSPACE root;
      * otherwise                            -> the pilot root (bare
        `tools/ligature/...`, `specs/...`, `rust/...`, `ci/...` paths, which is how
        each of those was originally recorded).
    """
    cmd = re.sub(r"nix develop\s+\S+", "nix develop FLAKEREF", raw)
    cmd = re.sub(r"\s#.*$", "", cmd, flags=re.S)     # trailing shell comment
    if re.search(r"date-creusot(?=[/\s\"'`;,\)\]]|$)", cmd):
        return WORK
    return WORK / "date-creusot"


def repair_documented_repros(fid, raw):
    """Repair only the dead command syntax already documented in the verdicts.

    The ledger is append-only, so these substitutions are applied to the
    in-memory command that runs against the disposable copy. They do not
    rewrite the original repro_cmd or any pilot artifact.
    """
    cmd = raw
    changes = []
    if fid == "date-ligature-024":
        old = "json.dump(d,indent=2)+chr(10)"
        new = "json.dumps(d,indent=2)+chr(10)"
        if old not in cmd:
            raise ValueError("documented -024 json.dump typo not found")
        cmd = cmd.replace(old, new)
        changes.append("json.dump -> json.dumps (descriptor writer)")
    elif fid == "date-ligature-028":
        old = "print(json.dump(d))"
        new = "print(json.dumps(d))"
        if old not in cmd:
            raise ValueError("documented -028 json.dump typo not found")
        cmd = cmd.replace(old, new)
        changes.append("json.dump -> json.dumps (boundary draft input)")
    elif fid in {"date-ligature-032", "date-ligature-033", "date-ligature-034"}:
        old = "ci/manifest/work-package.json"
        new = "ci/manifest/WP-DATE-CREUSOT.json"
        if old not in cmd:
            raise ValueError("documented stale work-package path not found for " + fid)
        cmd = cmd.replace(old, new)
        changes.append(old + " -> " + new)
    return cmd, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="only these finding ids")
    ap.add_argument("--slow", action="store_true", help="include nix-shell repros")
    ap.add_argument("--summary", action="store_true", help="counts only")
    ap.add_argument("--normalize-descriptor-overlap", action="store_true",
                    help="on scratch only, replace docs/*.md with the exact evidence-promotion path to bypass the known #73 preflight conflict")
    args = ap.parse_args()
    global NORMALIZE_DESCRIPTOR_OVERLAP
    NORMALIZE_DESCRIPTOR_OVERLAP = args.normalize_descriptor_overlap

    OUTDIR.mkdir(parents=True, exist_ok=True)
    findings = [d for d in load() if not args.ids or d["id"] in args.ids]

    make_baseline()
    results = []
    for d in findings:
        fid, recorded = d["id"], d.get("repro_cmd", "")
        raw, repairs = repair_documented_repros(fid, recorded)
        rec = {"line": d["_line"], "id": fid, "tool": d.get("tool"),
               "severity": d.get("severity"), "recorded_exit": d.get("exit_code"),
               "probe": PROBES.get(fid, ""), "repro_repairs": repairs}
        rec["scratch_normalization"] = (
            "removed allowed docs/*.md; allowed docs/evidence-promotion-exception.md"
            if NORMALIZE_DESCRIPTOR_OVERLAP else None)
        if NIX_SLOW.search(raw) and not args.slow:
            rec["status"] = "SKIPPED-needs-nix"
            results.append(rec)
            if not args.summary:
                print("[skip-nix] %s" % fid, flush=True)
            continue
        reset()
        cmd = raw.replace(str(WS), str(WORK))
        if NIX_SLOW.search(raw):
            cmd = wrap_nix(cmd)
        cwd = pick_cwd(raw)
        rec["cwd"] = os.path.relpath(str(cwd), str(WORK)) or "."
        t0 = time.time()
        try:
            p = subprocess.run(["bash", "-c", cmd], cwd=str(cwd),
                               capture_output=True, text=True, timeout=TIMEOUT)
            out, err, code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            code = None
        blob = out + "\n" + err
        rec.update(exit=code, secs=round(time.time() - t0, 1),
                   probe_hit=bool(rec["probe"]) and rec["probe"] in blob,
                   exit_match=code == d.get("exit_code"),
                   substituted=cmd != recorded)
        repair_note = "; ".join(repairs) if repairs else "(none)"
        normalization_note = rec["scratch_normalization"] or "(none)"
        (OUTDIR / (fid + ".out")).write_text(
            "### SCRATCH NORMALIZATION\n%s\n### DOCUMENTED REPRO REPAIRS\n%s\n### CMD\n%s\n### EXIT\n%s\n### STDOUT\n%s\n### STDERR\n%s\n"
            % (normalization_note, repair_note, cmd, code, out, err))
        rec["status"] = ("CANDIDATE-MATCH" if rec["probe_hit"] and rec["exit_match"]
                         else "CANDIDATE-KEY" if rec["probe_hit"] else "CANDIDATE-NO")
        results.append(rec)
        if not args.summary:
            print("[%s] %-22s exit=%s recorded=%s probe=%r %.1fs"
                  % (rec["status"], fid, code, rec["recorded_exit"], rec["probe"], rec["secs"]),
                  flush=True)

    (SCRATCH / "results.json").write_text(json.dumps(results, indent=1))
    if not args.summary:
        return 0
    print("\n=== %d repro_cmds re-run from a clean copy ===" % len(results))
    c = Counter(r["status"] for r in results)
    for k, v in sorted(c.items()):
        print("  %3d  %s" % (v, k))
    print("  per-finding output: %s" % OUTDIR)
    print("  NOTE: these are CANDIDATE labels from a single literal probe, not verdicts.")
    print("        Read analysis/ligature/reverify-VERDICTS.md for the hand-assigned verdicts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
