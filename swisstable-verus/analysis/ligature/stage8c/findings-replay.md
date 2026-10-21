# Issue #33 fresh replay audit

Result: all 76 current ledger IDs are represented below. Each executable `repro_cmd` was attempted from a fresh per-finding extraction of `/tmp/issue33-replay-85264497f7/pilot-pristine-76.tar.gz` under `/tmp/issue33-replay-85264497f7/runs-v3/` (and fresh `runs-v4` copies for #75/#76). Absolute pilot paths were redirected to the extracted copy; scratch/build paths were confined to per-finding `/tmp` directories. Each run had isolated HOME/XDG/TMPDIR/CARGO_HOME, offline Cargo, and preserved source modes. The prose-only command was marked unavailable. The live pilot, ledger, descriptor, workspace files, and Chainlink DB were not edited.

Counts by target disposition: 31 exit matches with the target reached; 13 exit mismatches with the target reached; 32 unavailable (8 permission-denied direct pyz invocations, 1 prose-only repro, 17 Nix Git-flake failures before Verus, 6 helper-runner Nix `/tmp`-flake failures before Cargo/Verus). Total: 76. For reconciliation, the raw runner-status tally is 49 exit-code matches, 18 exit-code mismatches, and 9 marked not-replayed (IDs 1–76). That tally counts expected wrapper exits as matches even when Nix failed before invoking Verus. This report therefore reclassifies those 23 flake-blocked rows as unavailable, rather than successful target replays. Three of the eight EACCES rows also have raw shell codes differing from the ledger; all eight remain unavailable. The report retains each raw code below.

`Expected` is the ledger `exit_code`; `observed` is the outer repro-shell exit unless shown as none. `MISMATCH` compares the outer observed code to the ledger value. `UNAVAILABLE` means the target executable/proof did not run to the finding being audited. Printed inner statuses are distinguished where they differ from the shell exit.

## Per finding

| # | Finding | Expected exit | Observed exit/outcome | Status and reason | Log |
|---:|---|---:|---|---|---|
| 1 | `swisstable-mcp-001` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `01-swisstable-mcp-001.log` |
| 2 | `swisstable-mcp-002` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `02-swisstable-mcp-002.log` |
| 3 | `swisstable-mcp-003` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `03-swisstable-mcp-003.log` |
| 4 | `swisstable-mcp-004` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `04-swisstable-mcp-004.log` |
| 5 | `swisstable-mcp-005` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `05-swisstable-mcp-005.log` |
| 6 | `swisstable-mcp-006` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `06-swisstable-mcp-006.log` |
| 7 | `swisstable-mcp-007` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `07-swisstable-mcp-007.log` |
| 8 | `swisstable-mcp-008` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `08-swisstable-mcp-008.log` |
| 9 | `swisstable-mcp-009` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `09-swisstable-mcp-009.log` |
| 10 | `swisstable-mcp-010` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `10-swisstable-mcp-010.log` |
| 11 | `swisstable-mcp-011` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `11-swisstable-mcp-011.log` |
| 12 | `swisstable-mcp-012` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `12-swisstable-mcp-012.log` |
| 13 | `swisstable-ligature-001` | 1 | 126 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `13-swisstable-ligature-001.log` |
| 14 | `swisstable-ligature-002` | 0 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `14-swisstable-ligature-002.log` |
| 15 | `swisstable-ligature-003` | 0 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `15-swisstable-ligature-003.log` |
| 16 | `swisstable-ligature-004` | 0 | 1 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `16-swisstable-ligature-004.log` |
| 17 | `swisstable-mcp-013` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `17-swisstable-mcp-013.log` |
| 18 | `swisstable-mcp-014` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `18-swisstable-mcp-014.log` |
| 19 | `swisstable-mcp-015` | 0 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `19-swisstable-mcp-015.log` |
| 20 | `swisstable-mcp-016` | 0 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `20-swisstable-mcp-016.log` |
| 21 | `swisstable-mcp-017` | 0 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `21-swisstable-mcp-017.log` |
| 22 | `swisstable-mcp-018` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `22-swisstable-mcp-018.log` |
| 23 | `swisstable-mcp-019` | 1 | 0 | **UNAVAILABLE** — The recorded command directly executes tools/ligature/ligature.pyz, but the copied file is mode 664 and not executable; shell reported Permission denied, so the intended Ligature command did not run. | `23-swisstable-mcp-019.log` |
| 24 | `swisstable-ligature-005` | 1 | 0 | **MISMATCH** — outer command returns 0 after run-proofs; captured conclusion reports draft-validation failures, so the stored 1 is not the outer shell status. | `24-swisstable-ligature-005.log` |
| 25 | `swisstable-ligature-006` | 1 | initial 2; seeded rerun 0 | **MISMATCH** — initial exact replay exits 2 because the named scratch proof.txt parent is absent; seeded rerun exits 0 and prints inner approval failures [exit 1]. Expected 1. | `25-swisstable-ligature-006.log; 25-swisstable-ligature-006-seeded.log` |
| 26 | `swisstable-ligature-007` | 1 | 0 | **MISMATCH** — outer command exits 0; log prints check --json -> exit 1, then trailing inspection succeeds. | `26-swisstable-ligature-007.log` |
| 27 | `swisstable-ligature-008` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `27-swisstable-ligature-008.log` |
| 28 | `swisstable-ligature-009` | 1 | 0 | **MISMATCH** — outer command exits 0 after collecting draft files; differs from stored 1. | `28-swisstable-ligature-009.log` |
| 29 | `swisstable-ligature-010` | 1 | 0 | **MISMATCH** — stage45 log prints EXIT=1 for G9 bridge syntax errors; wrapper shell returns 0. | `29-swisstable-ligature-010.log` |
| 30 | `swisstable-ligature-011` | 1 | 0 | **MISMATCH** — wrapper shell returns 0 after stage45 scratch proof/accept-policy flow; stored status is 1. | `30-swisstable-ligature-011.log` |
| 31 | `swisstable-ligature-012` | 1 | 0 | **MISMATCH** — initial exact replay cannot create the destination because its /tmp/opencode/s2 parent is absent (rsync 11); after creating only that scratch parent, the command prints inner exit=1 but wrapper returns 0. | `31-swisstable-ligature-012.log; 31-swisstable-ligature-012-parent.log` |
| 32 | `swisstable-ligature-013` | 1 | 0 | **MISMATCH** — read-only sed command emits the requested text and exits 0; stored expected 1 is not its shell status. | `32-swisstable-ligature-013.log` |
| 33 | `swisstable-ligature-014` | 2 | 0 | **MISMATCH** — initial rsync fails because /tmp/opencode/s2 parent is absent; after creating it, output is after=2/before=0 but wrapper returns 0 (stored expected 2). | `33-swisstable-ligature-014.log; 33-swisstable-ligature-014-parent.log` |
| 34 | `swisstable-verus-001` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `34-swisstable-verus-001.log` |
| 35 | `swisstable-verus-002` | 1 | 1 | **MATCH** — target ran; outer exit matches ledger. | `35-swisstable-verus-002.log` |
| 36 | `swisstable-verus-003` | 1 | 0 | **MISMATCH** — grep exits 0 because its broad tokens occur in a source comment; no unsafe/raw-pointer implementation was demonstrated. | `36-swisstable-verus-003.log` |
| 37 | `swisstable-verus-004` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `37-swisstable-verus-004.log` |
| 38 | `swisstable-verus-005` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `38-swisstable-verus-005.log` |
| 39 | `swisstable-verus-006` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `39-swisstable-verus-006.log` |
| 40 | `swisstable-verus-008` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `40-swisstable-verus-008.log` |
| 41 | `swisstable-verus-009` | 0 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `41-swisstable-verus-009.log` |
| 42 | `swisstable-verus-010` | 0 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `42-swisstable-verus-010.log` |
| 43 | `swisstable-verus-011` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `43-swisstable-verus-011.log` |
| 44 | `swisstable-verus-012` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `44-swisstable-verus-012.log` |
| 45 | `swisstable-verus-013` | 0 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `45-swisstable-verus-013.log` |
| 46 | `swisstable-verus-014` | 0 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `46-swisstable-verus-014.log` |
| 47 | `swisstable-verus-015` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `47-swisstable-verus-015.log` |
| 48 | `swisstable-verus-016` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `48-swisstable-verus-016.log` |
| 49 | `swisstable-verus-017` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `49-swisstable-verus-017.log` |
| 50 | `swisstable-verus-018` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `50-swisstable-verus-018.log` |
| 51 | `swisstable-verus-019` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `51-swisstable-verus-019.log` |
| 52 | `swisstable-verus-020` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `52-swisstable-verus-020.log` |
| 53 | `swisstable-verus-021` | 0 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `53-swisstable-verus-021.log` |
| 54 | `swisstable-spec-008` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `54-swisstable-spec-008.log` |
| 55 | `swisstable-verus-022` | 1 | 0 | **MISMATCH** — errors-by-fn now reports 0 error locations in 0 functions (stored expected 1). | `55-swisstable-verus-022.log` |
| 56 | `swisstable-verus-023` | 1 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `56-swisstable-verus-023.log` |
| 57 | `swisstable-verus-024` | 1 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `57-swisstable-verus-024.log` |
| 58 | `swisstable-verus-025` | 0 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `58-swisstable-verus-025.log` |
| 59 | `swisstable-verus-028` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `59-swisstable-verus-028.log` |
| 60 | `swisstable-verus-029` | 0 | 0 | **UNAVAILABLE** — runner resolved '/tmp' as the flake path and stopped before Cargo/Verus; target proof did not run. | `60-swisstable-verus-029.log` |
| 61 | `swisstable-verus-030` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `61-swisstable-verus-030.log` |
| 62 | `swisstable-verus-031` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `62-swisstable-verus-031.log` |
| 63 | `swisstable-spec-001` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `63-swisstable-spec-001.log` |
| 64 | `swisstable-spec-002` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `64-swisstable-spec-002.log` |
| 65 | `swisstable-spec-003` | 0 | 1 | **MISMATCH** — grep no longer finds capacity_bits <= 62; exits 1 (stored expected 0). | `65-swisstable-spec-003.log` |
| 66 | `swisstable-spec-004` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `66-swisstable-spec-004.log` |
| 67 | `swisstable-spec-005` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `67-swisstable-spec-005.log` |
| 68 | `swisstable-spec-006` | 1 | 1 | **UNAVAILABLE** — Nix could not open workspace flake Git repository; Verus was never launched. | `68-swisstable-spec-006.log` |
| 69 | `swisstable-verus-032` | 0 | none | **UNAVAILABLE** — The repro_cmd is prose only: it names tcb.md, the pinned Verus version, and a transcript, but gives no executable command, target file/arguments, or working directory. Reconstructing those choices would change the recorded repro. | `—` |
| 70 | `swisstable-verus-033` | 101 | 101 | **MATCH** — target ran; outer exit matches ledger. | `70-swisstable-verus-033.log` |
| 71 | `swisstable-verus-034` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `71-swisstable-verus-034.log` |
| 72 | `swisstable-ligature-015` | 1 | 1 | **MATCH** — target ran; outer exit matches ledger. | `72-swisstable-ligature-015.log` |
| 73 | `swisstable-verus-035` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `73-swisstable-verus-035.log` |
| 74 | `swisstable-verus-036` | 0 | 0 | **MATCH** — target ran; outer exit matches ledger. | `74-swisstable-verus-036.log` |
| 75 | `swisstable-verus-037` | 1 | default isolation 100; no-isolation 0 (16 passed, 0 skipped) | **MISMATCH** — default Miri run failed on fixture open under isolation, as symptom describes, but raw exit differs from stored value; no-isolation run passes 16/16. | `75-swisstable-verus-037-default.log; 75-swisstable-verus-037-no-isolation.log` |
| 76 | `swisstable-ligature-016` | 1 | 1 | **MATCH** — fresh gate replay ran; exit matches. Zero eligible candidate clusters; gate-g14 reports no closure directory. | `76-swisstable-ligature-016.log` |

### Replay artifact index

- Main per-record logs: `replay-logs/logs-v3/`.
- #25 scratch-seeded rerun: `replay-logs/logs-supp/25-swisstable-ligature-006-seeded.log`.
- #31/#33 scratch-parent reruns: `replay-logs/logs-supp/`.
- #75 Miri default/no-isolation outputs and #76 gate output: `replay-logs/logs-v4/`.
- An initial exploratory attempt stopped before completion and is excluded; audited results are from the fresh corrected `runs-v3`/`runs-v4` extractions.
