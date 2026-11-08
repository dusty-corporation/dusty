"""GPU identity signatures are local, process-free and non-identifying hashes."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from dusty.platform import gpu_signature

ROOT = Path(__file__).resolve().parents[2]
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="Reads macOS sysctl values")


@mac_only
def test_mac_signature_is_a_stable_sha256():
    first = gpu_signature.display_driver_signature()
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert gpu_signature.display_driver_signature() == first


@mac_only
def test_mac_sysctl_values_are_read_without_shell_tools():
    model, brand, build = (gpu_signature._sysctl_string(key) for key in gpu_signature._MAC_KEYS)
    assert model and brand and build
    assert gpu_signature._sysctl_string(b"dusty.not.a.sysctl") == ""


@mac_only
def test_mac_signature_import_and_call_start_no_process_and_skip_winreg():
    source = """
import sys
def reject(event, args):
    if event in {"subprocess.Popen", "os.posix_spawn", "os.fork", "os.exec", "os.system"}:
        raise AssertionError("process started: " + event)
sys.addaudithook(reject)
from dusty.platform.gpu_signature import display_driver_signature
assert len(display_driver_signature()) == 64
assert "winreg" not in sys.modules
assert "subprocess" not in sys.modules
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", source], cwd=ROOT, env=environment, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_mac_signature_changes_with_hardware_or_os(monkeypatch):
    values = {
        b"hw.model": "Mac14,2",
        b"machdep.cpu.brand_string": "Apple M2",
        b"kern.osversion": "",
    }
    monkeypatch.setattr(gpu_signature, "_sysctl_string", lambda key: values[key])
    monkeypatch.setattr(gpu_signature._platform, "mac_ver", lambda: ("26.2", ("", "", ""), ""))
    first = gpu_signature.display_driver_signature("darwin")
    monkeypatch.setattr(gpu_signature._platform, "mac_ver", lambda: ("26.3", ("", "", ""), ""))
    second = gpu_signature.display_driver_signature("darwin")
    values[b"hw.model"] = "Mac15,3"
    third = gpu_signature.display_driver_signature("darwin")
    assert len({first, second, third}) == 3
    assert "Apple" not in first and "Mac14" not in first


def test_mac_signature_without_any_identity_is_unavailable(monkeypatch):
    def fail(_key):
        raise OSError("no libSystem")

    monkeypatch.setattr(gpu_signature, "_sysctl_string", fail)
    monkeypatch.setattr(gpu_signature._platform, "mac_ver", lambda: ("", ("", "", ""), ""))
    assert gpu_signature.display_driver_signature("darwin") == "unavailable"


def test_unknown_platform_signature_is_unavailable():
    assert gpu_signature.display_driver_signature("linux") == "unavailable"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows reads the real registry")
def test_windows_registry_path_refuses_off_windows():
    with pytest.raises(OSError):
        gpu_signature.display_driver_signature("win32")
