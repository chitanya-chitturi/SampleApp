#!/usr/bin/env python3
"""Overlays a broken variant from scenarios/<name>/ onto the real source tree.

Used only by the self-healing CI demo (workflow_dispatch) to reproduce a
failure category on a throwaway demo branch. Never run against main.
"""
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# scenario name -> list of (source under scenarios/<name>/, destination in repo)
SCENARIOS = {
    "deterministic-bug": [
        (
            "CalculatorController.java",
            "src/main/java/com/example/sampleapp/CalculatorController.java",
        ),
    ],
    "flaky-test": [
        (
            "FlakyExampleTest.java",
            "src/test/java/com/example/sampleapp/FlakyExampleTest.java",
        ),
    ],
    "dependency-mismatch": [
        ("pom.xml", "pom.xml"),
    ],
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        valid = ", ".join(SCENARIOS)
        print(f"Usage: inject_scenario.py <{valid}>", file=sys.stderr)
        sys.exit(1)

    scenario = sys.argv[1]
    for src_name, dest_rel in SCENARIOS[scenario]:
        src = REPO_ROOT / "scenarios" / scenario / src_name
        dest = REPO_ROOT / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        print(f"Injected {scenario}: {src_name} -> {dest_rel}")


if __name__ == "__main__":
    main()
