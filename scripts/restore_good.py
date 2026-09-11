#!/usr/bin/env python3
"""Restores the known-good version of whatever file(s) a scenario broke, by
checking them out from origin/main. Run on the demo branch, after `git fetch
origin main`, before committing the auto-remediation fix.

Usage: restore_good.py <scenario>
"""
import subprocess
import sys

from inject_scenario import SCENARIOS


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        valid = ", ".join(SCENARIOS)
        print(f"Usage: restore_good.py <{valid}>", file=sys.stderr)
        sys.exit(1)

    scenario = sys.argv[1]
    for _, dest_rel in SCENARIOS[scenario]:
        subprocess.run(["git", "checkout", "origin/main", "--", dest_rel], check=True)
        print(f"Restored {dest_rel} from origin/main")


if __name__ == "__main__":
    main()
