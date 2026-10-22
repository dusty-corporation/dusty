"""Measure M2 package line coverage with the Python standard library."""

import json
import subprocess
import sys
import trace
from pathlib import Path
from types import CodeType

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("core", "export", "models", "queue", "privacy")


def executable_lines(code: CodeType) -> set[int]:
    lines = {line for _, _, line in code.co_lines() if line is not None and line > 0}
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            lines.update(executable_lines(constant))
    return lines


def main() -> int:
    tracer = trace.Trace(count=True, trace=False)
    result = tracer.runfunc(pytest.main, ["-q"])
    counts = tracer.results().counts
    child = subprocess.run(
        [sys.executable, str(ROOT / "tools/trace_network_guard.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    guard = ROOT / "src/dusty/privacy/network_guard.py"
    for line in json.loads(child.stdout):
        counts[(str(guard), line)] = 1
    hit_total = 0
    executable_total = 0
    below_target = False
    for package in PACKAGES:
        hit = 0
        executable = 0
        for source in (ROOT / "src/dusty" / package).rglob("*.py"):
            code = compile(source.read_text(encoding="utf-8"), str(source), "exec")
            lines = executable_lines(code)
            source_path = str(source.resolve())
            hit += sum((source_path, line) in counts for line in lines)
            executable += len(lines)
        hit_total += hit
        executable_total += executable
        print(f"{package}: {hit}/{executable} = {hit / executable:.1%}")
        below_target |= hit / executable < 0.85
    print(f"total: {hit_total}/{executable_total} = {hit_total / executable_total:.1%}")
    return int(result) or int(below_target)


if __name__ == "__main__":
    sys.exit(main())
