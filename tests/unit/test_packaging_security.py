"""Exact platform and redistribution contracts, including negative evidence."""

import hashlib
import json
import shutil
import sys
import tomllib
from pathlib import Path

import pytest

from tools import check_licenses, check_pe_imports

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mutation", ["none", "hash", "functions", "dns", "other-pe", "missing"])
def test_platform_pin_contract(tmp_path: Path, monkeypatch, mutation: str) -> None:
    content = b"MZ-platform-test"
    target = tmp_path / "python312.dll"
    target.write_bytes(content)
    functions = ["WSAGetLastError", "getsockopt", "send"]
    libraries = {"ws2_32.dll": functions}
    pins = {
        "python312.dll": {"sha256": hashlib.sha256(content).hexdigest(), "ws2_32": functions.copy()}
    }
    if mutation == "hash":
        target.write_bytes(content + b"changed")
    elif mutation == "functions":
        libraries["ws2_32.dll"] = functions + ["connect"]
    elif mutation == "dns":
        libraries["dnsapi.dll"] = ["DnsQuery_W"]
    elif mutation == "other-pe":
        (tmp_path / "renamed.data").write_bytes(content)
    elif mutation == "missing":
        target.unlink()
    monkeypatch.setattr(check_pe_imports, "imports", lambda _: libraries)
    findings, checked = check_pe_imports.check(tmp_path, pins)
    assert bool(findings) == (mutation != "none")
    if mutation == "other-pe":
        assert len(checked) == 2  # PE signature, not an extension allowlist.


@pytest.fixture
def crt_evidence(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    redist = tmp_path / "VisualStudio/VC/redist"
    source = redist / "MSVC/14.44.35211/x64/Microsoft.VC143.CRT/vcruntime140.dll"
    source.parent.mkdir(parents=True)
    shutil.copyfile(Path(sys.base_prefix) / "vcruntime140.dll", source)
    target = bundle / "vcruntime140.dll"
    shutil.copyfile(source, target)
    shutil.copytree(ROOT / "packaging/licenses/microsoft", bundle / "licenses/microsoft")
    eula = (bundle / "licenses/microsoft/runtime-eula.txt").read_text(encoding="utf-8")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text(eula, encoding="utf-8")
    record = {
        "path": target.name,
        "source": str(source),
        "redist": str(redist),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "basis": "VS2022-Community-section-4/Visual-C++-Runtime-Files",
    }
    return bundle, {"microsoft_runtime": [record]}


@pytest.mark.parametrize("mutation", ["none", "bytes", "receipt", "debug", "pdf", "terms"])
def test_microsoft_exception_requires_evidence(crt_evidence, mutation: str) -> None:
    bundle, inventory = crt_evidence
    record = inventory["microsoft_runtime"][0]
    if mutation == "bytes":
        record["sha256"] = "0" * 64
    elif mutation == "receipt":
        inventory["microsoft_runtime"] = []
    elif mutation == "debug":
        original = Path(record["source"])
        debug = original.parent / "debug_nonredist" / original.name
        debug.parent.mkdir()
        shutil.copyfile(original, debug)
        record["source"] = str(debug)
    elif mutation == "pdf":
        (bundle / "licenses/microsoft/community-2022.pdf").write_bytes(b"changed")
    elif mutation == "terms":
        (bundle / "THIRD_PARTY_NOTICES.md").write_text("terms omitted", encoding="utf-8")
    actual = {
        path.relative_to(bundle).as_posix(): path for path in bundle.rglob("*") if path.is_file()
    }
    findings = check_licenses.check_microsoft(bundle, inventory, actual)
    assert bool(findings) == (mutation != "none")
    assert not check_licenses.allowed_license("unrelated", check_licenses.MSVC_LICENSE)


def test_runtime_license_and_test_only_docx() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["license"] == "Apache-2.0"
    assert check_licenses.allowed_license("dusty", project["project"]["license"])
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert {"python-docx", "lxml"}.isdisjoint(check_licenses.runtime_packages(lock))
    pins = json.loads(check_pe_imports.PINS.read_text(encoding="utf-8"))
    assert set(pins) == {"python312.dll", "qt6core.dll"}
