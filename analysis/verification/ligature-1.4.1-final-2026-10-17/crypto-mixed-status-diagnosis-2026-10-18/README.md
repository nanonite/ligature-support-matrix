# crypto-mixed `status --json`: diagnosis (2026-10-18)

Local issues: #146 (pilot) and #145 (epic #1 escalation). Follows
`../crypto-mixed-status-timeout-followup.md`, which recorded exit 124 at a
20-second bound.

## Identity

- Bundle SHA-256 `973b883b3f4d19e60950ce6b9f0247828459d60fadd05f0d6e29d17d19c31ab8`
  (Ligature 1.4.1, adjudicator `sha256:2f975350565f3dfb09682d69b34ed137ae1dc6342decb7cf9c986ed56a7d733a`).
- Pilot: a disposable `rsync -a` copy of `crypto-mixed/` at HEAD
  `13e602135232fb6f188125b17aa01cc1e2ffb3dd` with the uncommitted 1.4.1 install.
  The live pilot was not used.

## Method (black box)

`status_probe.sh` runs the command below with a 1200-second bound and logs the
process tree (`ps --forest`) about every 15 seconds. The bundle was not opened,
and nothing in its code was read or traced. The only observations are process
names and arguments.

```sh
timeout --kill-after=5s 1200 python3 -I tools/ligature/ligature.pyz status --json
```

## Result

- `result.txt`: **exit 0 after 286 s**. `status.stdout.json` is 23,420 bytes of
  valid JSON; stderr is empty.
- `ptree.log` (19 samples): while it runs, `status` starts `cargo-kani` →
  `cbmc` for the pilot's recorded Kani harnesses. Seen in the samples:
  `kani_proofs::kani_chacha20_c002_exact_length_65_boundary` (`--unwind 66`) and
  `kani_proofs::kani_poly1305_finalize_tag_length` (`--unwind 32`), each with
  `--exact --output-into-files --target-dir /tmp/ligature-kani-067-*`.
  Peak `cbmc` RSS in the samples was about 6.5 GB. Harnesses that finished
  between two samples may not appear in the log.
- After the run, `diff -rq` between the live pilot and the copy was empty, so
  `status` left no file changes in the workspace.
- The status output reports `installation_manifest.state=current`,
  `gate_integrity.state=pinned`, and cluster `crypto-kani` as
  `closure_kind=bounded`, `state=blocked`, with limitation
  `generic_callees_type_universal_or_creusot_owned`.

## Interpretation

The earlier 20 s and 180 s timeouts were not a hang. On this pilot, `status`
reruns the recorded bounded-model-check harnesses, so its runtime is set by
Kani/CBMC (here about 5 minutes and several GB of memory). It prints no
progress or diagnostic while doing so. The date-creusot control finishes in
under 30 s because that pilot has no Kani evidence to rerun.

The open upstream question is a design/UX one: should a status command rerun
verifiers by default, without saying so or offering a cheap mode? It is
reported upstream under the ligature-workspace issue linked from local #145.
