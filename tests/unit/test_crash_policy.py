"""C2: only disposable CI may deliberately crash against real WER stores."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from dusty.platform.win_process import run_job_process


def test_entrypoints_request_error_mode_before_main():
    for module in ("dusty", "dusty_fetch"):
        script = f"""
import ctypes, runpy, sys
sys.argv = ['{module}', '--version']
try:
    runpy.run_module('{module}', run_name='__main__')
except SystemExit:
    pass
assert ctypes.windll.kernel32.GetErrorMode() & 2
print('error mode set')
"""
        child = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=10
        )
        assert child.returncode == 0, child.stderr
        assert "error mode set" in child.stdout


def test_store_roots_were_captured_before_test_appdata_redirect(real_wer_roots):
    assert len(real_wer_roots) == 2
    assert real_wer_roots[0] != Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/WER"


@pytest.mark.skipif(
    os.environ.get("DUSTY_WER_ACCEPTANCE") != "1",
    reason="Deliberate crash/store inspection runs only in installed disposable CI acceptance",
)
def test_installed_exclusions_cover_abort_and_seh_in_real_stores(
    real_wer_roots, tmp_path, monkeypatch
):
    import winreg

    from tools.wer_observer import EXCLUDED_NAMES, EXCLUSION_KEY, require_disposable_ci, snapshot

    require_disposable_ci(os.environ)
    # Precondition must fail before any deliberate crash if Setup did not register.
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, EXCLUSION_KEY) as key:
        for name in EXCLUDED_NAMES:
            assert winreg.QueryValueEx(key, name)[1] == winreg.REG_DWORD
    assert real_wer_roots[0] != Path(os.environ["LOCALAPPDATA"]) / "Microsoft/Windows/WER"
    # The native children get the real profile too, removing any ambiguity about
    # whether a WER implementation consults environment or Windows known folders.
    monkeypatch.setenv("LOCALAPPDATA", str(real_wer_roots[0].parents[2]))
    monkeypatch.setenv("PROGRAMDATA", str(real_wer_roots[1].parents[2]))
    before, states = snapshot(real_wer_roots)
    fixture = tmp_path / "fixture-bin"
    fixture.mkdir()
    source = fixture / "crash.c"
    source.write_text(
        "#include <windows.h>\n#include <stdlib.h>\n#include <stdint.h>\n"
        "#include <string.h>\n"
        "int main(int argc, char **argv) {\n"
        " if (!(GetErrorMode() & SEM_NOGPFAULTERRORBOX)) return 9;\n"
        ' if (argc > 1 && strcmp(argv[1], "abort") == 0) abort();\n'
        " CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)(uintptr_t)1, NULL, 0, NULL);\n"
        " Sleep(5000); return 8;\n}\n",
        encoding="ascii",
    )
    vswhere = (
        Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    )
    found = subprocess.run(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    devcmd = Path(found.stdout.strip()) / "Common7/Tools/VsDevCmd.bat"
    assert devcmd.is_file()
    build = fixture / "compile.cmd"
    build.write_text(
        '@echo off\ncall "' + str(devcmd) + '" -arch=x64 -host_arch=x64 >nul\n'
        "if errorlevel 1 exit /b 1\n"
        "cl /nologo /O2 /MD crash.c /Fe:whisper-cli.exe\n",
        encoding="utf-8",
    )
    compiled = subprocess.run(
        ["cmd.exe", "/d", "/c", str(build)], cwd=fixture, capture_output=True, text=True, timeout=90
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    binary = fixture / "whisper-cli.exe"
    assert binary.is_file()
    monkeypatch.setenv("DUSTY_BIN_DIR", str(fixture))
    observed = []
    started = time.monotonic()
    for name in EXCLUDED_NAMES:
        executable = fixture / name
        if executable != binary:
            shutil.copyfile(binary, executable)
        for mode in ("abort", "seh"):
            result = run_job_process([str(executable), mode], timeout_sec=15)
            assert not result.cancelled
            expected = {3, 0xC0000409, 0x40000015} if mode == "abort" else {0xC0000005}
            assert result.exit_code in expected, (name, mode, result.exit_code)
            observed.append({"name": name, "mode": mode, "exit_code": result.exit_code})
            after, states = snapshot(real_wer_roots)
            assert after == before, "Real WER store changed after a deliberate crash"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        after, states = snapshot(real_wer_roots)
        assert after == before, "Real WER store changed during delayed observation"
        time.sleep(0.1)
    receipt = (
        Path(__file__).resolve().parents[2] / "build/installer/acceptance/wer-real-stores.json"
    )
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(
            {
                "roots": [str(root) for root in real_wer_roots],
                "states": states,
                "cases": observed,
                "new_reports_observed": 0,
                "observation_seconds": time.monotonic() - started,
                "unproven_paths": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Real WER stores: 10 crash cases; zero new reports observed across all six areas")
