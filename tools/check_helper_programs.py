"""Smoke test the built add-on helper programs; exit nonzero on any finding.

    python -m tools.check_helper_programs --mac-app build/mac-app/Dusty.app
    python -m tools.check_helper_programs --windows-bundle dist/Dusty

Each program in packaging/addons/programs.json (tools/helper_programs.py) is
run through its own check module. On Windows its folder also gets the offline
PE import check. Public Dusty has no helper programs, so this passes at once.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from tools.helper_programs import ROOT, load_programs


def run(*args: str) -> int:
    return subprocess.run([sys.executable, *args], cwd=ROOT, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--mac-app", type=Path)
    where.add_argument("--windows-bundle", type=Path)
    args = parser.parse_args(argv)
    programs = load_programs()
    if not programs:
        print("No helper programs to check")
        return 0
    failed = 0
    for program in programs:
        if args.mac_app is not None:
            failed |= run("-m", program.check, str(args.mac_app / program.mac_executable))
            continue
        bundle = args.windows_bundle
        failed |= run(
            "tools/check_pe_imports.py",
            str(bundle / program.name),
            "--output",
            f"build/packaging/audit/offline-pe-{program.name}.json",
        )
        failed |= run("-m", program.check, str(bundle / program.windows_executable))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
