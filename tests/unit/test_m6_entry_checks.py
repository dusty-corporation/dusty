"""Real locked-partial outcomes and refusal of CI-only app entry points."""

import subprocess
import sys
from pathlib import Path

from dusty.installer_support import cancel_partial
from dusty.models import load_manifest
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]


def test_locked_cancel_partial_reports_retention_then_removes_after_release(tmp_path):
    models = tmp_path / "user/models"
    models.mkdir(parents=True)
    manifest = load_manifest(ROOT / "resources/models.json")
    part = models / (manifest.models["tiny"].file_name + ".part")
    part.write_bytes(b"public synthetic download prefix")
    paths = RuntimePaths(tmp_path / "bin", models, ROOT / "resources", models.parent)
    child = subprocess.Popen(
        [
            sys._base_executable,
            "-u",
            "-c",
            """
import ctypes,sys
from ctypes import wintypes as W
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
k.CreateFileW.restype=W.HANDLE
h=k.CreateFileW(sys.argv[1],0x80000000,0,None,3,0,None)
assert h!=ctypes.c_void_p(-1).value
print('ready',flush=True)
sys.stdin.read()
""",
            str(part),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "ready"
        assert cancel_partial(paths, "tiny") is False
        assert part.exists()
    finally:
        child.kill()
        child.wait(timeout=10)
        child.stdin.close()
        child.stdout.close()
    assert part.read_bytes() == b"public synthetic download prefix"
    assert cancel_partial(paths, "tiny") is True
    assert not part.exists()


def test_packaged_hardening_entry_refuses_normal_use(tmp_path, monkeypatch):
    from dusty.app.hardening_check import run

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert run(tmp_path / "unused") == 2
    assert not (tmp_path / "unused").exists()
