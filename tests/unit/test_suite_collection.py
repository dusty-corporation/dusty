"""The whole test suite must collect on every supported platform.

A test module that imports a POSIX-only module such as fcntl at the top fails
to import on Windows before its own platform gate can skip it. That stops the
full Windows run at collection, so no test runs at all.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_test_module_collects_on_this_platform(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={tmp_path / 'collect'}",
            "tests",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    errors = [line for line in result.stdout.splitlines() if line.startswith("ERROR ")]
    assert result.returncode == 0, errors or result.stdout[-2000:]
