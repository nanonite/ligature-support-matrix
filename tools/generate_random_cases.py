#!/usr/bin/env python3
"""Seeded random case generator for the date-creusot differential oracle.

Generates the `random-*` cases of `oracle/cases.jsonl` (protocol section 8,
source 3). The output is fully deterministic for a given seed: the same
seed always produces the same case lines, in the same order.

Usage (from the pilot root):

    python3 tools/generate_random_cases.py --seed 20260924

The generated lines are merged into `oracle/cases.jsonl` (sorted by
case_id); `oracle/cases.jsonl.manifest.json` records the seed, generator
version, and this command so the random subset is reproducible.

Domains follow the operation contract (oracle/operations.md):
  * days_from_civil / ymd_ok: year in [-32767, 32767], month in [1, 12],
    day in [1, 31] (valid dates; invalid-domain probes are hand-written
    `boundary-*` cases, not random ones).
  * civil_from_days / weekday_from_days / iso_weekday_from_days: z in
    [-12687428, 11248737], the range the C++ era decomposition is defined
    over (years [-32767, 32767]).
"""

import argparse
import random

# Operation contract domains (see oracle/operations.md).
YEAR_MIN, YEAR_MAX = -32767, 32767
MONTH_MIN, MONTH_MAX = 1, 12
DAY_MIN, DAY_MAX = 1, 31
Z_MIN, Z_MAX = -12687428, 11248737

# Case counts per operation. ymd_ok deliberately mixes valid and invalid
# inputs (~40% invalid) to probe the validity predicate differentially.
COUNTS = {
    "days_from_civil": 16,
    "civil_from_days": 12,
    "weekday_from_days": 10,
    "ymd_ok": 14,
    "iso_weekday_from_days": 10,
}

INVALID_MONTHS = (0, 13)
INVALID_DAYS = (0, 32)


def generate(seed):
    rng = random.Random(seed)
    cases = []
    for op, count in COUNTS.items():
        for index in range(1, count + 1):
            case_id = "random-{}-{:04d}".format(op.replace("_", "-"), index)
            if op == "days_from_civil":
                inputs = {
                    "y": rng.randint(YEAR_MIN, YEAR_MAX),
                    "m": rng.randint(MONTH_MIN, MONTH_MAX),
                    "d": rng.randint(DAY_MIN, DAY_MAX),
                }
            elif op == "ymd_ok":
                if rng.random() < 0.4:
                    m = rng.choice(INVALID_MONTHS + (MONTH_MIN, MONTH_MAX))
                    d = rng.choice(INVALID_DAYS + (DAY_MIN, DAY_MAX))
                else:
                    m = rng.randint(MONTH_MIN, MONTH_MAX)
                    d = rng.randint(DAY_MIN, DAY_MAX)
                inputs = {
                    "y": rng.randint(YEAR_MIN, YEAR_MAX),
                    "m": m,
                    "d": d,
                }
            else:
                inputs = {"z": rng.randint(Z_MIN, Z_MAX)}
            cases.append((case_id, op, inputs))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    for case_id, op, inputs in generate(args.seed):
        print('{{"case_id":"{}","op":"{}","inputs":{}}}'.format(
            case_id, op,
            "{" + ",".join(
                '"{}":{}'.format(key, value) for key, value in inputs.items()
            ) + "}"))


if __name__ == "__main__":
    main()
