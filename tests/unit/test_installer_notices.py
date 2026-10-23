"""Notice generation preserves every approved component and exact MPL source."""

import hashlib
import io
import json
import zipfile

import pytest

from tools import installer_notices


def test_source_archive_retains_exact_bytes_and_rejects_modification(tmp_path, monkeypatch):
    licenses = tmp_path / "licenses"
    licenses.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    original = b"{ Original source and notices }\r\nunit NewUxTheme;\r\n"
    (source / "NewUxTheme.pas").write_bytes(original)
    (licenses / "runtime-source.json").write_text(
        json.dumps(
            {
                "reviewed_files": [],
                "jedi_sources": [
                    {"path": "NewUxTheme.pas", "sha256": hashlib.sha256(original).hexdigest()}
                ],
            }
        )
    )
    (licenses / "jedi-uxtheme.txt").write_bytes(b"Full retained license\n")
    monkeypatch.setattr(installer_notices, "LICENSES", licenses)
    packed = installer_notices.source_archive(source)
    assert packed == installer_notices.source_archive(source)
    with zipfile.ZipFile(io.BytesIO(packed)) as archive:
        assert archive.read("NewUxTheme.pas") == original
        assert archive.read("LICENSE-and-notices.txt") == b"Full retained license\n"
    (source / "NewUxTheme.pas").write_bytes(b"changed")
    with pytest.raises(ValueError, match="differs"):
        installer_notices.source_archive(source)


def test_runtime_notices_cover_exact_approved_components(tmp_path):
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text("App notices\n")
    text = installer_notices.runtime_notices(tmp_path)
    rows = json.loads((installer_notices.LICENSES / "components.json").read_text())
    for row in rows:
        assert row["name"] in text
        assert row["source"] in text
        assert (installer_notices.LICENSES / row["notice"]).read_text(encoding="utf-8") in text
    assert "Made using RemObjects Pascal Script" in text
    assert "installer-jedi-source.zip" in text
