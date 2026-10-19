# Prompt for the Ligature upstream owner: issues #166–#169

Work in `/home/goya/agent-workspace/ligature-workspace`. Resolve upstream
Ligature Chainlink issues **#169, #168, #166 and #167** and ship one attested
release for downstream black-box verification. Read the repository
instructions, and each issue with all its comments, before editing. This
prompt authorizes source work in the upstream project only. The port
workspace keeps its black-box rule. Do not edit anything under
`/home/goya/storage/full-ligature-port-workspace`; reading the evidence paths
named below is fine.

Use the upstream tracker explicitly:

```sh
for i in 169 168 166 167 139 138 137 161 143; do
  chainlink --db /home/goya/agent-workspace/ligature-workspace/.chainlink --json issue show $i
done
```

| Upstream | Port-workspace local | Priority | Topic |
|---|---|---|---|
| #169 | #149 | high (soundness) | G14 and R1/G16 accept a stale, empty C_static report |
| #168 | #148 | medium | write-set-check flags the bridge harnesses that G9 requires |
| #166 | #145 | medium | `status --json` silently reruns Kani harnesses |
| #167 | #147 | medium | the "shipped CLI contract" cited by help is unreachable |

Baseline: Ligature 1.4.1, bundle SHA-256
`973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`, source
`742cb253e0cb9753c7a34a0c32559936130e03ab`, adjudicator
`sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`.
Downstream evidence lives under
`/home/goya/storage/full-ligature-port-workspace/date-creusot/analysis/verification/ligature-1.4.1-final-2026-10-17/`
(below, `$EV`). Work in priority order: #169, #168, #166, #167.

## #169: stale, empty call-graph observation accepted (fix first)

The crypto-mixed pilot's committed `ci/results/c_static/crates_crypto-mixed-core.json`
was extracted before the Rust source existed. It has 0 call sites,
`local_concepts: []`, and no binding to the source. With it, `gate-r1-g16`
exits 0 (`accepted`, 0 checked; declared interactions shown only as info) and
`gate-g14` exits 0 (`degraded` on CG3 only). A fresh `extract-c-static`
finds 16 / 12 / 4 unresolved, and G14 then exits 1 (`blocked`). So call-site
validation was silently skipped for every earlier pass. Evidence:
`$EV/crypto-mixed-stale-cstatic-2026-10-18/` (both reports and captures) and
`$EV/crypto-mixed-134-regeneration-2026-10-18/`.

Required:
- Bind each C_static report to the source it describes when it is extracted,
  e.g. a digest over the scanned crate files plus extractor version and
  config scope. Keep `discovered-lower-bound` semantics and the per-call-site
  `syntax_hash`.
- Make R1/G16 and G14 (and `check`/`status`, which read them) recompute the
  binding. When it is missing or does not match the current source, refuse or
  report a blocking finding, naming `extract-c-static --target <triple>` as the
  sanctioned next action.
- Treat an observation with zero local concepts or call sites as suspect
  when the closure's work-package manifests own functions in that crate.
- Legacy reports without a binding fail closed with that actionable
  diagnostic. Never accept them silently.

Acceptance: source and packaged-binary regressions for: source changed after
extraction (refused); empty report extracted before the source existed
(refused); fresh extraction (accepted); legacy unbound report (actionable
failure). Also include a fixture reproducing the crypto-mixed sequence above.
Port-workspace local #127 (stale Verus report accepted) is the same soundness
class for a different artifact. Note it if a shared freshness mechanism
applies, but don't widen this release's scope without saying so.

## #168: G9 harnesses vs write-set-check

`check-bridges` writes `ci/harness/<bridge_id>.<verifier>.rs` and
`ci/results/bridge_checks/<bridge_id>.json`. `gate-g9` requires the harness
file: without it, G9 exits 1 with "no generated harness … run
`pipeline.py check-bridges`". `write-set-check` reports exactly those harness
files as out-of-set violations, tracked or untracked, on 1.3.11, 1.3.12, 1.4.0
and 1.4.1. The `bridge_checks` JSON is accepted. So G9 passing and a clean
write-set are mutually exclusive without widening a protected descriptor.
Evidence: `$EV/crypto-mixed-harness-writeset-2026-10-18/` (README plus
per-step captures).

Required: make the two commands agree with no descriptor change. Either
recognize generated bridge harnesses as pipeline artifacts, or generate them
into a location write-set-check already treats as canonical. Vouch only for
bytes the generator would produce, or bytes matching the recorded bridge-check
record, so a hand-edited harness is still flagged. Fix the diagnostic to name
`ligature.pyz check-bridges`.

Acceptance: `check-bridges` → `gate-g9` exit 0 → `write-set-check` clean. An
edited harness is flagged. A missing harness gives an actionable G9 error
naming the right command. Existing pilots need no descriptor edit.

## #166: `status --json` silently reruns verifiers

On the Kani pilot, `status --json` runs `cargo-kani` → `cbmc` for the
recorded harnesses: about 286 s, peak about 6.5 GB RSS, no progress output.
Bounded callers at 20 s or 180 s get exit 124 with no output. date-creusot's
status finishes in under 30 s. Today `gate-g14 --json` took 145 s and
`check --issue N --json` took 284 s on the same pilot. Evidence:
`$EV/crypto-mixed-status-diagnosis-2026-10-18/`.

Required: `status` is cheap and read-only by default. It reports recorded
state with freshness indicators and does not run verifiers. Add an explicit
opt-in (e.g. `--revalidate`) for reruns. Any command that runs a verifier
prints per-harness progress on stderr. Document which commands execute
verifiers and their expected cost (help, SKILL.md, the CLI contract). If the
status JSON changes, version its schema.

Acceptance: on a Kani fixture, `timeout 20 python3 -I ligature.pyz status
--json` returns valid JSON. A regression test asserts that default `status`
spawns no verifier process. The opt-in path reruns with progress output.

## #167: unreachable CLI contract

Every subcommand's help says "see the shipped CLI contract for per-command
outcomes", and top-level help cites `docs/cli-contract.md` §3 (`gate`) and §6
(`report`). The file is not installed by `init` or `migrate`, is not
doctor-managed, and `schema show cli-contract` exits 1 ("unknown schema").
Evidence: `$EV/replay/out/date-ligature-023.out`, `$EV/replay/review-1.4.1.md`.

Required: make the contract reachable from the installed artifact. Install it
as a managed resource, or add a command that prints it (e.g. `ligature.pyz
contract [--json]`), or both. Update the help references to name something
reachable. The contract enumerates per-command exit codes and JSON outcomes,
matching actual behavior.

Acceptance: reachable after a fresh `init` and after `migrate --upgrade` from
1.4.1. A test checks that every parser subcommand has a contract entry.

## Housekeeping (no code)

These upstream pilot tasks are already done downstream. Verify each with
read-only reads of the port workspace, then close it with the evidence:
- **#137** (crypto-mixed Cargo.lock): created 2026-10-14 under exact grant
  `GW-a1dcdf9a9708`, SHA-256 `500245d4c61242e614363a03597f8c88f7c827d02115ffbc92f8dabd774f5fc1`.
  `cargo metadata --locked` passes (local #134).
- **#138** (Kani scope vs manifest domains): bounded scopes reviewed and
  reapproved for I-CRYPTO-MIXED-001/002/003; manifests regenerated 2026-10-14
  (local #134 comments).
- **#139** (G13 managed-skill hashes): both manifests regenerated 2026-10-18
  with `generate-work-package --regenerate` under human grants
  `GW-fde9361f89c4` / `GW-37dc6f039aad`. Both `validate-work-package` runs
  exit 0. crypto-mixed commit `2f2152d`.

Downstream 1.4.1 verification for **#161/#143** is complete (local #144
closed). The remaining downstream items are #166–#169 and the pilot's own
Stage 8A call-site work. Update #161/#143 as you judge appropriate.

## Constraints

- Reproduce in upstream fixtures or disposable `/tmp` copies only. Never
  edit downstream pilots, manifests, descriptors, ledgers or policy.
- Keep human checkpoints intact (grants, approve/ruling/promotion). Don't
  weaken assurance or write-set policy to make a test pass.
- cbmc can use about 6.5 GB per harness on this machine, so run Kani-backed
  tests one at a time.

## Release and handoff

Use the 1.4.1 procedure: clean source commit;
`releases/vX.Y.Z/{ligature.pyz,NOTICE,PROVENANCE.json,SHA256SUMS,THIRD_PARTY_NOTICES.txt}`;
`sha256sum -c` OK; `version --verify` attested; a scratch `migrate --upgrade`
from 1.4.1 returning `result=current`, no conflicts. Post a handoff comment
on #161 with:
1. Version, source commit, artifact SHA-256, content/adjudicator hash, fixed
   issue IDs, and per-issue verification evidence (source tests plus
   exact-artifact CLI checks).
2. **Every managed or gate-pinned resource whose hash changed, especially
   `.codex/skills/ligature/SKILL.md`.** A SKILL.md change breaks G13 in every
   generated work-package manifest and forces another human-granted
   regeneration downstream. Avoid unnecessary churn, and state it plainly if
   it happens.
3. Downstream-visible behavior changes and migration steps, e.g. "existing
   C_static reports are now unbound; rerun `extract-c-static`" (#169), or a
   new managed contract file (#167).
4. Exact black-box re-verification commands per issue, so the port workspace
   can confirm each fix on its pilots. Downstream will close local
   #145/#147/#148/#149 only after its own verification.
