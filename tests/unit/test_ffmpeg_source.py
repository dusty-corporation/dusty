"""Source closure and retained runtime notices cannot be silently omitted."""

import hashlib
import json
from pathlib import Path

import pytest

from tools import ffmpeg_source
from tools.check_licenses import allowed_license
from tools.inventory_bundle import clean_buildconf

ROOT = Path(__file__).resolve().parents[2]


def test_retained_runtime_notice_hashes_and_exact_license_boundary():
    provenance = json.loads((ROOT / "packaging/licenses/sources.json").read_text())
    for name in ("mingw-w64-runtime.txt", "winpthreads-COPYING.txt"):
        content = (ROOT / "packaging/licenses" / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == provenance[name]["sha256"]
    assert allowed_license("winpthreads", "MIT AND BSD-3-Clause")
    assert not allowed_license("winpthreads", "MIT AND UNKNOWN")
    assert not allowed_license("mingw-w64-runtime", "LicenseRef-MinGW-w64-runtime")


def test_corresponding_source_and_script_hash_fail_closed(tmp_path, monkeypatch):
    content = b"synthetic source archive"
    monkeypatch.setitem(ffmpeg_source.PIN, "sha256", hashlib.sha256(content).hexdigest())
    archive = tmp_path / ffmpeg_source.PIN["name"]
    script = tmp_path / "build_ffmpeg.sh"
    archive.write_bytes(content)
    script.write_bytes((ROOT / "native/build_ffmpeg.sh").read_bytes())
    ffmpeg_source.verify(tmp_path)
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="source hash"):
        ffmpeg_source.verify(tmp_path)
    archive.write_bytes(content)
    script.write_bytes(b"changed")
    with pytest.raises(ValueError, match="build script"):
        ffmpeg_source.verify(tmp_path)


def test_notices_drop_wine_bootstrap_preamble_only():
    banner = "ffmpeg version n9.0.2\n  configuration: --disable-network\n"
    assert clean_buildconf("wine: initialization noise\n" + banner) == banner.strip()
    with pytest.raises(ValueError, match="banner missing"):
        clean_buildconf("wine: initialization noise")
