# Ligature 1.4.2 downstream verification — 2026-10-18

## Artifact and installation

- Bundle SHA-256: c4d989f3c72f7c9439cefb9a787b5ce23ad8467204fd61d9e00b761675c5b184
- Source commit: 5749590e076bd1bad048d57a0df7f38151647dbd
- Content/adjudicator: sha256:2e0616b7ff7d54776c4798ba6a1f447136f4434f211b9ccd655e753d19f3e928
- Installed into date-creusot, crypto-mixed, and swisstable-verus. In each pilot, sha256sum -c SHA256SUMS and python3 -I tools/ligature/ligature.pyz version --verify passed. migrate --upgrade --json returned result=current, with no conflicts or required human action. doctor exited 0 in all three.
- All three contract --json calls exited 0, returning valid ligature.cli-contract.v1 output (129,843 bytes), SHA-256 sha256:6d3d6a27c3f6a18cd9f246d8a72d9da91a9197bca0890e7f053c7427e256882f; the contract includes command outcomes and gate-g14.

## #166: default status no longer reruns Kani

Live command in crypto-mixed: python3 -I tools/ligature/ligature.pyz status --json.
Exit 0, 1.747 seconds, 15,468 bytes valid JSON, empty stderr. Passive /proc child-process sampling observed no Kani/CBMC process. status --help states that default checks recorded source/harness hashes; --revalidate opts into Kani reruns and can take minutes / several GB. A ptrace-based trace was attempted but the sandbox denied PTRACE_TRACEME; passive sampling was used instead.

## #167: contract is reachable

contract --json passed from each of the three pilot-local binaries with the same contract hash above. Top-level help and command help now direct the operator to ligature contract [--json].

## #168: generated bridge harnesses are recognized by write-set checks

Live crypto-mixed commands:
- write-set-check --json: exit 0, no violations.
- gate-g9: exit 0, both bridges pass.

Scratch-only negative probes (scratch root /tmp/ligature-1.4.2-bridge-scratch, copied from crypto-mixed; the live harnesses were not edited):
- Appending one newline to ci/harness/BR-CRYPTO-MIXED-001.kani.rs made write-set-check --json exit 1 and name that harness as outside the write set.
- Removing that harness made gate-g9 exit 1 with the action ligature.pyz check-bridges.

## #169: stale/unbound C_static is rejected; current report is source-bound

Before refreshing the live crypto-mixed report, the 1.4.1 C_static report had 16 discovered / 12 resolved / 4 unresolved and no source binding. On Ligature 1.4.2:
- validate-callsites: exit 1, G1b says the legacy report has no source binding and directs ligature extract-c-static --target x86_64-unknown-linux-gnu.
- gate-r1-g16 --json: exit 1, gate_acceptance=blocked; rejected the report and reported no valid C_static reconciliation, explicitly directing extraction.
- A scratch-only replay with the historical empty 0/0/0 report from the 1.4.1 evidence folder also made validate-callsites and gate-r1-g16 --json exit 1; R1/G16 did not treat an empty reconciliation as a pass.

Then the supported live command python3 -I tools/ligature/ligature.pyz extract-c-static --target x86_64-unknown-linux-gnu exited 0 and wrote 16 discovered / 12 resolved / 4 unresolved. The report in ../crypto-mixed/ci/results/c_static/crates_crypto-mixed-core.json (copied here) carries:
- source binding SHA-256 sha256:2fe9ef3ec8261c34a0acfde39a59af0a7baea13b2d8367e6f714d615ac7694e0, 6 files;
- target x86_64-unknown-linux-gnu, no features/cfg;
- coarse-syntactic-callgraph extractor version 0.2.0, completeness discovered-lower-bound.
validate-callsites then exited 0.

After that fresh extraction, gate-r1-g16 --json exited 1 with 16 discovered, 9 checked, 4 unresolved, and 3 undeclared blocking direct cross-concept calls. The full gate-g14 --json run exited 1 after 151.1 seconds and revalidated the three named Kani obligations. It blocked on the four unresolved calls (including G17 declaring 0 but computing 4); the accepted CG3 degradation remains per-instantiation. Thus the former stale-empty false pass is fixed, while the live port still has real call-reconciliation/G14 blockers.

## G13 and write-set follow-up

- Ligature 1.4.2 changes managed .codex/skills/ligature/SKILL.md and .ligature/schemas/project-state.schema.json hashes. The date-creusot and crypto-mixed work-package validations now fail G13 against their old hashes. No protected manifests were edited or regenerated because fresh human-issued exact-path grants are required. SwissTable's manifest validation passes.
- Crypto-mixed and swisstable-verus write-set-check --json exit 0. Date-creusot's existing .gitignore and PORT-GAPS.md out-of-set findings remain; no new backup/evidence path was added to its write set.
- No source test suites were run.

The full G14 check was also run against the historical empty report in the isolated scratch root /tmp/ligature-1.4.2-empty-cstatic-scratch: it exited 1 after 143.3 seconds, revalidated the three Kani obligations, and blocked both required bridges plus the unresolved-call condition because no valid C_static observation existed. Its finding explicitly says an unobserved call graph is not a resolved one and directs extraction. The captured result is crypto-mixed-empty-cstatic-g14-scratch.json.
