"""Real pinned native acceptance belongs in the full asset-backed suite."""

import hashlib
import json
import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

from tools import mingw_runtime as policy

ROOT = Path(__file__).resolve().parents[2]


def test_approved_binary_pins_match_exact_existing_archive():
    import tomllib

    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    archive = ROOT / "build/downloads/minimal-ffmpeg.zip"
    assert (
        hashlib.sha256(archive.read_bytes()).hexdigest()
        == pins["engine_release"]["minimal_ffmpeg_zip_sha256"]
    )
    with zipfile.ZipFile(archive) as source:
        for name, digest in policy.BINARY_SHA256.items():
            assert hashlib.sha256(source.read(Path(name).name)).hexdigest() == digest
    provenance = json.loads((ROOT / "packaging/licenses/sources.json").read_text())
    assert provenance["mingw-w64-runtime.txt"]["sha256"] == policy.NOTICE_SHA256


def test_selftest_entrypoint_starts_with_guard(tmp_path: Path) -> None:
    script = """
        import runpy
        import sys
        from dusty.privacy.network_guard import NetworkBlockedError, is_installed
        sys.argv = ["dusty", "--self-test", "--backend", "cpu", "--model", "tiny"]
        try:
            runpy.run_module("dusty", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
        assert is_installed()
        try:
            sys.audit("socket.connect", "CANARY_HOSTNAME_SECRET")
        except NetworkBlockedError:
            print("selftest guarded")
        else:
            raise AssertionError("Self-test did not install guard")
    """
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=ROOT,
        env={**os.environ, "LOCALAPPDATA": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "OK" in result.stdout
    assert "selftest guarded" in result.stdout
    assert "CANARY_HOSTNAME_SECRET" not in result.stderr
