# Q7 probe inputs relocated out of the pilot (2026-11-17, chainlink #196)

The Q7 reproduction inputs were retained under
`analysis/p4-verifier-fit/p4-5-probes/q7-bridge-dispatch/inputs/` as copies of
the `/tmp/ligature-p4-5-probes/q7-bridge-dispatch` scratch workspace.

Ligature 1.5.1's G1b walks the whole project tree and treats **any** file under
**any** directory named `specs/_closure` as a closure artifact. The probe copies
therefore registered as non-canonical closure artifacts: `validate-closure`
failed the workspace and `check --json` carried three high G1b findings plus a
G14 finding refusing the probe's `crypto-aead` degradation record. See
[`README.md`](README.md) §1 and [`stray-closure-probe.txt`](stray-closure-probe.txt).

## Destination

The whole `inputs/` tree was moved out of the pilot to:

```
/tmp/ligature-p4-5-probes/q7-bridge-dispatch/inputs/
```

Its relative layout is unchanged. `relocated-q7-inputs.sha256` lists the 14
moved members with their SHA-256; `sha256sum -c` reported `OK` for all of them
after the move. The same hashes are the `q7-bridge-dispatch/inputs/` rows of
`analysis/p4-verifier-fit/p4-5-probes/inputs.sha256`.

## What stayed in the pilot

The Q7 write-up and captured results remain in
`analysis/p4-verifier-fit/p4-5-probes/q7-bridge-dispatch/`: `commands.txt`, the
original `README` section, `check-bridges.stdout.txt`,
`check-bridges.stderr.txt`, the three bridge specs, the three generated Kani
harnesses, and both mock backend scripts. A `RELOCATED-INPUTS.md` note in that
directory records the move for local readers.

To replay Q7, copy `inputs/` into a scratch workspace **outside** the pilot, or
use the relocated tree directly. Never restore a `specs/_closure` directory
under `crypto-mixed/analysis/`.
