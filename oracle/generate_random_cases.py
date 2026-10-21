#!/usr/bin/env python3
"""Generate deterministic SwissTable oracle action sequences (SplitMix64 v1)."""

import argparse
import json
from pathlib import Path

UPSTREAM_COMMIT = "2065f4ded0558c6f89fee67c8e5228feb4eb960e"
MASK64 = (1 << 64) - 1


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & MASK64

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64


def make_cases(seed, count):
    rng = SplitMix64(seed)
    cases = []
    for number in range(1, count + 1):
        actions = ["reserve(8)"]
        for _ in range(24):
            choice = rng.next() % 10
            key = 1 + (rng.next() % 18)
            if choice < 4:
                value = rng.next() % 1000000
                actions.append(f"insert({key},{value})")
            elif choice < 6:
                actions.append(f"erase({key})")
            elif choice < 8:
                actions.append(f"contains({key})")
            elif choice == 8:
                actions.append(f"reserve({rng.next() % 4})")
            else:
                actions.append("clear()")
        cases.append({
            "case_id": f"random-table-sequence-{number:04d}",
            "op": "map_sequence",
            "inputs": {"actions": ";".join(actions)},
            "oracle_scope": "compare",
        })
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    if args.count < 1:
        raise SystemExit("--count must be positive")
    root = Path(__file__).resolve().parent
    case_path = root / "random-cases.jsonl"
    manifest_path = root / "random-cases.jsonl.manifest.json"
    cases = make_cases(args.seed, args.count)
    case_path.write_text("".join(json.dumps(c, separators=(",", ":")) + "\n" for c in cases), encoding="utf-8")
    manifest = {
        "case_file": case_path.name,
        "source": "random",
        "seed": args.seed,
        "generator": "splitmix64-v1",
        "command": f"python3 oracle/generate_random_cases.py --seed {args.seed} --count {args.count}",
        "upstream_commit": UPSTREAM_COMMIT,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(cases)} cases in {case_path}; seed={args.seed}")


if __name__ == "__main__":
    main()
