"""Regression checks for packaging exclusions and the actual-content license gate."""

import hashlib
import json
import struct
from pathlib import Path

import pytest

from tools import check_bundle, check_licenses


@pytest.mark.parametrize("name", ["Qt6Network.dll", "qt6network.DLL", "Qt6WebEngineCore.dll"])
def test_bundle_rejects_nested_forbidden_dll(tmp_path: Path, name: str) -> None:
    plugin = tmp_path / "_internal/PySide6/plugins"
    plugin.mkdir(parents=True)
    (plugin / name).write_bytes(b"prohibited")
    assert any("Prohibited Qt DLL" in item for item in check_bundle.check(tmp_path))


def test_bundle_checks_windowed_and_console_subsystems(tmp_path: Path) -> None:
    def executable(subsystem: int) -> bytes:
        data = bytearray(256)
        struct.pack_into("<I", data, 0x3C, 64)
        data[64:68] = b"PE\x00\x00"
        struct.pack_into("<H", data, 64 + 24 + 68, subsystem)
        return data

    (tmp_path / "dusty.exe").write_bytes(executable(3))
    (tmp_path / "dusty-fetch.exe").write_bytes(executable(2))
    findings = check_bundle.check(tmp_path)
    assert sum("Incorrect windowed/console" in item for item in findings) == 2


@pytest.fixture
def inventory(tmp_path: Path) -> tuple[Path, Path, dict]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "sample.dll").write_bytes(b"sample")
    data = {
        "components": {"sample": {"name": "sample", "license": "MIT"}},
        "files": [
            {
                "path": "sample.dll",
                "sha256": hashlib.sha256(b"sample").hexdigest(),
                "components": ["sample"],
            }
        ],
    }
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return bundle, path, data


def test_bundle_license_gate_accepts_verified_allowed_file(inventory) -> None:
    bundle, path, _ = inventory
    assert check_licenses.check_bundle(bundle, path) == []


@pytest.mark.parametrize("mutation", ["extra", "missing", "hash", "unmapped", "unknown", "static"])
def test_bundle_license_gate_fails_closed(inventory, mutation: str) -> None:
    bundle, path, data = inventory
    if mutation == "extra":
        (bundle / "extra.dll").write_bytes(b"unreviewed")
    elif mutation == "missing":
        (bundle / "sample.dll").unlink()
    elif mutation == "hash":
        (bundle / "sample.dll").write_bytes(b"changed")
    elif mutation == "unmapped":
        data["files"][0]["components"] = ["unreviewed"]
    elif mutation == "unknown":
        data["components"]["sample"]["license"] = "UNKNOWN"
    else:
        data["components"]["sample"].update(
            name="pyside6", license="LGPL-3.0-only", linkage="static"
        )
    path.write_text(json.dumps(data), encoding="utf-8")
    assert check_licenses.check_bundle(bundle, path)
