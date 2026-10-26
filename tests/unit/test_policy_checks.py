"""Positive and negative samples for the M0 policy gates."""

from pathlib import Path

import pytest

from tools import check_licenses, check_no_huggingface, check_no_network


@pytest.mark.parametrize(
    "source",
    [
        "import ctypes; ctypes.WinDLL('ws2_32.dll')",
        "import ctypes as c; c.CDLL('C:/Windows/System32/WINHTTP.DLL')",
        "from subprocess import run as r; r(['curl.exe'])",
        "import subprocess as s; s.Popen(['curl.exe'])",
        "from importlib import import_module as load; load('soc' + 'ket')",
        "import os; os.startfile('https://example.invalid')",
        "import webbrowser; webbrowser.open('https://example.invalid')",
    ],
)
def test_static_guard_rejects_dynamic_network_and_launch_bypasses(source):
    assert check_no_network.scan_source(source, "bad.py")


def test_network_checker_accepts_offline_import(tmp_path: Path) -> None:
    app = tmp_path / "src" / "dusty"
    app.mkdir(parents=True)
    (app / "sample.py").write_text("import pathlib\n", encoding="utf-8")
    assert check_no_network.check(tmp_path) == []


def test_network_checker_rejects_bad_import(tmp_path: Path) -> None:
    app = tmp_path / "src" / "dusty"
    app.mkdir(parents=True)
    (app / "bad.py").write_text("from PySide6 import QtNetwork\n", encoding="utf-8")
    assert "forbidden networking import" in check_no_network.check(tmp_path)[0]


def test_network_checker_rejects_dynamic_import() -> None:
    findings = check_no_network.scan_source("__import__('socket')", "bad.py")
    assert len(findings) == 1


def test_model_host_checker_accepts_clean_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "clean.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert check_no_huggingface.check(tmp_path) == []


def test_model_host_checker_rejects_bad_source(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "bad.py").write_text("HOST = '" + "hugging" + "face.co'\n", encoding="utf-8")
    assert len(check_no_huggingface.check(tmp_path)) == 1


def test_model_host_checker_scans_required_inputs_and_exempts_spec_adrs(tmp_path: Path) -> None:
    token = "hugging" + "face"
    paths = [
        tmp_path / "src" / "bad.py",
        tmp_path / "tests" / "bad.py",
        tmp_path / "uv.lock",
        tmp_path / ".github" / "workflows" / "ci.yml",
        tmp_path / "native" / "bad.sh",
        tmp_path / "modelpipeline" / "bad.py",
        tmp_path / "packaging" / "bad.spec",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")
    for path in (tmp_path / "docs" / "pm" / "SPEC.md", tmp_path / "docs" / "adr" / "0001.md"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")
    assert len(check_no_huggingface.check(tmp_path)) == len(paths)


def test_license_checker_accepts_allowed_alternative() -> None:
    assert check_licenses.allowed_license(
        "PySide6", "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
    )


def test_license_checker_rejects_bad_license(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "dusty"\nversion = "0.0.1"\n'
        'dependencies = [{ name = "bad-library" }]\n'
        '[[package]]\nname = "bad-library"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )

    class BadDistribution:
        version = "1.0.0"
        metadata = {"License": "GPL-3.0-only"}

    monkeypatch.setattr(
        check_licenses.importlib.metadata, "distribution", lambda _: BadDistribution()
    )
    assert "unapproved" in check_licenses.check(tmp_path)[0]


def test_license_checker_rejects_unknown_license() -> None:
    assert not check_licenses.allowed_license("bad-library", "UNKNOWN")


def test_pyinstaller_bootloader_exception_is_exact() -> None:
    expression = check_licenses.PYINSTALLER_BOOTLOADER
    assert check_licenses.allowed_license("pyinstaller-bootloader", expression)
    assert not check_licenses.allowed_license("another-bootloader", expression)
    assert not check_licenses.allowed_license("pyinstaller-bootloader", "GPL-2.0-or-later")


def test_license_checker_checks_locked_runtime_tree() -> None:
    lock = {
        "package": [
            {"name": "dusty", "version": "0.0.1", "dependencies": [{"name": "bad-library"}]},
            {"name": "bad-library", "version": "1.0.0"},
        ]
    }
    assert check_licenses.runtime_packages(lock) == {"dusty": "0.0.1", "bad-library": "1.0.0"}


@pytest.mark.parametrize("api", ["LoadLibraryW", "LoadLibraryExW", "GetModuleHandleW"])
@pytest.mark.parametrize("dll", ["ws2_32.dll", "MSWSOCK", "C:/Windows/System32/IPHLPAPI.DLL"])
def test_static_network_dll_win32_loader_and_handle_routes(api, dll):
    assert check_no_network.scan_source(
        f"import ctypes; ctypes.windll.kernel32.{api}({dll!r})", "bad.py"
    )
