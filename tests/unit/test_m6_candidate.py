"""Candidate validation rejects changed bytes before staging either package."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from io import BytesIO

import pytest

from tools.prepare_m6_candidate import ROOT, prepare


@pytest.mark.parametrize("damage", [None, "cpu", "vulkan", "unexpected"])
@pytest.mark.parametrize("release_tag", ["engine-v2", "engine-v3"])
def test_candidate_checks_every_package_before_staging(tmp_path, damage, release_tag):
    native = tmp_path / "native"
    native.mkdir()
    shutil.copyfile(ROOT / "native/versions.toml", native / "versions.toml")
    pins_file = native / "versions.toml"
    pins = pins_file.read_text(encoding="utf-8")
    original = tomllib.loads(pins)
    pins_file.write_text(
        pins.replace(f'tag = "{original["engine_release"]["tag"]}"', f'tag = "{release_tag}"'),
        encoding="utf-8",
    )
    manifest = native / "windows-utf8.manifest"
    manifest.write_bytes(b"fixture manifest")
    spec = {
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "run_id": 1,
        "source_commit": "a" * 40,
        "backends": {},
    }
    source = tmp_path / "inputs"
    for backend in ("cpu", "vulkan"):
        folder = source / backend
        folder.mkdir(parents=True)
        content = (backend + " fixture").encode()
        (folder / "whisper-cli.exe").write_bytes(content)
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            item = zipfile.ZipInfo("whisper-cli.exe")
            item.external_attr = 0o600 << 16
            item.create_system = 3
            archive.writestr(item, content)
        spec["backends"][backend] = {
            "members": {"whisper-cli.exe": hashlib.sha256(content).hexdigest()},
            "archive_sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
            "archive_bytes": len(buffer.getvalue()),
        }
    (native / "m6-engine-candidate.json").write_text(json.dumps(spec), encoding="utf-8")
    before = (native / "versions.toml").read_bytes()
    if damage in {"cpu", "vulkan"}:
        (source / damage / "whisper-cli.exe").write_bytes(b"tampered")
    elif damage:
        (source / "vulkan/unexpected.exe").write_bytes(b"unknown")
    if damage:
        with pytest.raises(ValueError):
            prepare(source, tmp_path)
        assert (native / "versions.toml").read_bytes() == before
        assert not (tmp_path / "build").exists()
    else:
        prepare(source, tmp_path)
        assert (tmp_path / "build/bin/cpu/whisper-cli.exe").read_bytes() == b"cpu fixture"
        assert "m6-validation-only" in (native / "versions.toml").read_text(encoding="utf-8")
        staged = tomllib.loads(pins_file.read_text(encoding="utf-8"))
        assert staged["engine_release"]["tag"] == "m6-validation-only"
        assert staged["whisper_cpp"] == original["whisper_cpp"]
        assert staged["models_release"] == original["models_release"]


def test_candidate_cli_refuses_non_ci_execution():
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    result = subprocess.run(
        [sys.executable, "-m", "tools.prepare_m6_candidate", "unused"],
        env=env,
        capture_output=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert b"restricted" in result.stderr
