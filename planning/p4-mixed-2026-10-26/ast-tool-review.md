# AST tool report review for P4

Reviewed 2026-11-14 UTC. The operator identified `/home/goya/storage/callgraph-benchmark-workspace` and its `docs/combined-tools/FULL-LIGATURE-HANDOFF.md` as the AST report. The report and retained v2.43 roll-up, provider query contract, CodeQL setup amendment, selected run manifest, and disposable C++ smoke evidence were reviewed. No AST benchmark or verifier was rerun for this review.

## Decision status

The pending-report prerequisite is satisfied: the report is available and reviewed. This clears only the AST-specific wait recorded on #161 and #177. It does not select a provider for production work, authorize workspace creation or protected writes, resolve #161's human decisions, or establish proof/assurance composition. #161 remains open; #177 remains blocked by #161. The local issue graph still lists #161 as blocked by #160 even though #160 is closed; that pre-existing relationship was left unchanged because it is not the AST-specific hold.

The report is suitable as **tool-selection evidence and an evidence-capture template** for targeted C++ source questions. It does not establish a complete AST, a complete call graph, the correctness of any P4 source claim, full-Ligature intake, C++ to Rust equivalence, production proof coverage, or generated Rust patch success. Its fixtures are small and workspace-owned.

## Measured tool guidance

| Use | Report-supported choice | Measured result and limit |
|---|---|---|
| Targeted, citation-bearing structural/security question | CodeQL CLI with a question-specific query, a source-bound C++ database, and preserved raw output | Best measured strict structural evidence in these fixtures: 69/84 eligible strict facts, with 15 missed facts, 39 extra/incorrect observations, and 9 shape-only observations; structural case conditions were 13 success / 9 failed / 8 inconclusive / 1 unsupported. Frozen security score: 4 correct / 4 unknown case conditions. The v2.41 answer-aware result (8 correct) is diagnostic and not frozen. Query support and identity must be checked per question. |
| Lightweight navigation and source reading | Tilth or `rg` plus literal source reads | No strict structural accuracy credit. Tilth's C++ bare-symbol lookup failed and a cross-file callee was reported as `extern`; search-plus-read and Rust symbol lookup were useful. Ripgrep is lexical evidence only. These tools read current source directly but do not detect stale retained indexes. |
| Optional repository graph or metadata inventory | CodeSight with line-level citations checked against the same checkout | Structural results: 0 strict facts, 24 shape-only observations, 12 extra observations, and 21 missed facts. Metadata had 30/30 eligible values, but only 2/10 unique facts had valid line citations; 8 were unverifiable. A measured graph edge pointed to the callee definition, not the caller site. |
| Freshness for indexed tools | Explicitly rebuild/refresh and bind the output to source/build/index digests | CodeQL and CodeSight silently reused stale indexes before refresh and reported refreshed afterward. Freshness controls passed 32/32. Tilth and ripgrep read direct source but cannot detect retained-index staleness. |

No tool is generally ranked best. Do not promote provider agreement, name/shape matches, or graph unions to truth. Keep static targets separate from runtime candidates, definition spans separate from call sites, and `unknown`, `unsupported`, `inconclusive`, `partial`, `stale`, `invalid`, or `truncated` distinct from pass/fail.

The accepted structural-pair roll-up is not a basis for composition claims: one route was a measured negative, four routes had no jointly eligible cases, and one union was incomplete. No metadata or security pair was measured; the #47 amendment-02 independent packet review/freeze was incomplete. MCP transport parity and a combined wrapper were not measured. `MCP-DECISION.md` defers a unified wrapper until a concrete workflow justifies one.

## Tool, version, invocation, inputs, and outputs

| Tool | Exact version/build in report | Supported invocation and inputs | Output and limits |
|---|---|---|---|
| CodeQL CLI | 2.27.3; `/nix/store/m5a0k6v4yyk7bkmlifiq27ax1kqpjb8s-codeql-2.27.3/codeql/codeql`; SHA-256 `c2c5df912a2ac8ed7ea29aa24567574a4ae43aa1507ce8e3d04e9f0d6bf4a55f`. C++ query pack `codeql/cpp-all` 12.3.0, pack-lock SHA-256 `634263180d46f02e5eceaa275bb69c22bc3eb564edd0ce7307ba16f53fbdd3d3`. | CLI help was checked for `database create`, `query run`, `bqrs decode`, and `bqrs interpret`. C++ database creation requires the exact source root and a successful, project-appropriate C++ build-capture command. The selected query must be compatible with the database and installed pack. | `query run` writes raw BQRS. The measured row-query path decodes BQRS to CSV. Path queries use `bqrs interpret` to SARIF v2.1.0; the recorded template has `--max-paths=4`, so that cap must be disclosed and must not be treated as an exhaustive path enumeration. Preserve BQRS, decoded output, stdout/stderr, exit codes, source/build/query/pack digests, and run manifest. |
| Tilth | 0.12.0; report-recorded executable `/home/goya/storage/callgraph-benchmark-workspace/tools/tilth-0.12.0/bin/tilth`; SHA-256 `60b5304e4a839455a639ad88fd6690eb3317003c772a4cac93ee01828045b763`. | CLI help supports `tilth grok <TARGET> [--scope <SCOPE>] [--full]`; recorded template: `tilth grok '<literal case target>' --scope "$SOURCE_ROOT"`. Input is a literal target and source-root scope. | Help does not establish a stable structured output schema. Preserve raw stdout/stderr and treat results as navigation/source-read candidates. Do not claim AST accuracy or a complete call graph. |
| CodeSight | 0.6.0; report-recorded executable digest `f22ebcc40a0170e3efd7b19c52aa3988a8231dd01ccf0441b15aba12ecfea526`, commit `816d523a1126b210afffa8a422760bbfce42f5f6`. | Recorded index command: `codesight index-folder --path "$SOURCE_ROOT" --use-ai-summaries false`, with `CODE_INDEX_PATH="$RUN_DIR/codesight-index"` and `CODESIGHT_ALLOWED_ROOTS="$SOURCE_PARENT"`. Recorded operations include `search_symbols`, `get_callees`, and `search_references`; CLI arguments map underscores to hyphens, JSON is the default. | Retain exact JSON stdout/stderr and index identity. Verify each citation against the exact checkout. Refresh/rebuild after source changes; report evidence of freshness. The study did not measure full-Ligature intake or a unified MCP wrapper. |
| ripgrep | 15.2.0 (rev `e89fff89ac`); report-recorded binary SHA-256 `e62198eb19b136b88c330af83647b5a962cb99b6b1f066758568f12de1974849` | Recorded lexical form: `rg -n -w -e '<pattern>' -- <file roots>`; source reads: `nl -ba -- <file>`. Keep roots restricted to the selected source files. | Raw matching lines and one-based source lines are lexical/source evidence, not resolved AST edges. |

## CodeQL C++ smoke and reusable runbook

The C++ setup amendment corrected a harness argument-tokenization defect: the prior setup had passed shell quoting and `&&` as literal arguments and marked affected C++-dependent cases invalid. The selected amended runs are bound to an independently reviewed, frozen amendment. That repair is evidence about the benchmark harness, not evidence that arbitrary P4 project build recipes work.

The retained disposable smoke used source tree `387ce2b448b96dc4cb0647467db6cfcf47d8d74ee80fce164adfb00c47d4c9a8`, unchanged before and after. Its exact absolute `argv`, working directory, environment, output hashes, and exits are retained in `smoke-attempt-03/smoke-result.json`. The following is the same invocation shape with its fixture-specific absolute paths replaced by variables; database creation, query execution, and CSV decoding all exited 0:

```sh
/nix/store/m5a0k6v4yyk7bkmlifiq27ax1kqpjb8s-codeql-2.27.3/codeql/codeql database create \
  --language=cpp \
  --source-root="$SOURCE_ROOT" \
  --command="/bin/bash $BUILD_SCRIPT $SOURCE_ROOT $BUILD_DIR" \
  "$DATABASE"

/nix/store/m5a0k6v4yyk7bkmlifiq27ax1kqpjb8s-codeql-2.27.3/codeql/codeql query run \
  --common-caches="$WORKSPACE/.cache/codeql" \
  --search-path="$WORKSPACE/.cache/codeql/packages" \
  --database="$DATABASE" \
  --output="$RUN_DIR/call-edges.bqrs" \
  "$WORKSPACE/runs/tool-selection/codeql/queries/cpp/CallEdges.ql"

/nix/store/m5a0k6v4yyk7bkmlifiq27ax1kqpjb8s-codeql-2.27.3/codeql/codeql bqrs decode \
  --format=csv \
  --output="$RUN_DIR/call-edges.csv" \
  "$RUN_DIR/call-edges.bqrs"
```

For a path-problem query, the provider contract separately records this SARIF interpretation template; it was not exercised by the disposable smoke:

```sh
"$CODEQL" bqrs interpret \
  --format=sarifv2.1.0 \
  --no-sarif-minify \
  --max-paths=4 \
  -t=kind=path-problem \
  -t="id=$QUERY_METADATA_ID" \
  --output="$RUN_DIR/raw/$QUERY_ID.sarif" \
  "$RUN_DIR/$QUERY_ID.bqrs"
```

The limit of four paths is an explicit query-output cap. Preserve raw BQRS and SARIF separately and disclose the cap; do not infer that omitted paths do not exist.

Those commands are a **fixture reproduction**, not a ready P4 command: `$SOURCE_ROOT`, `$BUILD_SCRIPT`, `$BUILD_DIR`, `$DATABASE`, `$RUN_DIR`, and `$WORKSPACE` must identify a separately authorized immutable P4 source snapshot, a project-specific and pinned build script, and fresh output roots. The smoke build script SHA-256 is `eb1155200846b08ae966514f4c7f86fc3e7a24fa344c424b0004997418e63120`; its `CallEdges.ql` SHA-256 is `49e6a8881ed9fc953754ddaab2b00f24069393fd6e4a862b6d6b0ca5ebc90de3`. It used `LC_ALL=C.UTF-8`, `TZ=UTC`, `CMAKE_BUILD_PARALLEL_LEVEL=1`, and isolated `HOME`/`TMPDIR`; full `PATH` and exact values are in `smoke-result.json`. The smoke's CMake 4.0.3, clang 18.1.3, GNU Make 4.3, and binutils 2.42 were recorded; they are not approved P4 pins. The query produced 42 CSV data rows. The raw BQRS is 22,671 bytes (SHA-256 `4277cdf1bca48fd86ca189941ca8bdcf39b15d2d13db147f14bb72c7d84f2e48`); the CSV is 5,062 bytes (SHA-256 `aae3be37d65e19b50c74ea6654d7a2f88a11f3b2acd72d70ebb0244046f20888`); the database tree digest is `55fd23ea2cb74fec4ba9ffdc8dedec96cef61ae28d2bad3398736ababb26c0c4`.

Before using any result in a later P4 task:

1. Pin the source snapshot, tree digest, exact build command/toolchain, query and query-pack lock; ensure the database is newly built from that source.
2. Save exact argv, working directory, environment overrides, tool version/build, start/end status and exit code for every command.
3. Preserve raw BQRS, CSV/SARIF, stdout/stderr and hashes. Mark any query cap, pagination, truncation, unsupported operation, failed extraction or decode issue explicitly.
4. Check completeness against the declared query/output contract and verify every source citation, identity, caller site, and target role against the same source snapshot. Keep unresolved or conflicting claims unresolved.
5. Rebuild the database after any source or build change; refresh CodeSight's index after source changes. Direct-source Tilth/rg reads need no index refresh, but still need snapshot-bound citations.
6. Treat these records as navigation/structural observations only. Contracts, semantic behavior, verifier coverage, proof composition, and production risk require their separate P4 evidence and human decisions.

## Evidence index

The report files remain in the callgraph benchmark workspace; they were not copied or modified. SHA-256 identities reviewed:

| Evidence | Path | SHA-256 |
|---|---|---|
| Current full-Ligature handoff | `/home/goya/storage/callgraph-benchmark-workspace/docs/combined-tools/FULL-LIGATURE-HANDOFF.md` | `2464345f5175ef017c18c9fde7d109141e51c3c705f5f401b0e0a56602bfe4bc` |
| MCP decision | `/home/goya/storage/callgraph-benchmark-workspace/docs/combined-tools/MCP-DECISION.md` | `c7f4326744d51cd32ae0030bb8962d40efde2b1b0a6e48139cef2fcb5df92702` |
| Workspace capability report | `runs/tool-selection/combined/workspace-study/REPORT.md` | `63f45c1a207c3fc9fc1d804fff9a97ad65baa5fb48cb3e6d90ff646e8acc13c2` |
| Accepted v2.43 roll-up report | `runs/tool-selection/combined/workspace-study/measurement-audit/atomic-v2.43-capability-rollup01/REPORT.md` | `78d4197e698dbf452911ab5102a44d7025040b08bcc55dfbc14e6fe6b5ef611c` |
| v2.43 machine roll-up | `runs/tool-selection/combined/workspace-study/measurement-audit/atomic-v2.43-capability-rollup01/rollup-v243.json` | `811868af55f30f71ffdd03459ed9bee85758645bb6b56e5749b95a777c8ead83` |
| Provider query/invocation contract | `runs/tool-selection/combined/workspace-study/provider-queries.json` | `8c3f8436835aacea81069037841c5d88c800f0e85a7eed3b2556ced4216c60d7` |
| Selected amended CodeQL run manifest, rep-03 | `runs/tool-selection/combined/workspace-study/capabilities/runs/rep-03-amendment-codeql-cpp-setup-v1/run-manifest.json` | `d9a3df4b5dc30a1de585bd7ac546324c1fb714f90b1111fe9d2f73120e9fdbde` |
| CodeQL C++ smoke result | `runs/tool-selection/combined/workspace-study/contract-amendments/codeql-cpp-build-v1/smoke-attempt-03/smoke-result.json` | `d8267ec8ad82b055671d16892db0e7ebf94f8916d2ada778c5f149483074fc0b` |
| C++ setup amendment freeze | `runs/tool-selection/combined/workspace-study/contract-amendments/codeql-cpp-build-v1/amendment-freeze.json` | `4b1fe7da2126c0cbbba8b265d809ccb9b2f7a57a57f2c3a827f7fd91153ef093` |
| Independent review record | `runs/tool-selection/combined/workspace-study/contract-amendments/codeql-cpp-build-v1/review-record.json` | `c596146cad7deae1a99e889e3ea94733725e2c30181a5d18bbceba52187144d6` |

The selected rep-03 run manifest binds to workspace revision `ccb0b33cbc06289448f35ceb3b2b75a01febbde7` with a dirty worktree status digest `e1901e008032d4650e7436067a45088c55263b720881a2bd5f250e01c6a6ed01`; its logical C++ fixture tree digest is `387ce2b448b96dc4cb0647467db6cfcf47d8d74ee80fce164adfb00c47d4c9a8`. The manifest's internal digest is `db0d05a659682ba0b14a5287e4aa497f1939c6dbc44c355f93e03955e1b16618`, and it binds the query-plan digest to the provider contract digest above. The exact amended smoke run, separate from the three-repetition measurement manifest, is identified by the `smoke-result.json` hash in the table.

The report's reproduction commands rebuild/check the roll-up and run validators over retained evidence; they do not query a provider or build a database. They were not rerun for this review. No benchmark, provider query, database build, Ligature binary invocation, Ligature source inspection, or verifier run was performed here.

## Remaining prerequisites

- #161 must resolve scope, contract/TCB, toolchain, trust, risk-ceiling, and write-policy decisions. No decision is inferred from this report.
- #177 stays blocked until #161 is resolved. Subsequent work needs explicit roots and capabilities plus project-specific compiler/build prerequisites.
- Before P4 uses CodeQL, the operator must authorize the exact project source, build-capture command/toolchain, query(s), pack lock, output/evidence roots, and citation-review method. Reported C++ fixture behavior does not validate any selected upstream project build.
- Full-Ligature ingestion and transformation of this evidence have not been demonstrated. The handoff provides an evidence contract, not an invocation for a Ligature binary or a claim that Ligature consumes these records.
- P4 closure and assurance composition remain separate: mixed-verifier evidence can affect CG1/CG3, and a build layout or source-analysis report establishes neither deductive closure nor risk acceptance.
