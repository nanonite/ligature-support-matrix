#!/usr/bin/env python3
"""Derive swisstable-verus/upstream/test-baseline.txt from a ctest --output-junit run.

Usage (from the pilot root):
  python3 analysis/upstream/make-test-baseline.py \\
      --junit analysis/upstream/ctest-results.xml \\
      --out upstream/test-baseline.txt

The baseline is the P2 parity reference: the exact set of upstream CTest tests
and their status at the pinned commit. Mirrors date-creusot/upstream/test-baseline.txt.
"""

import argparse
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET

SUMMARY_RE = re.compile(r"\[\s*PASSED\s*\]\s+(\d+) tests?\.")
RUNNING_RE = re.compile(r"\[=+\]\s+Running\s+(\d+) tests?\s+from\s+(\d+) test suites?\.")
SUITE_RE = re.compile(r"\[\s*FAILED\s*\]\s+(\d+) tests?\.")


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              check=True).stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pin-json", default="upstream/upstream-pin.json")
    args = ap.parse_args()

    junit = pathlib.Path(args.junit)
    root = ET.parse(junit).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    results = []
    gtest_passed = 0
    gtest_running = 0
    gtest_suites = 0
    for suite in suites:
        for case in suite.findall("testcase"):
            name = case.get("name")
            skipped = case.find("skipped") is not None
            failed = bool(case.findall("failure")) or case.get("status") == "fail"
            if skipped:
                status = "not_run"
            elif failed:
                status = "fail"
            else:
                status = "pass"
            results.append((name, status))
            out = ""
            for tag in ("system-out", "system-err"):
                node = case.find(tag)
                if node is not None and node.text:
                    out += node.text
            gtest_passed += sum(int(m) for m in SUMMARY_RE.findall(out))
            for m in RUNNING_RE.findall(out):
                gtest_running += int(m[0])
                gtest_suites += int(m[1])

    results.sort(key=lambda r: r[0])
    counts = {s: sum(1 for _, t in results if t == s) for s in ("pass", "fail", "not_run")}

    pin = json.loads(pathlib.Path(args.pin_json).read_text())

    lines = []
    lines.append("# abseil-cpp upstream test baseline (parity reference for P2)")
    lines.append("# repo=" + pin["repo"])
    lines.append("# pinned_sha=" + pin["commit"])
    lines.append("# pinned_tag=" + pin["tag"])
    lines.append("# pinned_commit_date=" + pin["commit_date"])
    lines.append("# upstream_version=" + pin["upstream_version"])
    lines.append("# runner=ctest")
    lines.append("# cmake_source=" + pin["cmake_source"])
    lines.append("# build_dir=" + pin["build_dir"])
    lines.append("# cmake_flags=" + pin["cmake_flags"])
    lines.append("# compiler=" + pin["compiler"])
    lines.append("# googletest=" + pin["googletest"]["version"])
    lines.append("# status values: pass, fail, not_run")
    lines.append("")
    lines.append("# CTest inventory: {n} tests; {p} passed; {f} failed; {nr} not run.".format(
        n=len(results), p=counts["pass"], f=counts["fail"], nr=counts["not_run"]))
    lines.append("# gtest case total across the suite (from the captured gtest output): "
                 "{c} cases in {s} suites.".format(c=gtest_running, s=gtest_suites))
    lines.append("test_name\tstatus")
    for name, status in results:
        lines.append(name + "\t" + status)
    pathlib.Path(args.out).write_text("\n".join(lines) + "\n")
    print("wrote {0}: {1} tests, pass={2} fail={3} not_run={4}; gtest cases={5} in {6} suites".format(
        args.out, len(results), counts["pass"], counts["fail"], counts["not_run"],
        gtest_running, gtest_suites))


if __name__ == "__main__":
    main()

