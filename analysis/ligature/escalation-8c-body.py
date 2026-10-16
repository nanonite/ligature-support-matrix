"""
Draft body for the epic #1 subissue filed by chainlink #18.
Kept in the pilot as a file so the exact text that was filed is reviewable.
"""
BODY = r"""Pilot: date-creusot (P1), chainlink #18 (Stage 8C: validate-closure, gate-g14, report; re-verify findings).
Binary: date-creusot/tools/ligature/ligature.pyz, ligature 1.1.0.
PINNED BINARY SHA256 (from date-creusot/tools/ligature/SHA256SUMS, verified with `sha256sum -c SHA256SUMS` -> ligature.pyz: OK):
  ede2514e9070a628b30fe3a0a3ead9e81574ac041f692b7c498a7fb88bd0883f  ligature.pyz

SUMMARY
  Two Stage 8C commands write the same canonical path with mutually incompatible
  schemas. Running the pipeline in the order the pipeline is named in -- `report`
  first, then the closure gate -- silently invalidates the evidence the closure
  gate reads, and gate-g14 then reports the whole cluster BLOCKED on six errors
  that were not true one command earlier. This is the ordering trap Stage 8C
  exists to be immune to.

EXACT COMMAND RUN (cwd = date-creusot/, on a tree where `record-assurance` has
just populated ci/results/feature_ledger.json with the five Creusot obligation
records; verified on a clean rsync copy of the pilot, byte for byte):

  $ md5sum ci/results/feature_ledger.json
  463583d9eda1ed0292800703bf2835cf  ci/results/feature_ledger.json
  $ python3 tools/ligature/ligature.pyz gate-g14 ; echo "EXIT=$?"
  cluster 'date-creusot-core' closes: closure_kind=deductive, 1 work package(s), ...
  OK: 1 cluster(s) close under their declared profile, 0 released under an accepted degradation record
  EXIT=0

  $ python3 tools/ligature/ligature.pyz report feature-ledger ; echo "EXIT=$?"
  wrote ci/results/feature_ledger.json (0 declared features -- nothing to check)
  EXIT=0

  $ md5sum ci/results/feature_ledger.json
  c8571e0944ad0eaefb60adf3a194bbea  ci/results/feature_ledger.json

  $ python3 tools/ligature/ligature.pyz gate-g14 ; echo "EXIT=$?"
  cluster 'date-creusot-core' is BLOCKED: closure not established
    - [G14/error] WP-DATE-CREUSOT: assurance report ci/results/feature_ledger.json is not schema-valid: 'work_package' is a required property
    - [G14/error] Weekday.C1: WP-DATE-CREUSOT provides this obligation but recorded no achieved assurance for it -- record one from this work package's proof certificates with `ligature record-assurance WP-DATE-CREUSOT --proof Weekday.C1=<path>`
    - [G14/error] Weekday.C2: ... (same)
    - [G14/error] Weekday.C3: ... (same)
    - [G14/error] YearMonthDay.C2: ... (same)
    - [G14/error] YearMonthDayLast.C1: ... (same)
    - [G14/error] [generic_callees_type_universal_or_creusot_owned] date-creusot-core: ... this closure's artifacts cannot verify it: no achieved assurance record at all for WP-DATE-CREUSOT -- ... releasing this cluster needs a degradation record naming this condition with a tracking issue
  FAIL: 1 cluster(s) blocked, 0 not blocked
  EXIT=1

EXIT CODE: 1 for gate-g14 after the report; 0 for gate-g14 before it; 0 for
`report feature-ledger` itself, which prints no warning that it overwrote
anything.

EXPECTED
  The generated feature-ledger projection and the work package's assurance report
  are distinct artifacts at distinct paths, so regenerating one cannot invalidate
  the other; or `report feature-ledger` refuses to overwrite a path that currently
  holds an assurance report, instead of doing it silently at exit 0.

ACTUAL
  The work-package manifest names `report.emit = "ci/results/feature_ledger.json"`,
  and `record-assurance` writes the assurance report to exactly that path -- the
  same file `report feature-ledger` regenerates. One command turns a closing gate
  into a blocking one. `gate-g14` is not wrong here: it is right to reject a
  schema-invalid assurance report. The defect is the collision and the silence.

  It is exactly reversible: re-running `record-assurance` with all five `--proof`
  flags restores the file byte-identically (md5 back to 463583d9eda1ed0292800703bf2835cf)
  and gate-g14 back to exit 0. That is how this was found -- it happened to the
  live pilot root during this issue and cost one command to recover.

SECONDARY: the remedy `record-assurance` prints is not available to an agent
  Re-running record-assurance prints, verbatim:

    warning: ci/results/feature_ledger.json held a generated feature ledger, which
    was replaced by this work package's assurance report -- `report feature-ledger`
    writes the same path and would replace this report in turn -- point the
    manifest's report.emit at a free ci/results/*.json path (e.g.
    ci/results/<work-package>.json) to separate the two artifacts

  `report.emit` lives in `ci/manifest/WP-DATE-CREUSOT.json`, and this project's
  descriptor lists `ci/manifest/**` in `write_set.protected_roots`, which the
  hash-pinned SKILL.md authority boundary 5 glosses as "CI manifests" and forbids
  ("Write only under `allowed_roots`; never write into `protected_roots`"). So the
  one fix the tool recommends is a write the tool's own rules prohibit an agent
  from making, and the pilot cannot separate the two artifacts at all -- it runs
  permanently on a configuration the tool itself calls defective, kept working only
  by remembering an order the tool does not document.

  It is worse than unreachable, because the same boundary is not enforced:
  `write-set-check` reports `state: clean` for a file dropped into `ci/manifest/`
  (that is epic #1 subissue #90, filed minutes earlier by the same pilot). Its own
  `details` string says a file is "accounted for by allowed_roots, protected_roots,
  the ownership manifest, a declared crate's specs/ tree, or a canonical pipeline
  location" -- protected roots ACCOUNT for a file rather than VIOLATE it. So the
  rule that blocks the documented fix is the same rule that cannot be broken, and
  neither half helps.

BLACK-BOX RULE OBSERVED
  Yes. No source inspection. `ligature.pyz` was never unzipped, read, or
  decompiled; nor was the ligature source checkout at
  /home/goya/agent-workspace/ligature-workspace/ read. Everything above comes from
  `--help`, from command output, and from files the tool generates, plus the
  pilot's own `project-descriptor.json` and the hash-pinned
  `.codex/skills/ligature/SKILL.md` (an installed file, read at lines 66-83).

PILOT FINDINGS BACKING THIS
  date-ligature-051 (the collision), date-ligature-052 (the unreachable remedy),
  date-ligature-047 (the same collision seen from the record-assurance side, filed
  earlier and now only half a picture: v1.1 DID fix its record-loss half -- it now
  prints "preserved 4 existing obligation record(s) this run did not record" -- but
  the path collision itself is unchanged). In this pilot's
  findings/limitations.jsonl.

SUGGESTED FIX DIRECTIONS (none attempted here)
  1. Give the two artifacts different default paths: the assurance report is
     per-work-package, so a default of `ci/results/<work-package>.json` costs the
     feature-ledger projection nothing.
  2. Or make the write conditional: if the target path currently holds an assurance
     report (detectable -- it has `work_package` and `obligation_records`),
     `report feature-ledger` writes elsewhere or exits non-zero, mirroring the
     warning record-assurance already prints.
  3. Or make the ORDER explicit in the tool: `report` is documented as Stage 4.5
     output and `record-assurance` as Stage 7+, so a pipeline that runs the Stage
     8C report set after Stage 7 will always trip this. Say so in --help.
  4. Separately, reconcile the warning's own advice with authority boundary 5 --
     either report.emit becomes worker-writable, or the boundary carves it out.
"""
