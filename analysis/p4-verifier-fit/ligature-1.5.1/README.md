# Ligature 1.5.1 re-check — crypto-mixed (chainlink #196)

Date: 2026-11-17
Pilot: `crypto-mixed/`
Binary: `tools/ligature/ligature.pyz`
Bundle SHA-256: `d704c5a5875d200214310c1fca7854a14a105c1b74cebaa5bc03f6a870bcc030`
`version --verify` (exit 0, `baseline/version-verify.txt`):

```
ligature 1.5.1
  adjudicator: zipapp (attested: true)
  content hash: sha256:def6b87957ff4e26737e18a469a7df447fdadb5df3eac5180db881c42baccfcb
  bundle: 133 file(s)
  bundled schemas: 36
  source: 29acabdb6c70dbab4213ca73626d3fed78afcbcf (clean working tree)
```

`doctor` exits 0 (`doctor.stdout.txt`). Baseline artifacts are in `baseline/`:
the pre-fix `check --json` and `gate g14 --json`, the old C_static report, the
old manifest hashes and pins, and the binary identity.

Order of work: (1) stray P4-5 closure input, (2) C_static re-extraction,
(3) G13 manifest refresh. Steps 1 and 2 are fixed. Step 3 is prepared and
blocked on a human-issued protected-write grant (`g13-regeneration-plan.md`).

## 1. Stray P4-5 closure input (fixed)

### What 1.5.1 reported

`analysis/p4-verifier-fit/p4-5-probes/q7-bridge-dispatch/inputs/specs/_closure/`
held three untracked P4-5 Q7 probe fixtures (not project records):

| File | SHA-256 |
|---|---|
| `crypto-aead.json` | `e07db29180a4a3937577041a9530be8bb6ef065c78052a7eab2955281c5ad46f` |
| `crypto-aead.degradation.json` | `038e5e002d377d1ae436aedbb5fe0ea095c17cd068356c5c6589ec1a24da9389` |
| `crypto-primitives.json` | `d6f8c73f89cd7323c9e6809a5a91ef79dc877461b85665d6282bd086f5c39625` |

Pre-fix `check --json` (exit 1, `baseline/check-before.json`) carried three
high G1b findings, one high G14 finding on the probe's `crypto-aead`
degradation record, and the G1b/G14/R1 findings from the stale C_static report:

```
G1b high analysis/…/q7-bridge-dispatch/inputs/specs/_closure/crypto-aead.json
  closure artifact is not directly under the canonical directory
  …/crypto-mixed/specs/_closure -- found under
  …/crypto-mixed/analysis/p4-verifier-fit/p4-5-probes/q7-bridge-dispatch/inputs/specs/_closure
```

Before the move, `validate-closure` printed `FAIL: 3 finding(s)` with exactly
those three G1b errors (the same findings are in
`baseline/check-before.json`). `stray-closure-probe.txt` reproduces the
behaviour on a scratch copy outside the pilot.

### Discovery scope, measured on a scratch copy outside the pilot

`stray-closure-probe.txt` (`/tmp/opencode/ligature151-probe-cstatic`, a copy of
the pilot's descriptor and artifact trees): with no stray directory,
`validate-closure` exits 0 (`OK … (2 discovered)`). Adding an arbitrary
`analysis/probe/specs/_closure/notes.txt` and `stray.json` makes it exit 1 with
two G1b errors — **any file, any extension, under any directory named
`specs/_closure` anywhere in the project tree** is treated as a closure
artifact. Removing the directory restores exit 0. The check is
directory-name-based, not content- or schema-based.

### Resolution

The whole retained Q7 `inputs/` tree (14 files, including the three closure
fixtures) was moved out of the pilot to:

```
/tmp/ligature-p4-5-probes/q7-bridge-dispatch/inputs/
```

The relative layout is unchanged, so all 14 members still verify against
`analysis/p4-verifier-fit/p4-5-probes/inputs.sha256`; `sha256sum -c` reported
`OK` for every member on 2026-11-17. The Q7 write-up is kept in place:
`commands.txt`, the captured stdout/stderr, the bridge specs, the generated
harnesses and both mock backends, plus
`q7-bridge-dispatch/RELOCATED-INPUTS.md` recording the destination and member
hashes. Replaying Q7 must copy `inputs/` into a scratch workspace outside the
pilot, never back under `crypto-mixed/analysis/`.

After the move and the C_static refresh in §2, `validate-closure` exits 0:

```
OK: all closure artifacts pass G1a/G1b and G17 profile/record consistency (2 discovered)
```

and `gate g14 --json` exits 0 with `crypto-kani` **released as degraded** under
the accepted CG3 record (`gate-g14.json`):

```
cluster: crypto-kani | status: degraded | closure_kind: bounded | findings: 1
degradation: {"ceiling": "per-instantiation",
              "conditions": ["generic_callees_type_universal_or_creusot_owned"]}
```

### Is "a stray copy invalidating the real record" documented behaviour?

**Partly — and the measured effect is narrower than the issue title implies.**

- Documented: the bundled CLI contract (§ G14 / degradation records) says a
  degradation record "filed outside `specs/_closure/` … is named as an error and
  excuses nothing", that `gate g14` therefore exits 1 on it and "never prints a
  cluster as released under it", and that "a record held but unusable is never
  the same as a workspace declaring no degradation at all". So refusing the
  stray **probe** record is documented.
- Not documented: that closure discovery walks the entire project tree and
  classifies **any** file under **any** nested directory named `specs/_closure`
  (probe inputs under `analysis/`, any filename or extension) as a closure
  artifact. The contract only states where real records must live; it never
  says retained scratch inputs in an evidence tree will be discovered.
  Reproducing it needs the scratch probe above.
- Measured effect: the canonical `specs/_closure/crypto-kani.degradation.json`
  was **not** refused. In `baseline/gate-g14-before.json` the `crypto-kani`
  cluster carried the accepted `medium` degradation finding and was blocked
  only by a separate high finding — "no C_static observation exists" — from the
  stale report. The stray record produced its own G1b/G14 errors and failed the
  workspace verdict. Removing the stray clears those; the C_static refresh in
  §2 is what actually releases `crypto-kani`. This attribution is recorded
  because the issue description attributes the block to the stray copy.

This is logged as `crypto-ligature-020` in `findings/limitations.jsonl`.

## 2. C_static re-extraction (fixed)

The committed `ci/results/c_static/crates_crypto-mixed-core.json` was produced
by extractor `0.2.0`, which 1.5.1 rejects as "a different or unknown extractor
version" (G1b, G14, R1/G16). The old bytes are preserved as
`baseline/c-static-old-extractor.json`
(`sha256:098548ae4614b3d1a964cc4933052c89abf05ed99c673870e15da2c79314141c`).

```sh
./tools/ligature/ligature.pyz extract-c-static \
  --target x86_64-unknown-linux-gnu --feature default
# exit 0
# wrote …/ci/results/c_static/crates_crypto-mixed-core.json:
#   35 discovered, 35 resolved, 0 unresolved (discovered-lower-bound)
```

`--feature default` is required: `crypto-ligature-019` still reproduces under
1.5.1. Without it the report records `config_scope.features: []` and a
different source digest (`stray-closure-probe.txt`):

| Extraction | `features` | `source_binding.digest` | Report SHA-256 |
|---|---|---|---|
| `--feature default` (committed) | `["default"]` | `sha256:6f8dad7f…` | `35773746aa5cfea7065581474803350315998f9921c1ee19e6562edec6455101` |
| without `--feature` | `[]` | `sha256:e730a131…` | `3f4096aec359914fd0c74a5e0cfec874c01fbe2256051fd6978466b7f8b3dea8` |

Report delta:

| Field | Old (0.2.0) | New (0.3.0) |
|---|---|---|
| `coverage_scope.extractor_version` | `0.2.0` | `0.3.0` |
| `source_binding.digest` | `sha256:fa3f1bef…` | `sha256:6f8dad7f…` |
| `source_binding.file_count` | 6 | 6 |
| callsites | 18 discovered / 18 resolved | 35 discovered / 35 resolved |
| `scanned_item_kinds` | `inherent-impl-method`, `trait-impl-method` | unchanged |

The re-extraction is deterministic: a second run wrote the identical
`35773746…` bytes (`c-static-extract.stdout.txt`). `crypto-ligature-018`
remains true in substance — the extractor still scans only inherent/trait impl
methods and still reports no free-function edge — but its "18 callsites"
figure is now `35` under 0.3.0.

`validate-callsites`:

```
exit 0
OK: all C_static reports pass G1a/G1b (incl. recomputed callsite coverage and
callee shapes) (1 discovered)
```

`gate r1-g16 --json` (`gate-r1-g16.json`):

```
exit 0
gate_acceptance: accepted
counts: discovered 35, checked 35, unresolved 0, undeclared_blocking 0,
        undeclared_warnings 0, configuration_mismatches 0
interaction_reconciliation: complete
source_resolution: complete
```

All 31 findings are `info` (internal-helper calls, intent without realization,
two declaration notes). **No new R1/G16 decision is outstanding**, so the
acceptance at #47 stands and nothing needs escalation.

## 3. G13 work-package refresh (prepared, blocked on a human grant)

`migrate --upgrade --json` exits 1, with `files_written: []`, no conflicts, and
G13 errors as its only post-upgrade findings (`migrate-upgrade.json`). Both
manifests pin the pre-1.5.1 managed-skill hash:

```
declared sha256:431a8179e9364591db288c707b6b5c8a3f28bd6799db5932482e14ca83bf588a
actual   sha256:ee39e9e64d510dbb918eb1cab6185aae8df5f4054f84a5f09766a2033df39735
.codex/skills/ligature/SKILL.md
```

`validate-work-package` exits 1 with the same single G13 error plus two
pre-existing `10.1/info` findings for each manifest
(`validate-work-package.stdout.txt`). `ci/manifest/**` is a protected root, so
the manifests were not hand-edited.

Prepared and refused only for the missing capability: fresh issue-196
exact-path grants plus the sanctioned `generate-work-package --regenerate`
calls, with the #134 Stage 7 plans copied and only their `issue` field changed
to `chainlink:196`. Current manifest bytes match the latest grant-backed
generation events, so `--regenerate` is the correct mode (not
`--adopt-existing`). Both refusal probes exited 2 with
`missing-or-invalid-grant` and changed nothing.

Exact grant and regeneration commands, expected derived changes, and the
post-regeneration acceptance checks are in
[`g13-regeneration-plan.md`](g13-regeneration-plan.md). They need the
operator's `ESCALATION:` checkpoint. After regeneration,
`migrate --upgrade --json` should exit 0 and `check --json` should stay at the
state below (one `medium` G14 finding).

## 4. Current gate state (steps 1 and 2 applied, step 3 pending)

| Check | Exit | Result |
|---|---|---|
| `version --verify` | 0 | 1.5.1, attested |
| `doctor` | 0 | current, adjudicator pinned |
| `validate-closure` | 0 | `OK … (2 discovered)` |
| `validate-callsites` | 0 | `OK … (1 discovered)` |
| `gate r1-g16 --json` | 0 | accepted, 35/35 resolved, no unresolved/undeclared |
| `write-set-check --issue 196 --json` | 0 | `write set is clean`; protected surface 49 files / 22 patterns reported |
| `check --json` | **0** | 37 `info` findings + **1 `medium`**: the accepted `crypto-kani` CG3 degradation; no high findings |
| `gate g14 --json` | **0** | `crypto-kani` `degraded`, `bounded`, per-instantiation degradation; 0 workspace findings |
| `migrate --upgrade --json` | **1** | G13 only, two manifests (§3) |

`check --json` matches the Stage 8C acceptance shape: only the accepted CG3
degradation (`medium`) remains blocking-adjacent, with `info` findings only.
`migrate --upgrade` is the single remaining exit-1 surface, pending the G13
grant and regeneration.

## Scope and safety checks

- No writes to `project-descriptor.json`, `specs/_closure/**`, `ci/manifest/**`,
  `crates/*/specs/**`, `scripts/**`, `docs/*-schema.json` or any other protected
  root. The only non-evidence change is the sanctioned
  `extract-c-static` rewrite of `ci/results/c_static/crates_crypto-mixed-core.json`.
- `ci/results/protected-writes.jsonl` is unchanged before and after every probe
  and gate run: `sha256:f640cef78c562ef768ffb6fae4f227950f1bd5f56b580153d7a49a6af943f39f`
  (`baseline/manifest-hashes.json`).
- No `git push`, no `authorize-write`, no hand edit of a manifest or closure
  record, no `git stash`.
- Every Kani-rerunning command (`check`, `gate g14`) ran with
  `CARGO_TARGET_DIR=/tmp/opencode/kani-target-196`, outside the pilot, and the
  commands ran one after another so only one harness ran at a time. No `target/`
  directory was created in the pilot.
- Evidence is confined to the issue's writable root
  `analysis/p4-verifier-fit/ligature-1.5.1/` plus the Q7 relocation record in
  the already-existing `analysis/p4-verifier-fit/p4-5-probes/` tree.

## Evidence index

| File | Contents |
|---|---|
| `baseline/check-before.json` | pre-fix `check --json` (exit 1; stray G1b + stale C_static) |
| `baseline/gate-g14-before.json` | pre-fix G14 (exit 1; crypto-kani blocked on C_static) |
| `baseline/c-static-old-extractor.json` | the 0.2.0 report, preserved |
| `baseline/manifest-hashes.json` | manifest hashes, stale/current skill pins, ledger hash |
| `baseline/version-verify.txt`, `doctor.stdout.txt` | binary identity and install health |
| `stray-closure-probe.txt` | scratch-copy G1b discovery scope and the `--feature` delta |
| `validate-closure.stdout.txt` | closure profile/record validation after the move |
| `c-static-extract.stdout.txt` | deterministic re-extraction (0.3.0, 35/35) |
| `validate-callsites.stdout.txt` | C_static G1a/G1b validation |
| `gate-r1-g16.json` | R1/G16 reconciliation, accepted, no new decision |
| `check-after.json` | final consolidated check (exit 0, one medium) |
| `gate-g14.json` | final G14 (exit 0, crypto-kani degraded under CG3) |
| `write-set-check-196.json` | write-set verdict for this issue |
| `migrate-upgrade.json` | post-upgrade validation, G13 only |
| `validate-work-package.stdout.txt` | G13 detail for both manifests |
| `stage-7-plan-WP-CRYPTO-MIXED-*-issue-196.json` | prepared Stage 7 plans (only `issue` differs from #134) |
| `generate-AEAD-refusal.json`, `generate-PRIMITIVES-refusal.json` | pre-grant refusals, nothing written |
| `g13-regeneration-plan.md` | human grant commands, sanctioned regeneration, acceptance |
