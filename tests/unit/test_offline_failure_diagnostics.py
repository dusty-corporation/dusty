"""A failing offline child must be identifiable without disclosing its data."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "tools/offline_failure_diagnostics.ps1"


def invoke(child: str, *, allowed: str = "@(0)") -> subprocess.CompletedProcess[str]:
    # The helper runs without WFP or administrator rights; the real audit still
    # exercises it on the disposable Windows CI runner.
    script = (
        f"$repo = '{ROOT}'; $pythonPath = '{sys.executable}'; "
        f". '{HELPER}'; "
        "try { "
        f"$result = Invoke-TestPython -Executable $pythonPath -Arguments @('-c', '{child}') "
        f"-AllowedExitCodes {allowed}; Write-Output ('result=' + $result); "
        "} catch { Write-Output $_.Exception.Message }"
    )
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )


def test_failing_child_reports_name_and_redacted_stream_tails() -> None:
    child = (
        'import sys; print("private lecture transcript"); '
        'print("FIXTURE_STATUS=FAILED"); '
        'print("RuntimeError: C:/Users/Secret/private.m4a",file=sys.stderr); '
        "sys.exit(37)"
    )
    result = invoke(child)
    assert result.returncode == 0, result.stderr
    assert "process=python.exe" in result.stdout
    assert "exit_code=37" in result.stdout
    assert "stdout_tail=" in result.stdout and "FIXTURE_STATUS=FAILED" in result.stdout
    assert "stderr_tail=" in result.stdout and "RuntimeError" in result.stdout
    assert "[redacted]" in result.stdout
    assert "private lecture" not in result.stdout
    assert "Secret" not in result.stdout
    assert "C:/Users" not in result.stdout
    assert "private.m4a" not in result.stdout


def test_allowed_exit_codes_and_success_stdout_are_preserved() -> None:
    result = invoke('print("OK"); raise SystemExit(1)', allowed="@(0,1)")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "result=OK"
