#!/usr/bin/env python3
"""Hand-assigned verdict for every repro_cmd in findings/limitations.jsonl.

chainlink #18's second acceptance criterion: "a fresh agent re-runs every
repro_cmd in findings/limitations.jsonl from a clean copy." The harness
(`reverify.py`) does the re-running and labels each result CANDIDATE-* from one
literal probe; this file holds the VERDICT, which is assigned by reading the
captured output by hand. Render with:

    python3 analysis/ligature/verdicts-8c.py > analysis/ligature/reverify-VERDICTS.md

Verdict vocabulary (unchanged from the previous run so the two tables compare):

  MATCH              reproduces exactly as recorded -- the finding says it does
  STILL REPRODUCES   the behaviour is present today, verbatim or near-verbatim
  RESOLVED           no longer reproduces -- a later release fixed it
  PARTLY RESOLVED    one half fixed, the other half still live
  SUPERSEDED         the state the finding describes was moved on by other work
  CHANGED            still true in substance, different mechanism
  NOT-RUNNABLE       the repro cannot run as written (literal placeholder, or it
                     names a file/step that no longer exists)
  NOT-RUNNABLE(ENV)  the environment cannot realise it today (the nix dev shell
                     will not build -- see date-creusot-060)

Every `(id, verdict, evidence)` triple below was read from
`/tmp/opencode/reverify-8c/out/<id>.out` or a focused disposable-copy capture.
Focused captures use a scratch-only narrowing of the known invalid descriptor
glob when needed to get past its global preflight failure. No such normalization
was applied to the live pilot or the full 96-command harness run.
"""

RUN = {
    "binary": "ligature 1.3.11",
    "sha256": "446c87f93aa84c3f538710385706fcf753cd242a1282ba88faa1ad6722cb351f",
    "source_commit": "cdac78c21b6c32800b668b8fa2e17270f771d78c",
    "content_hash": "sha256:5f6e9d41af35a0ee219316b1d740547c84f8ccb8666afe21b3452bb638f1c2b8",
    "results": "/tmp/opencode/reverify-8c/results.json",
    "outputs": "/tmp/opencode/reverify-8c/out/",
    "executed": 96,
    "skipped": 0,
}

BUCKETS = [
    ("STILL REPRODUCES", "the finding's behaviour is present today"),
    ("MATCH", "reproduces exactly as recorded, which is what the finding says it does"),
    ("RESOLVED", "no longer reproduces -- a later ligature release fixed it"),
    ("PARTLY RESOLVED", "one half of the finding is fixed, the other half is still live"),
    ("SUPERSEDED", "the state the finding describes was moved on by other work"),
    ("CHANGED", "still true in substance, but a different mechanism"),
    ("NOT-RUNNABLE", "the repro_cmd cannot run as written (literal placeholder or dead file)"),
    ("NOT-RUNNABLE(ENV)", "the environment cannot realise it today (the nix dev shell will not build)"),
]

# id -> (verdict, one-line evidence)
V = {
 "date-mcp-001": ("STILL REPRODUCES", "get-callers exit 1, 'Symbol not found: include/date/date.h::days_from_civil#function'; get-file-outline still reports include/date/date.h as language 'c'"),
 "date-mcp-002": ("STILL REPRODUCES", "get-imports --direction importers exit 0, result_count 0"),
 "date-ligature-001": ("RESOLVED", "no artifact_id 'installation' in status --json at all; only installation_manifest.state"),
 "date-ligature-002": ("RESOLVED", "gate_integrity.details now names the offending key and the permitted set ('$.port_source: unexpected property commit; permitted: language, oracle_build_command, repository')"),
 "date-ligature-003": ("RESOLVED", "top-level closure_kind accepted: descriptor {closure_kind: deductive, state: present-valid}, exit 0"),
 "date-ligature-004": ('STILL REPRODUCES', "live 1.3.11 root: `doctor` exits 0 while `check --json` exits 5 and reports the descriptor's allowed/protected `docs/*.md` overlap; doctor should report `present-invalid` and non-clean status for the same descriptor"),
 "date-ligature-005": ("RESOLVED", "check exit 5, finding '.codex/skills/ligature/SKILL.md: hash drift' severity high, condition gate_integrity_failed"),
 "date-ligature-006": ("RESOLVED", "doctor now prints 'skill authority hash: drifted' (was 'verified')"),
 "date-ligature-007": ("RESOLVED", "installation_manifest.state = drifted instead of silently 'current'"),
 "date-ligature-008": ('STILL REPRODUCES', 'after filling `review.reviewer` and `port_source.repository`, P0 has 0 findings though `oracle_build_command` remains `cmake --build build --target oracle`; overall check exits 1 for unrelated setup findings. P0 should require explicit review of every shipped fixture value'),
 "date-ligature-009": ("PARTLY RESOLVED", "with `allowed_roots=[**]`, 1.3.11 check exits 5 and reports that `**` overlaps protected roots; this catches the all-inclusive pattern, but the same invalid descriptor preempts proof that nonexistent/out-of-root crate_dir values are rejected"),
 "date-ligature-010": ("RESOLVED", "'$.verifier_policy.default: creusot-rust is not one of [...]' -- field + permitted set + a next_action, and doctor prints present-invalid"),
 "date-ligature-011": ('RESOLVED', 'on a valid scratch descriptor, adding the unknown verifier_policy key `defualt` makes status report descriptor state `present-invalid`; the typo is rejected rather than silently accepted (#104, 1.2.2)'),
 "date-ligature-012": ("RESOLVED", "{default: verus, supporting: kani, fallback: creusot} is present-invalid, check exit 5 -- no longer accepted and silently discarded"),
 "date-ligature-013": ("RESOLVED", "check emits gate 'write-set' findings: 'outside every allowed_roots pattern and not accounted for by protected_roots...' for both probe files"),
 "date-ligature-014": ("RESOLVED", "gate_integrity {'details': 'descriptor declares no gate_integrity paths', 'state': 'unknown'} AND check exit 5 with a gate_integrity_failed condition"),
 "date-ligature-015": ("RESOLVED", "doctor prints DRIFTED for docs/reliance-policy.md with the exact 'record it with ligature accept-policy --reviewer <name>' remedy, and check emits the policy-drift finding"),
 "date-ligature-016": ("RESOLVED", "'reliance_policy_path /etc/hostname resolves outside the project root; fix the declaration to name the policy document inside the project'"),
 "date-ligature-017": ("RESOLVED", "llm_backend.kind is a closed enum (manual/claude/codex pass, anthropic/openai/ollama -> exit 5) and review.reviewed_at must be YYYY-MM-DD (2026-9-25, an ISO timestamp and 25-09-2026 all -> exit 5)"),
 "date-ligature-018": ('STILL REPRODUCES', 'the Stage 3 boundary prompt says `docs/reliance-policy.template.md`; init creates `docs/reliance-policy.md`, and `find` returns 0 template files (probe exit 0)'),
 "date-ligature-019": ('STILL REPRODUCES', 'normalized scratch: target `rust/date-creusot-core/rogue/evil.rs` passes crate-membership scope and reaches template rendering (error is `template ... references ...`, not a write-set rejection); `rust/rogue/evil.rs` is rejected as outside any declared crate. Draft/approve should enforce allowed_roots/protected_roots before rendering'),
 "date-ligature-020": ("RESOLVED", "promote-evidence exists and drafts/promotes cleanly (exit 0); the manual `mv` workaround is obsolete"),
 "date-ligature-021": ('RESOLVED', '`draft --help` exits 0 and lists all 11 canonical templates, including every template under `prompts/`; the tested short names `bridge`, `witness`, and `concept-drafting` are not documented template names, so their rejection does not reproduce the recorded discoverability failure'),
 "date-ligature-022": ('STILL REPRODUCES', 'with valid normalized descriptor and `specs_search_root: rust`, `check --json` exits 1 and includes six `applies_to unverifiable` info findings; `--help` has 0 specs-search matches. Ligature should resolve declared concepts against that root or reject the missing references'),
 "date-ligature-023": ('STILL REPRODUCES', 'scratch probe finds 0 `exit-code*` documents and help gives no per-command exit-code contract (one generic `exit code` mention); CLI should document status/exit semantics per command'),
 "date-ligature-024": ('STILL REPRODUCES', 'after the documented json.dumps repair, all three verifier_policy defaults (`creusot`, `kani`, `verus`) produce the same `OK: generated draft passes G1a/G1b immediate checks` (exit 0); Stage 3 should reject or flag evidence inconsistent with the declared verifier policy'),
 "date-ligature-025": ('RESOLVED', 'on a valid scratch descriptor, approving an already-promoted target exits 1 with `error: nothing was promoted: no staged draft at ...json.draft`; no traceback (#102, 1.2.2)'),
 "date-ligature-026": ('RESOLVED', 'sanctioned draft of a protected-tree artifact passes G1a/G1b (exit 0) and write-set-check reports `state=clean`, `violations=[]`; stray files in the same roots are caught as protected-write violations by -049 (#103/#114, 1.2.2; #132, 1.3.4)'),
 "date-ligature-027": ('STILL REPRODUCES', 'with staged interaction drafts present, `check next` exits 0 and returns `next action: [author-interaction] ...`; it does not surface the pending human approval. Next-action selection should identify the human checkpoint and reviewer action'),
 "date-ligature-028": ('PARTLY RESOLVED', "corrected repro on normalized scratch: interaction with `evidence_links: [E-999]` drafts with `OK: generated draft passes G1a/G1b immediate checks` (exit 0), but `approve` exits 1 with `[G4/error] ... evidence_links references 'E-999', but no valid workspace evidence record has that id` (#130, 1.3.4)"),
 "date-ligature-029": ('STILL REPRODUCES', 'normalized `check --json` exits 1 and reports six `applies_to unverifiable` findings for constraints whose ids are not resolvable from promoted concept specs; check should resolve or explicitly reject the missing source rather than leave permanent unverifiable notices'),
 "date-ligature-030": ("RESOLVED", "clean diagnostics both times: 'error: manifest not found: ...' / 'error: receipt not found: ...'"),
 "date-ligature-031": ("RESOLVED", "RE-PROBED: accept-promotion now refuses with 'refusing to mint a promotion receipt: no complete human ruling covers this accepted set', naming the uncovered artifacts and the `record-ruling` command. That is the second of the finding's two acceptable fixes, and it is real, not documentary"),
 "date-ligature-032": ('CHANGED', 'after the documented manifest-path repair, `generate-work-package --help` exits 0 and lists the command, but `doctor` still says the generator that reads promoted I/O and emits a manifest is not built; exact release introducing the CLI command is not identified'),
 "date-ligature-033": ('RESOLVED', 'after documented path repair, the two scripts are present and `validate-work-package ci/manifest/WP-DATE-CREUSOT.json` prints `OK: work package manifest passes G1a and §10.1 checks` (exit 0). Ligature 1.1+ init/migrate supplied the scripts; pilot manifest now pins actual hashes'),
 "date-ligature-034": ('RESOLVED', 'after documented path repair, `validate-work-package ci/manifest/WP-DATE-CREUSOT.json` passes G1a and §10.1 checks (exit 0); #133, 1.3.4'),
 "date-ligature-035": ('STILL REPRODUCES', 'the recorded `validate-evidence` repro exits 0 on 15 existing records; a sanctioned scratch `draft 0 evidence-intake evidence/E-999.json` probe exits 1 with `FAIL: generated draft has 1 G1a/G1b finding(s)` and `[G1a/error] ... `compile-time` is not one of [requirement, source-artifact, observed-behavior, test, comment]`'),
 "date-ligature-036": ("SUPERSEDED", "gate-r1-g16 still reports the same 5 'absent from I' errors, but the state has moved on: #95 staged 5 interaction drafts on the live root to resolve them, and #104 is re-verifying the escalations"),
 "date-ligature-037": ("NOT-RUNNABLE", "repro_cmd contains the literal '<path-to-a-hand-authored-.json-with-no-.draft-sibling>'; bash exits 2 on a syntax error before ligature runs"),
 "date-ligature-038": ("SUPERSEDED", "same as -036: the 5 blocking R1 findings are unchanged but #95 staged the interactions for them"),
 "date-ligature-039": ("RESOLVED", "gate-g14 exit 0, 'cluster date-creusot-core closes: closure_kind=deductive' and 'OK: 1 cluster(s) close under their declared profile'"),
 "date-ligature-040": ('PARTLY RESOLVED', 'the captured repro prints `No such file` for both local schema docs (overall shell exit 0 because the later help grep returns 0); current `draft --help` exposes closure-profile and degradation templates, so authoring exists but the packaged schemas have no documented local inspection path'),
 "date-ligature-041": ("RESOLVED", "closure_kind is ['deductive', 'bounded', 'partial']; deductive/bounded/partial all pass validate-closure and 'mixed'/'degraded' are both rejected with the permitted set named"),
 "date-ligature-042": ("RESOLVED", "no 'filename says' line: the manifest is ci/manifest/WP-DATE-CREUSOT.json and gate-g14 finds it"),
 "date-ligature-043": ("RESOLVED", "no 'HUMAN DECLARATION' text: generic_callees_type_universal_or_creusot_owned is now 'VERIFIED from artifact data, not taken on declaration', and 1.2.0 widened it further to every declared depends_on"),
 "date-ligature-044": ("NOT-RUNNABLE", "repro_cmd is `python3 /tmp/opencode/rerverify_v4.py`, a session-local script that no longer exists (Errno 2). A fresh agent could not have re-run this record at all -- which is why date-ligature-053 exists"),
 "date-ligature-045": ("RESOLVED", "gate-g14 contains no feature_ledger / assurance / well-founded / BLOCKED line; exit 0"),
 "date-ligature-046": ("NOT-RUNNABLE", "repro_cmd puts literal '...' in place of all five --proof paths: 'error: evidence path does not exist: ...'. Its substance is covered by the -040 verdict above"),
 "date-ligature-047": ('CHANGED', 'current `record-assurance` exits 0, writes `ci/results/feature_ledger.json`, and preserves 4 existing obligation records; report and assurance still share the configured path, so documented command order remains needed to retain the assurance report'),
 "date-ligature-048": ("MATCH", "record-assurance records all five obligations and gate-g14 then exits 0 with zero scc_wellfoundedness_discharged lines, which is what the manifest fix (required_guarantees: []) claims"),
 "date-ligature-049": ('RESOLVED', 'on scratch with a valid descriptor, stray `ci/manifest/PROBE.json` and `rust/.../specs/_interactions/I-PROBE.json` produce two `[protected-write]` violations and `write set: violations` (tool-reported exit 1); fixed by #132, 1.3.4'),
 "date-ligature-050": ("MATCH", "gate-r1-g16 exit 1 with exactly the 5 blocking 'absent from I' errors"),
 "date-ligature-051": ('PARTLY RESOLVED', 'on normalized scratch, `report feature-ledger` refuses to overwrite the assurance report (exit 1) and names `record-assurance`-last ordering or a separate report path; data loss is prevented, but the pilot still has one shared path and the separate-path remedy requires an operator-authorized manifest edit'),
 "date-ligature-052": ('PARTLY RESOLVED', '`report.emit=ci/results/feature_ledger.json` remains in protected `ci/manifest/**`; 1.3.11 names an order-based remedy, while separating paths still requires an operator-authorized manifest change. Unlike the old probe, write-set-check now catches stray protected files (#132, 1.3.4)'),
 "date-ligature-053": ('MATCH', 'the current harness and table are present; this repro reads the freshly generated 1.3.11 overlay'),
 "date-creusot-053": ('MATCH', 'the fresh harness reports `total 96`; its dead-repro scan includes the old work-package path in -032/-033/-034, repaired in memory as documented'),
 "date-ligature-054": ("MATCH", "report feature-ledger exit 1 with the refusal, md5 unchanged, gate-g14 exit 0 -- the documented order is no longer a silent trap"),
 "date-ligature-055": ("MATCH", "report exit=1 twice, report.emit == ci/results/feature_ledger.json, ci/manifest/** is protected_roots entry 2, SKILL.md boundary present (grep -c == 1)"),
 "date-ligature-056": ("MATCH", "with the ledger deleted, report feature-ledger writes the projection at exit 0 and record-assurance then prints 'warning: ... held a generated feature ledger, which was replaced by this' and restores md5 463583d9... at exit 0"),
 "date-ligature-057": ('RESOLVED', 'captured `version` is 1.3.11; installation.json pins product 1.3.11 and content hash `sha256:5f6e9d41…f1c2b8`; status reports `installation_manifest.state=current`, `doctor` exits 0 with `adjudicator pin: pinned`, and `version --verify` succeeds'),
 "date-ligature-094": ("RESOLVED", "epic #1 #96 is fixed in 1.2.0: with a promoted bridge present, gate-g9 no longer raises ValueError, it reports '[G9/error] BR-MIN-001: harness generated for creusot at ci/harness/BR-MIN-001.creusot.rs, but the project descriptor configures no verifier_backends.creusot command -- nothing was checked, so no result is recorded'. No traceback"),
 "date-ligature-095": ('RESOLVED', 'on normalized scratch, concept draft and `approve rust/date-creusot-core/specs/weekday.json` succeed; output says `approved: .../weekday.json (new)` (exit 0, #105, 1.2.2)'),
 "date-ligature-096": ('RESOLVED', '`draft --help` lists all 11 templates and says every template in prompts/ is listed (exit 0; 1.2.2 template-discovery work)'),
 "date-ligature-097": ('RESOLVED', 'after the prerequisite concept spec is approved, witness approval prints `approved: ...weekday.weekday_number.json (new)` (exit 0, #105, 1.2.2)'),
 "date-ligature-098": ("MATCH", "read-only command sweep: status 0, check 1, doctor 0, write-set-check 0, validate-work-package 1, gate-g14 0, gate-r1-g16 1, select-pilot-cluster 2"),
 "date-ligature-099": ("MATCH", "README.md carries the 1.1.1 authoring section at line 374 and 11 in-place SUPERSEDED markers"),
 "date-ligature-100": ("RESOLVED", "epic #1 #97 is fixed in 1.2.0: with the 5 staged interaction drafts on the tree, validate-interaction now exits 0 with 'OK: all interactions pass G1a/G1b (incl. computed eligibility), G15 protocol coverage, and R2 coverage (5 discovered)' and the probe literal \"'review' is a required property\" does not appear. The 5 medium findings and the human_decision_required condition are gone from check --json"),
 "date-creusot-001": ("NOT-RUNNABLE(ENV)", "the nix dev shell will not realise: cvc5-1.3.1 fetches CoCoALib-0.99800-trace.patch from a refs/heads/main URL that now 404s. See date-creusot-060"),
 "date-creusot-035": ("NOT-RUNNABLE(ENV)", "same -- the shell cannot be entered, so cargo creusot never runs"),
 "date-creusot-036": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-037": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-038": ("NOT-RUNNABLE(ENV)", "same (this one previously also failed the harness's cwd bug, now fixed -- the shell is the only remaining blocker)"),
 "date-creusot-039": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-040": ("NOT-RUNNABLE(ENV)", "same -- so `cargo creusot --help` cannot be timed in the pinned shell either"),
 "date-creusot-041": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-044": ("NOT-RUNNABLE(ENV)", "cargo nextest needs the same shell"),
 "date-creusot-047": ("NOT-RUNNABLE(ENV)", "the probe is a Rust source edit whose verification is `cargo creusot`"),
 "date-creusot-048": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-049": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-050": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-051": ("NOT-RUNNABLE(ENV)", "same"),
 "date-creusot-059": ("NOT-RUNNABLE(ENV)", "same -- filed by #104 after the shell broke"),
 "date-creusot-060": ('NOT-RUNNABLE(ENV)', 'the requested Nix realization cannot be reached in this sandbox: Nix daemon socket access returns `Operation not permitted` and the fetcher-lock path is read-only; the known cvc5 patch URL 404 remains NOT-RUNNABLE(ENV), not freshly reproduced'),
 "date-creusot-042": ("CHANGED", "after `extract-c-static` refreshes the report on normalized scratch, the five former R1 errors are classified as computed value-domain inquiries: the command reports `11 discovered, 6 checked against I` and `OK: R1 and G16 pass with 5 warning(s)` (exit 0); the five calls remain undeclared and are not counted as checked (#107, 1.2.2)"),
 "date-creusot-043": ("STILL REPRODUCES", "same 5 'absent from I' errors"),
 "date-creusot-045": ("MATCH", "'/tmp/neg.jsonl:1: unknown case field: extra', exit 2"),
 "date-creusot-052": ("MATCH", "extract-c-static writes '11 discovered, 11 resolved, 0 unresolved' and gate-g14 then exits 0 -- under the fixed manifest"),
 "date-creusot-053": ('MATCH', 'the fresh harness reports `total 96`; its dead-repro scan includes the old work-package path in -032/-033/-034, repaired in memory as documented'),
 "date-creusot-054": ("RESOLVED", "the cwd-routing defect is fixed: the regression probe now runs date-ligature-047 to completion ('recorded assurance: ci/results/feature_ledger.json ...') instead of dying with \"can't open file .../ws/tools/ligature/ligature.pyz\", and the four nix repros that it mis-routed are the only ones now blocked -- by the environment, not by the harness"),
 "date-creusot-055": ("MATCH", "the forged-Kani-record probe reproduces: gate-g14 rejects a hand-edited achievement with 'the recorded achievement disagrees with the manifest it would have been derived from', exit 1"),
 "date-creusot-056": ("MATCH", "planting a WP-KANI-OTHER kani result flips CG3 from VERIFIED to 'this workspace's artifacts cannot verify it ... That is a capability gap, not a checked condition', gate-g14 exit 1"),
 "date-creusot-057": ("MATCH", "a hand-written degradation record is refused: 'its own review block ... has no matching approval entry in ci/results/review_log.jsonl ... re-run the review through the sanctioned checkpoint' plus the record-ruling requirement; gate-g14 exit 1"),
 "date-creusot-058": ("SUPERSEDED", "the depends_on typo it recorded (WP-DATE-CREUSOT-CORE, a cluster name) was corrected in place by #104 at 22:30; gate-g14 is exit 0 and depends_on is []. The finding stands as the record of the intermediate state"),
 "date-ligature-101": ('RESOLVED', 'on normalized scratch, missing `.draft` approve/approve-pair calls exit 1 with `error: nothing was promoted: no staged draft at ...`; no FileNotFoundError traceback (#102, 1.2.2)'),
 "date-ligature-102": ("MATCH", "its repro's two grep assertions both hold on the current tree (`date-creusot(?=[/\\s\"'`;,\\)\\]]|$)` is present at reverify.py:251; the `analysis/codesight/index` baseline exclusion is gone, grep exit 1), and date-ligature-047 -- the repro the old routing killed -- runs to completion under this harness. Escalated to epic #1"),
 "date-creusot-061": ("NOT-RUNNABLE", "its repro_cmd starts `cd /tmp/opencode/104/dc` -- another chainlink worker's scratch copy, outside this pilot's scope and not guaranteed to exist. It is task #104's roll-up of the 18 epic-#1 escalations; the per-escalation verdicts belong in #104's own comment, not here. Judged by reading it: its substance (#90 still present) is independently confirmed by date-ligature-049 below"),
 "date-creusot-062": ("NOT-RUNNABLE", "repro begins with prose `RUN ON AN rsync SCRATCH COPY ONLY` parsed as shell; bash says `RUN: command not found`, then fails to find the manifest because cwd/path setup never ran. Do not repair it under this task's repair limits"),
}


def ledger_lines():
    import pathlib
    # resolve relative to the pilot root, so the script works from any cwd
    ledger = pathlib.Path(__file__).resolve().parents[2] / "findings" / "limitations.jsonl"
    out = []
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(line)
    return out


def emit_json(entries, counts):
    """A machine-readable twin of the table, so the verdicts are inspectable
    without re-running the harness (the raw per-finding captures live in the
    scratch root, which is /tmp and does not survive)."""
    import json
    rows = []
    for i, d in entries:
        v, ev = V[d["id"]]
        rows.append({
            "id": d["id"], "line": i, "verdict": v, "evidence": ev,
            "tool": d.get("tool"), "severity": d.get("severity"),
            "recorded_exit_code": d.get("exit_code"),
        })
    return json.dumps({
        "generated_for": "chainlink #18 Stage 8C",
        "binary": RUN["binary"], "pyz_sha256": RUN["sha256"],
        "source_commit": RUN["source_commit"], "content_hash": RUN["content_hash"],
        "findings_total": len(entries),
        "executed": RUN["executed"], "skipped": RUN["skipped"],
        "verdict_counts": counts,
        "generator": "analysis/ligature/verdicts-8c.py",
        "harness": "analysis/ligature/reverify.py --slow",
        "table": "analysis/ligature/reverify-VERDICTS.md",
        "per_finding": rows,
    }, indent=1, ensure_ascii=False)


def main():
    import json
    from collections import Counter

    entries = []
    for i, line in enumerate(ledger_lines(), 1):
        d = json.loads(line)
        entries.append((i, d))
    missing = [d["id"] for _, d in entries if d["id"] not in V]
    if missing:
        raise SystemExit("no verdict assigned for: " + ", ".join(missing))

    counts = Counter(V[d["id"]][0] for _, d in entries)
    old_counts = {
        "STILL REPRODUCES": 23, "MATCH": 18, "RESOLVED": 25,
        "PARTLY RESOLVED": 4, "SUPERSEDED": 3, "CHANGED": 3,
        "NOT-RUNNABLE": 4, "NOT-RUNNABLE(ENV)": 15,
    }
    moves = [
        ("date-creusot-042", "STILL REPRODUCES", "CHANGED", "1.2.2 / #107", "re-extraction classifies five missing-I calls as non-blocking value-domain warnings, but they remain uncounted against I"),
        ("date-ligature-011", "CHANGED", "RESOLVED", "1.2.2 / #104", "unknown verifier_policy keys are rejected"),
        ("date-ligature-021", "PARTLY RESOLVED", "RESOLVED", "1.2.2 template-discovery work; confirmed in 1.3.11", "draft help now enumerates all 11 canonical templates, resolving the incomplete discovery report"),
        ("date-ligature-025", "CHANGED", "RESOLVED", "1.2.2 / #102", "missing staged drafts now produce a diagnostic, not a traceback"),
        ("date-ligature-026", "STILL REPRODUCES", "RESOLVED", "1.2.2 / #103 and #114; confirmed with 1.3.4 / #132", "sanctioned spec pipeline artifacts are accounted for; stray protected files are violations"),
        ("date-ligature-028", "STILL REPRODUCES", "PARTLY RESOLVED", "1.3.4 / #130", "draft still stages a dangling evidence link, but approve rejects it at G4"),
        ("date-ligature-032", "STILL REPRODUCES", "CHANGED", "Observed in 1.3.11; exact introducing release not identified", "generate-work-package exists, but doctor still says the promoted-I/O generator is not built"),
        ("date-ligature-033", "STILL REPRODUCES", "RESOLVED", "Ligature 1.1+ init/migrate; confirmed in 1.3.11", "managed renderer scripts exist and the repaired manifest path validates"),
        ("date-ligature-034", "STILL REPRODUCES", "RESOLVED", "1.3.4 / #133", "work-package validation passes without the reported allowed/protected overlap"),
        ("date-ligature-049", "STILL REPRODUCES", "RESOLVED", "1.3.4 / #132", "write-set-check catches stray files in protected roots"),
        ("date-ligature-052", "MATCH", "PARTLY RESOLVED", "reclassification of existing behavior: 1.1.1 / #93 added the refusal and order remedy; 1.3.4 / #132 enforced protected-root writes, reconfirmed on 1.3.11", "no 1.2.1–1.3.11 release changed this pilot's shared path; the permitted order workaround exists while path separation still requires operator authority"),
        ("date-ligature-095", "STILL REPRODUCES", "RESOLVED", "1.2.2 / #105", "a concept spec draft can now be approved"),
        ("date-ligature-096", "STILL REPRODUCES", "RESOLVED", "1.2.2 template-discovery work", "draft help now lists all 11 templates"),
        ("date-ligature-097", "STILL REPRODUCES", "RESOLVED", "1.2.2 / #105", "witness approval succeeds after its concept spec is approved"),
        ("date-ligature-101", "MATCH", "RESOLVED", "1.2.2 / #102", "approving a missing draft now exits cleanly with an actionable message"),
        ("date-creusot-060", "MATCH", "NOT-RUNNABLE(ENV)", "No Ligature release change", "Nix daemon and fetcher-lock permissions block the current probe before the expected URL fetch"),
    ]
    open_gaps = {
        "date-ligature-004": ("`doctor` exit 0; live `check --json` exit 5 on the `docs/*.md`/`docs/reliance-policy.md` overlap.", "Have doctor report the descriptor as invalid and return a non-clean diagnostic when check rejects it."),
        "date-ligature-008": ("Focused fresh `init --mode port` probe: after setting reviewer, repository, and verifier default to valid non-template values, `check --json` exits 1 for unrelated setup findings but reports `P0 findings: 0`; the shipped `oracle_build_command` remains `cmake --build build --target oracle`.", "Require explicit review or replacement of every shipped placeholder, including the oracle command."),
        "date-ligature-009": ("With `allowed_roots=[\"**\"]`, `check --json` exits 5 and rejects the protected-root overlap. The original probe also sets an invalid absolute crate root, but that separate behavior is not established because descriptor validation stops first.", "No crate-root fix is proposed from this run; probe containment and existence separately with an otherwise valid descriptor before filing an upstream claim."),
        "date-ligature-018": ("The captured compound repro exits 0; its prompt excerpt says the policy is copied from `docs/reliance-policy.template.md`, `find` prints 0 matching files, and `docs/` contains `reliance-policy.md`.", "Point the prompt at the file `init` creates, `docs/reliance-policy.md`."),
        "date-ligature-019": ("The captured loop exits 0 after printing a template-rendering error for `rust/date-creusot-core/rogue/evil.rs`; the out-of-crate target prints `does not belong to any crate`. The in-crate rogue path is not rejected by the write-set boundary before rendering.", "Check allowed and protected roots before template rendering and reject the in-crate, out-of-write-set path."),
        "date-ligature-022": ("Focused normalized-scratch `check --json` exits 1 and contains six `applies_to unverifiable` findings with `specs_search_root=rust`; the captured command-help sweep exits 0 and finds zero `specs_search` references.", "Resolve concept specs under the declared search root or fail with a precise missing-reference diagnostic."),
        "date-ligature-023": ("The captured compound repro exits 0 and prints `0` for matching `exit-code*` docs and `1` for generic `exit code` help matches; it shows no per-command exit contract.", "Document exit status and machine-readable outcomes for each CLI command."),
        "date-ligature-024": ("After the documented `json.dump`→`json.dumps` scratch repair, all three verifier defaults (`creusot`, `kani`, `verus`) print `OK: generated draft passes G1a/G1b immediate checks`; the captured sweep exits 0.", "Apply the declared verifier policy when validating or drafting cross-verifier interaction evidence."),
        "date-ligature-027": ("The captured compound repro exits 0; `check next` prints `next action: [author-interaction] ligature draft interaction ...` while its staged interaction drafts already contain reviewer blocks, and it does not identify the pending human checkpoint.", "Expose the human checkpoint and required reviewer action as the next action when approval is pending."),
        "date-ligature-028": ("Focused scratch interaction draft with `evidence_links:[E-999]` exits 0 and prints `OK: generated draft passes G1a/G1b immediate checks`; sanctioned `approve --reviewer roger-codex-luna6` exits 1 with `[G4/error] ... evidence_links references 'E-999', but no valid workspace evidence record has that id`.", "Reject dangling evidence links at draft time or show the G4 blocker before staging the draft."),
        "date-ligature-029": ("Focused normalized-scratch `check --json` exits 1 and reports six G2+ `applies_to unverifiable` findings for the pilot's declared constraint IDs.", "Provide a sanctioned source for stable constraint IDs or report unresolved IDs as actionable errors."),
        "date-ligature-032": ("The captured compound repro exits 0: `doctor` prints that the promoted-I/O manifest generator is not built, while `validate-work-package` passes; focused `generate-work-package --help` exits 0 and lists the command.", "Make doctor describe the actual plan-driven command and distinguish it from automatic promoted-I/O generation."),
        "date-ligature-035": ("The recorded `validate-evidence` command exits 0 on 15 existing records. A sanctioned scratch draft of `evidence/E-999.json` with `kind=compile-time` exits 1: `FAIL: generated draft has 1 G1a/G1b finding(s)` and `[G1a/error] ... 'compile-time' is not one of ['requirement', 'source-artifact', 'observed-behavior', 'test', 'comment']`.", "Add a compile-time/const-eval evidence kind or a sanctioned documented mapping for proof artifacts."),
        "date-ligature-040": ("The recorded compound probe exits 0 but prints `No such file` for both `docs/closure-profile-schema.json` and `docs/degradation-record-schema.json`; focused `draft --help` exits 0 and lists closure-profile and degradation authoring templates.", "Document or provide a supported way to inspect the bundled schemas locally; the sanctioned draft/approve path already exists."),
    }
    decisions = [
        ("Pilot descriptor conflict", "The live `project-descriptor.json` has `allowed_roots: docs/*.md` overlapping protected `docs/reliance-policy.md`. `doctor` exits 0, but `check --json` exits 5; live `gate-g14` and `gate-r1-g16` each exit 1 before gate evaluation. This is a user-owned T2 scope decision; no descriptor was edited."),
        ("R1/G16 interaction approvals", "Against the C_static report currently on disk, normalized `gate-r1-g16` exits 1 with five high `absent from I` calls: YearMonthDay.ok→Year.ok, YearMonthDay.ok→Month.ok, YearMonthDayLast.ok→Year.ok, YearMonthDayLast.ok→Month.ok, and YearMonthDayLast.day→Year.is_leap; nine informational findings remain. The sanctioned `extract-c-static` refresh exercised by -042 reclassifies the five as warnings and exits 0, but reports only 6 of 11 call sites checked against I. After the descriptor decision, the operator should rerun extraction and decide whether warning-only, uncounted calls are acceptable or need reviewed interaction artifacts."),
        ("G14 scope and round_trip", "The normalized scratch G14 exits 0 with `closure_kind=deductive`, but says `0 obligation(s) in the transitive closure`. The saved Creusot `round_trip/proof.json` contains `vc_round_trip` with five Alt-Ergo child proof records. G14 therefore closes deductively but does not consume a round_trip obligation; no fresh Creusot proof run was possible in this environment."),
        ("Shared report path (date-ligature-047, -051, -052, -055)", "On normalized scratch, `record-assurance` exits 0 and writes `ci/results/feature_ledger.json`, preserving four prior obligation records. `report feature-ledger` now exits 1 and refuses that same path with an explicit safe order: run `record-assurance` last, or choose another `report.emit`. `ci/manifest/**` is protected, so path separation requires operator authority. `write-set-check` reports a stray probe file there as a violation. The tool now prevents destructive overwrite; decide whether to retain the order workaround or authorize a distinct report path. No upstream tool change is required by this observation."),
    ]

    w = []
    w += ["# Stage 8C re-verification verdicts (chainlink #18)", ""]
    w += ["This overlay rechecks all **%d** findings in `findings/limitations.jsonl` against **%s**." % (len(entries), RUN["binary"]), ""]
    w += ["Bundle SHA-256: `%s`; source commit: `%s`; attested content hash: `%s`." % (RUN["sha256"], RUN["source_commit"], RUN["content_hash"]), ""]
    w += ["The findings ledger is append-only; verdicts are recorded here. Every verdict was assigned from captured command output. The required unmodified `python3 analysis/ligature/reverify.py --slow` pass attempted all 96 commands with 0 skipped; its raw captures are preserved under `/tmp/opencode/reverify-8c-unmodified/`. A second 96-command pass used `python3 analysis/ligature/reverify.py --slow --normalize-descriptor-overlap`; it applied the documented scratch-only #73 descriptor normalization before each command. Focused scratch captures supplement findings `-008`, `-021`, `-022`, `-028`, `-029`, `-032`, `-035`, and `-040` where the recorded repro does not exercise the complete claim. This table uses the normalized pass only where the live descriptor preempts behavior. Render the overlay with `python3 analysis/ligature/verdicts-8c.py`.", ""]
    w += ["## What changed since the 1.2.0 table", ""]
    w += ["The previous table contained 95 rows; this table contains %d, including the later appended `date-creusot-062`. These are the bucket changes:" % len(entries), ""]
    for fid, before, after, release, why in moves:
        w.append("- `%s`: **%s → %s** — %s. %s." % (fid, before, after, release, why))
    w += ["", "The bundle itself was already 1.3.11 and the install pin was already current; no migration was needed. `version --verify` succeeds and `doctor` exits 0. `status` reports `descriptor.state=present-invalid`, however, because of the existing allowed/protected docs-pattern overlap.", ""]
    w += ["### Bucket counts", "", "| bucket | 1.2.0 | 1.3.11 |", "|---|---:|---:|"]
    for name, _meaning in BUCKETS:
        if old_counts.get(name, 0) or counts.get(name, 0):
            w.append("| %s | %d | %d |" % (name, old_counts.get(name, 0), counts.get(name, 0)))
    w += ["| **total** | **95** | **%d** |" % len(entries), ""]
    w += ["### Probe repairs", "", "Only the dead repro syntax already identified by the verdict notes was repaired in memory on scratch copies: `date-ligature-024` and `-028` use `json.dumps` instead of the recorded `json.dump`, and `-032/-033/-034` use `ci/manifest/WP-DATE-CREUSOT.json` instead of the stale `ci/manifest/work-package.json`. `findings/limitations.jsonl` was not changed. Each output capture records these repairs. Separately, the optional normalized pass replaces the overlapping `docs/*.md` allowed glob with `docs/evidence-promotion-exception.md` in scratch only; the live descriptor was not modified.", ""]
    w += ["The Nix-dependent Creusot repros remain **NOT-RUNNABLE(ENV)**. In this sandbox, Nix fails before the cvc5 fetch with a denied daemon socket or read-only fetcher-lock path; the reported patch URL 404 was not freshly reached. No flake edits were made.", ""]
    w += ["## Gate recheck", "", "On the live pilot, `check --json` exits 5 with `invalid_input`, `gate_integrity_failed`, and the `docs/*.md`/`docs/reliance-policy.md` overlap. Live `gate-g14` and `gate-r1-g16` both exit 1 on that descriptor diagnostic before evaluating their gates.", ""]
    w += ["To inspect the gates without changing the user-owned descriptor, a disposable copy replaced the overlapping docs glob with the exact already-allowed evidence-promotion document. On that scratch-only normalized copy, using the C_static report already on disk:", "", "- `check --json`: exit 1, 21 findings (16 info, 5 high); G14 and R1/G16 execute.", "- `gate-g14`: exit 0; `closure_kind=deductive`; 1 work package, 0 transitive obligations, 0 cycles discharged.", "- `gate-r1-g16`: exit 1; 5 high `absent from I` findings and 9 informational findings.", ""]
    w += ["The full normalized `date-creusot-042` repro reruns `extract-c-static` first. After that refresh, the 5 calls are classified as computed value-domain inquiries: R1/G16 exits 0 with 5 warnings (`11 discovered, 6 checked against I`). The calls remain undeclared and are not counted as checked; #107 changed their severity rung, not their presence. The current saved report has not been refreshed on the live root because the descriptor is invalid.", ""]
    w += ["The saved Creusot `round_trip/proof.json` has a `vc_round_trip` proof tree with five Alt-Ergo prover children. This is a saved artifact, not a fresh run. Because the current G14 closure has zero obligations, this recheck does not establish that G14 consumed `round_trip` as an obligation.", ""]
    w += ["## Ligature findings still active in 1.3.11", "", "The observations below are from the 1.3.11 captures. ‘Normalized scratch’ means only the conflicting descriptor glob was narrowed in a disposable copy so the probe could reach its target; the live pilot configuration was not edited.", "", "| finding | observed output and exit | what Ligature should do |", "|---|---|---|"]
    for i, d in entries:
        fid = d["id"]
        if d.get("tool") == "ligature" and V[fid][0] in ("STILL REPRODUCES", "PARTLY RESOLVED", "CHANGED") and fid in open_gaps:
            obs, expected = open_gaps[fid]
            w.append("| `%s` (%s) | %s | %s |" % (fid, V[fid][0], obs, expected))
    w += ["", "These are upstream-ready descriptions only where the observed issue is a product behavior. The shared report path and human approvals below require pilot decisions.", ""]
    w += ["## Operator decisions", ""]
    for title, detail in decisions:
        w += ["### %s" % title, "", detail, ""]
    w += ["## Per-finding overlay", ""]
    for i, d in entries:
        v, ev = V[d["id"]]
        w += ["### `%s` — %s" % (d["id"], v), "", "`line %d` · `tool: %s` · `severity: %s` · `recorded exit_code: %s`" % (i, d.get("tool"), d.get("severity"), d.get("exit_code")), "", ev, ""]
    return "\n".join(w)


if __name__ == "__main__":
    import argparse
    import pathlib
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--json", action="store_true", help="emit the machine-readable twin")
    a = ap.parse_args()
    if a.json:
        _entries = []
        import json as _json
        for _i, _line in enumerate(ledger_lines(), 1):
            _entries.append((_i, _json.loads(_line)))
        _counts = {}
        for _, _d in _entries:
            _v = V[_d["id"]][0]
            _counts[_v] = _counts.get(_v, 0) + 1
        print(emit_json(_entries, _counts))
    else:
        print(main())
