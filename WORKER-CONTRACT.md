# Worker contract

Read this before starting ANY chainlink issue in this workspace. It holds the rules and gotchas that apply to every issue, so individual issue descriptions don't repeat them. If an issue's own description conflicts with this file, this file wins for process/safety rules; the issue wins for what to actually build.

The current P4 plan is [P4-MIXED-PORT-PLAN.md](P4-MIXED-PORT-PLAN.md), with
exact project/stage IDs in `planning/p4-mixed-2026-10-26/backlog-map.json`.
The operator's 2026-10-26 direction preserves three baseline ports and adds
four DISTINCT C++ projects for the verifier pairs/triple. It supersedes
the baseline re-port expansion, not existing evidence or risk decisions.
The historical master-plan path
`/home/goya/.claude/plans/based-on-this-preliminary-gleaming-salamander.md`
is missing; do not treat it as the active P4 execution reference or silently
substitute another plan. Read the current plan and your issue before work.

## 0.0 Current Ligature baseline (1.4.3, verified 2026-10-25)

Ligature 1.4.3 is installed in all three pilots. Bundle SHA-256:
`1a7a50eab31584946d8a7035ac3633130b0dc52d473d2587f3cd26e2800fd4e1`.
Clean source commit: `89033eee6f0415e32ec1a2287110a1fb828dd0a8`;
content/adjudicator hash:
`sha256:bfc93caff9f5cbcfb62b9d12ab4c3761035589e7c9051683e8f2df474a5927bb`.
Checksum/attestation verification, `migrate --upgrade`, and `doctor` pass
in each pilot, with no migration conflicts or required human action.

The focused scratch reproductions verify the fixes for local #175 and #176
(upstream #172/#173): the one-obligation P1 Verus slice now closes with CG3
verified, and P3 intake succeeds with `harness: "verus"`. The old
`harness: "counter_capacity"` declaration is rejected with a field-specific
correction. The exact Verus function remains a separate `--verus-function`
mapping. These are focused results, not completion of the full Verus ports
or the remaining #159 probes.

P1 and P3 live work-package manifests retain their old managed-skill hash
and fail G13 after the upgrade; do not hand-edit them. Refresh through the sanctioned
workflow with the required issue/path grants. P1 retains its `.gitignore`
and `PORT-GAPS.md` write-set exceptions. Retained `_closure` evidence can
also be discovered by closure validation; a 1.4.2 scratch control reproduces
that behavior. Installation health does not imply every live project gate
passes.

Evidence: `date-creusot/analysis/verification/ligature-1.4.3-2026-10-25/`
and `crypto-mixed/analysis/p4-verifier-fit/p4-5-probes/verification-1.4.3/`.

### Previous baseline (1.4.2, verified 2026-10-18)

> **Current bundle:** Ligature 1.4.2, SHA-256
> c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184.
> Source commit 5749590e076bd1bad048d57a0df7f38151647dbd; attested
> content/adjudicator hash
> sha256:2e0616b7ff7d54776c4798ba6a1f447136f4434f211b9ccd655e753d19f3e928.
> All three pilot roots contain this checksum-verified bundle. Each
> migrate --upgrade completed with result=current, no conflicts, and no
> required human action. doctor exits 0 in all three pilots.
>
> Ligature 1.4.2 updates the managed skill and project-state schema. The
> date-creusot and crypto-mixed work-package manifests still pin the prior
> hashes, so their validate-work-package commands fail G13 until the
> manifests are regenerated through the sanctioned workflow with exact
> human-issued grants. SwissTable's work-package validation passes.
>
> The crypto-mixed C_static report was freshly generated and is now bound to
> six source files, the target/configuration, and extractor version 0.2.0.
> R1/G16 and G14 still block on four unresolved call sites and three
> undeclared direct cross-concept calls; these are current P3 port findings,
> not installation failures. date-creusot's write-set check retains its two
> existing out-of-set findings for .gitignore and PORT-GAPS.md.
>
> Release verification and detailed issue checks are recorded at
> date-creusot/analysis/verification/ligature-1.4.2-2026-10-18/README.md.

**Earlier update, 2026-10-02: pilots ran Ligature 1.2.1**
(releases/v1.2.1, SHA-256
30e504d388d5fb2acf1185fe3bfc17c96ec82483771d8d59a37fb3749009aacd;
date-creusot and swisstable-verus migrated). 1.2.1 also fixes #109
(doctor now follows --descriptor).

**Earlier update, 2026-10-01: pilots moved to Ligature 1.2.0**
(releases/v1.2, SHA-256
9c921eeb1bbb858c0041e49f07cf5d06988eb798ba60b9207f7576cba430637c;
date-creusot migrated). 1.2.0 fixes #96–#102 (re-verified and closed):
- check-bridges/gate-g9 no longer crash with a relative --workspace.
- validate-interaction skips staged .draft files.
- gate-g14 re-checks the proof certificate behind each assurance record.
- CG3 reads declared depends_on.
- Degradation records must carry valid review provenance before they excuse anything.
- status agrees with validate-closure.

## Historical 1.1.1 behavior notes

The following probes are retained as historical evidence. Do not treat an
old 1.1.1, 1.2.0, or 1.2.2 failure as current without reproducing it against
the 1.3.2 bundle in the relevant pilot root.

Several 1.0-era statements are still quoted in issue descriptions and pilot
READMEs; they were wrong for 1.1.1. The historical probes below were measured on
`date-creusot/` scratch `rsync` copies with the pinned 1.1.1 binary (sha256
`3edfd03c…`, `ligature version` -> `1.1.1`, `sha256sum -c SHA256SUMS` ->
`ligature.pyz: OK`).

**Nine `draft` templates ship, not three.** Read `.ligature/prompts/` in the
pilot root — that file list *is* the registry, because `draft --help` does not
list it and the stage argument is a closed `{0,3}` enum: `evidence-intake`
(stage 0), and at stage 3 `boundary-drafting`, `interaction-drafting`,
`concept-to-code`, `bridge-drafting`, `witness-drafting`, `exemption-drafting`,
`protocol-debt-drafting`, `conflict-resolution-drafting`. Each needs `--var`
values; the binary names the next missing one by name and exits 1, so enumerate
by iteration rather than guessing. Enumerate the var set *after* picking a valid
target path — the target-scope check runs first and its error says nothing
about whether the template exists.

**Three things 1.0-era docs get wrong, in the direction of under-claiming:**

- Evidence records are promoted by `ligature.pyz promote-evidence <target>`,
  not by a hand `mv`. The `mv` workaround in
  `date-creusot/docs/evidence-promotion-exception.md` was a one-time
  authorisation for a *missing command*; the command now exists, so use it. It
  takes the target (not the `.draft`) and no `--reviewer` — it is mechanical,
  not a human checkpoint.
- `accept-promotion` is gated on `ligature.pyz record-ruling --reviewer <human>
  --verdict ratified|rejected --artifact <path> …`; it refuses to mint a
  receipt until every accepted artifact is covered by a `ratified` ruling, and
  a ruling is hash-pinned to the exact content it covered. The human-ruling
  checkpoints that older docs describe as *social* constraints are now enforced.
  `--reviewer` still has no default and is documented as never LLM-supplied, so
  treat a ruling as a human action.
- `closure_kind` is a real top-level `project-descriptor.json` field
  (`['deductive', 'bounded', 'partial']`). Any "record the intended
  `closure_kind` in a side file because the descriptor cannot express it"
  instruction is obsolete. Descriptor schema errors are now reported with the
  JSON path and the permitted keys, and `doctor` exits non-zero on one.

**Historical gap, superseded in 1.2.2:** concept-spec promotion and the
Stage 3 template coverage were reported missing under earlier releases
(local epic #1 #79; upstream fixes #105/#111). Re-check the relevant command
help and validators before using the new route. Do not hand-write a spec into
a protected tree to work around a tool failure.

**Protected-write behavior changed in 1.2.2.** A protected path without a
matching active grant is now a blocking protected-write violation; a grant is
consumed only when `write-set-check --issue N` names the same issue. The
1.2.2 write-grant and supervisor rules are in [PROTECTED-WRITES.md](PROTECTED-WRITES.md).
The earlier false-negative report (#90) is therefore historical, not a
reason to hand-edit a protected path. When changing verifier_policy, use the
current descriptor validation and read back `status --json`; do not infer
that a typo is accepted or rejected from the old probes.

**Historical 1.1.1 crash, fixed in 1.2.0:** #96 reported bridge checks
crashing with a relative default workspace. The fix was verified upstream.
If the 1.3.2 command fails in a pilot, capture a fresh black-box reproduction
under §2 rather than applying the old workaround preemptively.

## 0.1 Protected writes: request, grant, sanctioned verb

T0 workers never write protected roots. A worker that needs one emits a
PROTECTED-WRITE REQUEST naming the issue, exact path/op, proposed sanctioned
command, and why the change is mechanical. The detailed tier definitions and
migration warning/error policy are in [PROTECTED-WRITES.md](PROTECTED-WRITES.md).

The protected-write command sequence for the currently installed 1.4.2 bundle is:

1. Confirm the change is not normative. Policy prose, proof scope, verifier
   choices, write-set changes, approvals, and rulings are T2 human work.
2. Obtain an exact `authorize-write` grant. A supervisor issuer is usable
   only if its identity is already listed in descriptor
   `write_set.authorized_supervisors`; the worker must never invent or
   self-issue that identity. Otherwise request a human-issued grant.
3. Run only the matching sanctioned verb, such as `scaffold-crate` for a
   declared crate, `configure-crate --profile cargo-verus` for an existing
   Verus crate, or `generate-work-package` for Stage 7. Do not hand-edit the
   protected output. The current SwissTable `configure-crate` refusal while
   resolving the Nix-packaged `vstd` is tracked as local escalation #124; do
   not work around it by hand-editing Cargo.toml.
4. Run `write-set-check --issue N --json`, the command-specific validator,
   `doctor`, and `check --json`. Record outputs and hashes on the issue.

`migrate --upgrade` is a separate managed-install updater; it is not a
general protected-write grant and does not authorize edits to user-owned
policy or work-package semantics. `accept-policy --reviewer HUMAN
--version NAME@MAJOR.MINOR` is a human checkpoint, not a Tier 1 worker verb.

## 0. Picking the next issue (for automation)

For the current P4 phase, use the explicit chain in
`planning/p4-mixed-2026-10-26/backlog-map.json`. #161 is still the open human
checkpoint. #177 is setup; the four project epics #178/#182/#186/#190 each
have three serial leaf stages, followed by the #169–#174 comparison/roll-up
chain and the M7 CG6/G15 control #194. #162 is preserved baseline maintenance
after #174. Old #163–#168 are CLOSED AS SUPERSEDED, not completed ports.

Before any action, read `chainlink --json issue show <id>` and verify every
listed blocker is closed. A title, this plan, an epic parent, or a proposed
scope does not authorize jumping a human checkpoint or writing protected
files. An unqualified `chainlink issue next` can also surface older work;
confirm it belongs to the intended phase instead of assuming a historical
nine-cell queue is still active. Prefer the current graph over old prose.

Use current JSON-capable Chainlink and inspect `.next.id` if using `issue
next`. Epic #1 contains ad hoc Ligature escalation reports and is outside
the execution chain; always retain the `--exclude 1` and `--no-close`
chainlink-loop rules in §5.5. Do not auto-close human decisions or label an
unimplemented superseded port as successful verification.

## 1. Black-box rule for ligature.pyz — the most commonly violated rule

This workspace tests each pilot's pinned release binary as a black box,
the way a real user would. The current baseline release and checksum are in
§0.0; 1.4.3 reports clean, attested provenance. Verify the pilot-local
`tools/ligature/SHA256SUMS` and `version --verify` rather than relying on a
historical version claim. Planned new roots obtain an approved bundle only
through their setup issue.
When a new release is installed, run `migrate --upgrade` only in an
initialized pilot, then verify status, doctor, write-set-check and the
current-phase gates. A nonzero project check can be a real project finding;
it is not automatically a migration failure.

- **Never read `/home/goya/agent-workspace/ligature-workspace/`** (the ligature source checkout, including its `docs/`, `plan.md`, `scripts/`). It sits on this same machine and it is tempting to peek at when the binary's own output is unclear — don't. If the binary's `--help`/output genuinely isn't self-explanatory enough to proceed, that gap is itself a finding (see §2), not a reason to read the source.
- **Never unzip or inspect the contents of `ligature.pyz` itself.**
- Allowed: `ligature.pyz <cmd> --help`, whatever the binary prints when run, and files it generates (e.g. `project-descriptor.json` after `init`). Discover field names, schemas, and behavior from what the tool actually shows you, not from outside knowledge.
- Always invoke the copy inside **your own pilot root** (`<pilot>/tools/ligature/ligature.pyz`), never another pilot's copy.

## 2. Escalation rule — when ligature.pyz itself is lacking or buggy

If `ligature.pyz` crashes, gives a contradictory/unclear error, rejects a value its own placeholder suggested was valid, or is simply missing functionality your issue needs:

1. Do not silently work around it or guess your way past it by trial and error.
2. File a subissue under epic **#1** (`chainlink issue subissue 1 "<title>" -l ligature-upstream -d "..."`), with these fields in the description: exact command run, exit code, expected vs. actual behavior, which pilot hit it, and the pinned binary's sha256 (from that pilot's `tools/ligature/SHA256SUMS`).
3. Make this the headline of your closing comment on your own issue — flag clearly that this needs human review before the ligature workspace owner can be told, don't bury it. Do not close your own issue as a normal success; note what's blocked and why.
4. If nothing like this happens and the binary behaves as documented, no escalation needed — just report normally.

This rule does not apply to third-party tools (Creusot, Verus, Kani, codesight-mcp, rdb, etc.) — friction with those is just a normal finding (§6), not an epic #1 escalation.

## 3. Standing scope constraints (apply to every issue unless it explicitly says otherwise)

- Touch only the root assigned to your issue. Existing baseline roots are
  `date-creusot/`, `swisstable-verus/`, and `crypto-mixed/`. Planned mixed roots
  are `icl-creusot-verus/`, `tinyxml2-creusot-kani/`, `snappy-verus-kani/`, and
  `leveldb-three-verifiers/`; they are not initialized or worker-writable
  merely because their names appear here. #161/#177 must establish their
  exact setup and write policy first. Never change another project's source,
  manifests, ledger, policy or evidence under an issue scoped to one root.
- A protected-write grant never widens the worker's allowed_roots. Use only the sanctioned verbs described in §0.1 and PROTECTED-WRITES.md; if a matching grant or authorized command path is absent, stop and request the human checkpoint.
- Never modify `flake.nix` or `flake.lock` at the workspace root. If something's missing from a Nix shell, report it as a finding on epic **#2**, don't install outside Nix or edit the flake yourself.
- The workspace root is an **operator-managed git repo** (remote `git@github.com:nanonite/ligature-support-matrix.git`) — never run `git init`, `git commit` or `git push` there. Each pilot (`crypto-mixed/`, `date-creusot/`, `swisstable-verus/`) is its own repo, linked into the root repo as a submodule (Ligature's work-package generation requires the pilot to be a Git repository root); commit inside your pilot as your issue requires, never push, and leave the root's submodule pins to the operator. `swisstable-verus/` keeps its ignore rules in `.git/info/exclude`, not a tracked `.gitignore`, because its write_set does not account for one. Other nested git repos (e.g. `upstream/date/.git`, `tools/codesight-mcp/.git`) are expected; leave their own `.git` alone unless your issue is specifically about that checkout.
- Don't touch `project-descriptor.json`, run `ligature.pyz init`, or run `draft`/`approve`/later pipeline stages ahead of where the issue graph says to — check `chainlink issue show <your-id>` for `Blocked by`; if it's non-empty and those issues aren't closed, stop and say so rather than proceeding.

## 4. Documents already written — read the relevant one, don't re-derive it

- `findings-schema.md` (workspace root): the exact field shape for every `findings/limitations.jsonl` entry. Every pilot root has its own `findings/limitations.jsonl`.
- `oracle-PROTOCOL.md` (workspace root, copied into each pilot's `oracle/`): the differential C++/Rust testing protocol — case/result JSONL formats, golden-file design, `test-map.csv` shape, non-observable-properties handling. Read this before writing any oracle case, driver, or Rust test generator.
- `rdb-divergence-workflow.md` (workspace root): how to minimize a failing oracle case and debug it with `rdb`, including real, verified command syntax and its known limitations (e.g. `expression` is not supported — use `register`/`variable`/`memory` instead).
- `oracle-example/` (workspace root): a working, verified, standalone worked example of the whole oracle-driver + Rust-check + rdb-debugging pipeline. Copy its pattern, don't reinvent it.

## 5. codesight-mcp usage — verified gotchas (don't repeat this trial-and-error)

- Binary: `tools/codesight-mcp/.venv/bin/codesight-mcp` (shared, one install for the whole workspace). Each pilot's `.mcp.json` sets `CODE_INDEX_PATH` and `CODESIGHT_ALLOWED_ROOTS` scoped to that pilot's own `upstream/`+`rust/` — never index outside your pilot's allowed roots (it will correctly refuse with `"Folder is outside allowed roots"`).
- CLI output for most operations prints a `[codesight] <op>` header line **before** the JSON body — strip the first line before parsing (`tail -n +2` or equivalent), or you'll get a JSON parse error that looks like a tool bug but isn't.
- The repo identifier is **auto-generated** by `index-folder` (e.g. `local/date-c96cc248007d`) — always read it back from `index-folder`'s own JSON `"repo"` field. Do not guess a repo id from the folder name.
- Flag names are sometimes not what you'd expect — e.g. `get-file-outline` takes `--file_path`, not `--file`. Check `codesight-mcp <op> --help` or `codesight-mcp tools` rather than guessing.
- **Known real limitation** (found in issue #11, reproduced independently): tree-sitter language detection misclassifies `.h` C++ header files as plain C for at least the HowardHinnant/date codebase, extracting only trivial `struct` declarations and failing to resolve most real symbols (`Symbol not found`). Expect this to bite P2/P3 too, which lean on C++ header analysis even more. Don't assume codesight-mcp's C++ support works well just because it's listed as supported — verify per-file with `get-file-outline` early in each pilot's analysis issue, and log what you find as a `tool: "mcp"` finding rather than silently working around it or skipping the analysis.

## 5.5. Running via `chainlink-loop` (opencode-loop-plugin) — always pass `--no-close`

This workspace's chainlink DB can be driven by `chainlink-loop` (`/home/goya/storage/opencode-chainlink-loop-plugin/bin/chainlink-loop`, a bun script that is not on PATH, so always call it by this absolute path from the workspace root with `CHAINLINK_DB=$(pwd)/.chainlink`), a deterministic outer/inner loop: it picks the next issue via `chainlink issue next --json`, runs a worker (`opencode run`, agent `build` by default), runs a reviewer (`plan` by default), and — **by default** — closes the issue on reviewer approval.

**That default closing behavior is a confirmed, real problem for this project and must be overridden with `--no-close` on every invocation.** Confirmed incident: on issue `#12`, the worker correctly followed §2 above across at least 7 attempts — it found real ligature defects, filed them as escalations under epic `#1`, and explicitly wrote "not closing #12 as a normal success" every time. The issue was still closed anyway, at a moment between two of those attempts' comments, almost certainly by the reviewer-approval auto-close path — which judges "is the deliverable done," not "does this project's escalation rule override normal closure." Two severity-`blocker` escalations (`#76`, `#77`) were filed minutes after that close and couldn't have been seen by whatever approved it. The same pattern repeated on `#14` (see its comments): closed despite its own final comment stating that Stage 4.5 promotion was deliberately left undone pending a human ruling.

**Standing rule:** always run `chainlink-loop` with `--no-close`. A human (or a session doing the reviewing job §6 describes) closes issues explicitly via `chainlink issue close <id>` after actually reading the result — never let the loop's own reviewer-approval close anything in this project. Also always pass `--exclude 1` so the queue never enters epic `#1`'s subtree (its children are escalation reports with no fixed position in the sequence, not sequential work — see §0's note on epic `#1`).

If you stop a live `chainlink-loop` run to change flags (e.g. to add `--no-close` retroactively), `SIGTERM` the wrapper process — it stops the loop, kills the in-flight step's process group, and releases its lock cleanly (confirmed: killing it does not discard already-written files, only the in-flight step). Relaunching with `--task <id>` and the default `--review-first auto` will detect the existing dirty tree/prior attempt and review it rather than redoing the work from scratch.

## 6. Closing checklist — every issue should end this way

1. Show **real command output** in your closing comment, not a paraphrase. If you claim a build passed, show the actual pass/fail line. If you claim a file has certain contents, quote it.
2. State explicitly which scope-constraint checks (§3) you confirmed, and how (e.g. "confirmed `flake.nix`/`flake.lock` md5 unchanged before/after").
3. Log every real finding — ligature (§2), third-party tool friction, or otherwise — in the right place: `findings/limitations.jsonl` (per `findings-schema.md`) for pilot-specific findings, a chainlink comment on epic #2 for flake/toolchain findings, a subissue under epic #1 for ligature defects.
4. Add a chainlink comment on your own issue with the full evidence, then close it — unless §2's escalation applies, in which case leave your own issue clearly flagged as blocked/needing review rather than closing it as a normal success.
5. Don't claim something is done without having actually run it in this session. A "should work" is not a finding and not a close.
6. If your issue touched the port itself (analysis, porting, proofs, oracle, or a scope ruling), add your C++→Rust gaps to `<pilot>/PORT-GAPS.md` (§6.5) before closing.

## 6.5. C++→Rust transfer gaps — a primary deliverable, not a side note

Part of the reason these pilots exist is to find **where moving C++ to Rust is weak**. The operator feeds every such gap into a knowledge repository, so each one has to be documented in a form that reads well outside this workspace. `limitations.jsonl` is organized by tool. `PORT-GAPS.md` is organized by porting weakness. Every gap goes in both, linked by finding id.

**What counts as a gap** (record each one, even when the port works around it):
- **Semantic divergence:** the Rust port observably differs from upstream. Example: swisstable-verus-021, where erase always writes kDeleted but abseil checks `WasNeverFull`.
- **Cut or simplified behaviour:** example: swisstable-verus-009, insert never grows. Operator scope rulings count here; a ruled scope cut is still a gap.
- **No faithful Rust or verifier equivalent:** for example SIMD, raw or unsafe slot storage, template metaprogramming, C++ object lifetimes, iterator invalidation, pointer stability.
- **Unprovable or costly obligations:** properties the verifier can't discharge, or only with manual lemmas, timeouts or budget changes. Example: swisstable-verus-023, set extensionality.
- **Tooling blind spots in the transfer:** analysis tools that misread the C++ (tree-sitter on headers), or oracle and test gaps where parity can't be checked.

**Format.** One `###` entry per gap in `<pilot>/PORT-GAPS.md`, with these fields:
`Category` (one of the five above) · `C++ construct / upstream location` (file:line at the pinned commit) · `What the Rust port does instead` · `Why` (language, verifier or tool reason) · `Impact` (observable behaviour, proof coverage, oracle parity) · `Status` (open / worked-around / ruled-scope-cut / fixed) · `Finding ids` · `Generalizable lesson` (one or two sentences a reader with no knowledge of this pilot can reuse).
Never remove an entry. If a gap is fixed later, update its `Status` and keep the history.
