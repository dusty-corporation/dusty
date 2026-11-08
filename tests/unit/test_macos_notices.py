"""Generated macOS notices, their bundle coverage check and the Mac license gate (P33)."""

import decimal
import json
import plistlib
import pyexpat
import shutil
import sqlite3
import ssl
import sys
from pathlib import Path

import pytest
from test_macos_packaging import macho

from tools import check_licenses
from tools import check_macos_bundle as check
from tools import macos_notices as notices

ROOT = Path(__file__).resolve().parents[2]
BIN = "Contents/Helpers/bin"
FRAMEWORKS = "Contents/Frameworks"
# Mac-only gate: the reason names the macOS dependency that Windows lacks.
mac_libpython = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="needs the macOS build of Python; its libmpdec matches the retained text",
)


def libpython_bytes(*, openssl: str | None = None) -> bytes:
    """Markers and version strings of every library linked into libpython."""
    parts = [
        f"OpenSSL {openssl or ssl.OPENSSL_VERSION.split()[1]} 11 Feb 2025".encode(),
        b"ffi_prep_cif ffi_call",
        b"SQLite format 3 " + sqlite3.sqlite_version.encode(),
        b"BZ2_bzCompress 1.0.8, 13-Jul-2019",
        b"\xfd7zXZ lzma_code\x005.2.12\x00",
        b"libmpdec",
        b"XML_ParserCreate " + pyexpat.EXPAT_VERSION.encode(),
        b"Hacl_Hash",
    ]
    return macho() + b"\0".join(parts)


def analysis() -> dict:
    site = "/venv/lib/python3.12/site-packages"
    stdlib = f"{sys.base_prefix}/lib/python3.12/json/__init__.py"
    return {
        "gui_pure": [
            ["dusty.app", str(ROOT / "src/dusty/app/__init__.py"), "PYMODULE"],
            ["json", stdlib, "PYMODULE"],
            ["PySide6", f"{site}/PySide6/__init__.py", "PYMODULE"],
            ["shiboken6", f"{site}/shiboken6/__init__.py", "PYMODULE"],
            ["_pyi_rth_utils", f"{site}/PyInstaller/fake_modules/_pyi_rth_utils.py", "PYMODULE"],
        ],
        "gui_scripts": [
            ["pyiboot01_bootstrap", f"{site}/PyInstaller/loader/pyiboot01_bootstrap.py", "S"],
            ["runtime_guard", str(ROOT / "packaging/runtime_guard.py"), "PYSOURCE"],
        ],
        "fetch_pure": [["dusty_fetch", str(ROOT / "src/dusty_fetch/__init__.py"), "PYMODULE"]],
        "fetch_scripts": [["fetch_entry", str(ROOT / "packaging/fetch_entry.py"), "PYSOURCE"]],
    }


def fake_app(tmp_path: Path) -> tuple[Path, Path]:
    """A staged, unsigned Dusty.app with the real file layout in miniature."""
    app = tmp_path / "Dusty.app"
    audit = tmp_path / "audit"
    audit.mkdir()
    (audit / "analysis.json").write_text(json.dumps(analysis()), encoding="utf-8")
    images = {
        "Contents/MacOS/Dusty": macho(),
        "Contents/Helpers/dusty-fetch/dusty-fetch": macho(),
        "Contents/Helpers/dusty-fetch/_internal/libpython3.12.dylib": libpython_bytes(),
        f"{FRAMEWORKS}/libpython3.12.dylib": libpython_bytes(),
        f"{FRAMEWORKS}/PySide6/QtCore.abi3.so": macho(),
        f"{FRAMEWORKS}/PySide6/libpyside6.abi3.6.9.dylib": macho(),
        f"{FRAMEWORKS}/shiboken6/libshiboken6.abi3.6.9.dylib": macho(),
        f"{FRAMEWORKS}/PySide6/Qt/plugins/platforms/libqcocoa.dylib": macho(),
        f"{BIN}/ffmpeg/ffmpeg": macho(),
        f"{BIN}/ffmpeg/ffprobe": macho(),
        f"{BIN}/cpu/whisper-cli": macho(),
        f"{BIN}/cpu/libwhisper.1.dylib": macho(),
        f"{BIN}/cpu/libggml.0.dylib": macho(),
        f"{BIN}/metal/whisper-cli": macho(),
        f"{BIN}/metal/libggml-metal.0.dylib": macho(),
        f"{BIN}/lifeline/dusty-lifeline": macho(),
    }
    for module, marker in (("QtCore", b"PCRE2 Keccak"), ("QtGui", b"harfbuzz")):
        base = f"{FRAMEWORKS}/PySide6/Qt/lib/{module}.framework/Versions/A"
        images[f"{base}/{module}"] = macho() + marker
        info = app / base / "Resources/Info.plist"
        info.parent.mkdir(parents=True)
        info.write_bytes(plistlib.dumps({"CFBundleVersion": "6.9.2"}))
    for relative, data in images.items():
        path = app / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    resources = app / "Contents/Resources"
    resources.mkdir(exist_ok=True)
    for relative in ("selftest.wav", "models.json", "base_library.zip"):
        (resources / relative).write_bytes(b"data")
    shutil.copytree(ROOT / "resources/tls", resources / "tls")
    translations = resources / "PySide6/Qt/translations"
    translations.mkdir(parents=True)
    (translations / "qt_fi.qm").write_bytes(b"qm")
    licenses = resources / "licenses"
    licenses.mkdir()
    for name, source in (
        ("dusty-LICENSE.txt", ROOT / "LICENSE"),
        ("dusty-NOTICE.txt", ROOT / "NOTICE"),
        ("ffmpeg-LGPL-2.1.txt", ROOT / "packaging/licenses/ffmpeg-LGPL-2.1.txt"),
        ("qt-LGPL-3.0.txt", ROOT / "packaging/licenses/qt-LGPL-3.0.txt"),
        ("qt-GPL-3.0-reference.txt", ROOT / "packaging/licenses/qt-GPL-3.0-reference.txt"),
        ("libffi-MIT.txt", ROOT / "packaging/licenses/libffi-MIT.txt"),
        ("openssl-Apache-2.0.txt", ROOT / "packaging/licenses/openssl-Apache-2.0.txt"),
        ("public-ca-NOTICE.txt", ROOT / "resources/tls/NOTICE.txt"),
        ("public-ca-sources.json", ROOT / "resources/tls/sources.json"),
    ):
        shutil.copyfile(source, licenses / name)
    (licenses / "cpython-LICENSE.txt").write_text(
        "Copyright (c) 2001 Python Software Foundation;\nAll Rights Reserved", encoding="utf-8"
    )
    (licenses / "pyinstaller-COPYING.txt").write_text("PyInstaller COPYING", encoding="utf-8")
    (licenses / "whisper.cpp-LICENSE.txt").write_text(
        "MIT License\n\nCopyright (c) 2023-2026 The ggml authors\n", encoding="utf-8"
    )
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Dusty"}))
    notices.stage_texts(app)
    return app, audit


BANNER = "ffmpeg version 9.0.2 Copyright (c) 2000-2026 the FFmpeg developers"
BUILDCONF = "configuration:\n    --disable-network\n    --disable-everything"


def generated(tmp_path: Path) -> tuple[Path, str, dict]:
    app, audit = fake_app(tmp_path)
    text, inventory = notices.generate(
        app, bin_dir=BIN, version="1.0.0", banner=BANNER, buildconf=BUILDCONF, audit=audit
    )
    (app / "Contents/Resources" / notices.NOTICES).write_text(text, encoding="utf-8")
    return app, text, inventory


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (f"{BIN}/ffmpeg/ffprobe", ["ffmpeg"]),
        (f"{BIN}/cpu/whisper-cli", ["whisper.cpp"]),
        (f"{BIN}/metal/libwhisper.1.dylib", ["whisper.cpp"]),
        (f"{BIN}/metal/libggml-metal.0.dylib", ["ggml"]),
        (f"{BIN}/lifeline/dusty-lifeline", ["dusty"]),
        (f"{FRAMEWORKS}/libpython3.12.dylib", ["cpython", "cpython-static-libraries"]),
        (f"{FRAMEWORKS}/PySide6/Qt/lib/QtGui.framework/Versions/A/QtGui", ["qt"]),
        (f"{FRAMEWORKS}/PySide6/Qt/plugins/platforms/libqcocoa.dylib", ["qt"]),
        ("Contents/Resources/PySide6/Qt/translations/qt_fi.qm", ["qt"]),
        (f"{FRAMEWORKS}/PySide6/QtCore.abi3.so", ["pyside6"]),
        (f"{FRAMEWORKS}/shiboken6/Shiboken.abi3.so", ["shiboken6"]),
        ("Contents/Resources/selftest.wav", ["jfk-fixture"]),
        ("Contents/Resources/tls/isrg-x1.pem", ["public-ca-certificates"]),
        ("Contents/Resources/tls/sources.json", ["dusty"]),
        ("Contents/Resources/licenses/qt-LGPL-3.0.txt", ["dusty"]),
    ],
)
def test_every_known_location_has_its_component(relative, expected):
    assert notices.attribute(relative, BIN, analysis()) == expected


def test_executables_carry_their_embedded_module_providers():
    gui = notices.attribute("Contents/MacOS/Dusty", BIN, analysis())
    fetch = notices.attribute("Contents/Helpers/dusty-fetch/dusty-fetch", BIN, analysis())
    assert gui == ["cpython", "dusty", "pyinstaller-bootloader", "pyside6", "shiboken6"]
    assert fetch == ["dusty", "pyinstaller-bootloader"]


@pytest.mark.parametrize(
    "relative",
    [
        f"{BIN}/cpu/unknown-tool",
        f"{BIN}/ffmpeg/ffplay",
        f"{BIN}/metal/sub/whisper-cli",
        "Contents/Resources/mystery.bin",
        f"{FRAMEWORKS}/libcurl.dylib",
    ],
)
def test_unknown_files_fail_closed(relative):
    with pytest.raises(notices.NoticesError):
        notices.attribute(relative, BIN, analysis())


def test_modules_from_an_unknown_provider_fail_closed():
    with pytest.raises(notices.NoticesError):
        notices.module_owner("/venv/lib/python3.12/site-packages/requests/__init__.py")


@mac_libpython
def test_libpython_libraries_are_detected_with_verified_versions():
    found = {item["name"]: item for item in notices.static_libraries(libpython_bytes())}
    assert set(found) == {
        "OpenSSL",
        "libffi",
        "SQLite",
        "bzip2",
        "XZ Utils liblzma",
        "mpdecimal",
        "Expat",
        "HACL* (vendored in CPython)",
    }
    assert found["OpenSSL"]["version"] == ssl.OPENSSL_VERSION.split()[1]
    assert found["SQLite"]["version"] == sqlite3.sqlite_version
    assert found["mpdecimal"]["version"] == decimal.__libmpdec_version__
    assert found["bzip2"]["version"] == "1.0.8"
    assert found["OpenSSL"]["text"] == "openssl-Apache-2.0.txt"
    assert found["Expat"]["text"] == "macos/libpython/expat-2.6.3-COPYING.txt"
    assert found["XZ Utils liblzma"]["version"].startswith("5.2.12 ")
    assert found["libffi"]["version"].startswith("3.4.6 ")
    assert found["XZ Utils liblzma"]["license"] == "LicenseRef-Public-Domain"


def test_a_liblzma_without_the_pinned_version_string_is_refused():
    data = libpython_bytes().replace(b"\x005.2.12\x00", b"\x005.8.1\x00")
    with pytest.raises(notices.NoticesError, match="liblzma"):
        notices.static_libraries(data)


def test_retained_texts_must_match_the_detected_version(monkeypatch):
    monkeypatch.setattr(decimal, "__libmpdec_version__", "4.0.1")
    data = libpython_bytes()
    with pytest.raises(notices.NoticesError, match="mpdecimal"):
        notices.static_libraries(data)


def test_a_libpython_from_another_build_is_refused():
    with pytest.raises(notices.NoticesError, match="OpenSSL"):
        notices.static_libraries(libpython_bytes(openssl="9.9.9"))


def test_libraries_absent_from_libpython_are_not_claimed():
    assert notices.static_libraries(macho() + b"ffi_prep_cif ffi_call") == [
        {
            "name": "libffi",
            "version": "3.4.6 (python-build-standalone pin; not exposed in the binary)",
            "license": "MIT",
            "text": "macos/libpython/libffi-3.4.6-LICENSE.txt",
        }
    ]


@mac_libpython
def test_generated_notices_cover_the_bundle_and_pass_the_checker(tmp_path):
    app, text, inventory = generated(tmp_path)
    assert check.notices_findings(app, BIN, BUILDCONF) == []
    rows = check.notices_file_rows(text)
    assert rows[f"{BIN}/metal/libggml-metal.0.dylib"] == ["ggml"]
    assert "- QtCore 6.9.2" in text and "- plugin platforms/libqcocoa.dylib" in text
    assert notices.WINDOWS_SOURCE_SENTENCE in text
    assert BUILDCONF in text and BANNER in text
    assert "ffmpeg-n9.0.2-946fcce.tar.gz" in text
    assert "ggml-silero-vad.bin" in text and "snakers4/silero-vad" in text
    assert inventory["open_items"] == []
    assert "licenses/macos/libpython/expat-2.6.3-COPYING.txt" in text
    assert "| PCRE2 | 10.45 |" in text and "licenses/macos/qt/pcre2__LICENCE.md.txt" in text
    assert "wintab (Windows only)" in text
    assert "licenses/macos/models/silero-vad-LICENSE.txt" in text
    assert set(inventory["files"]) == {
        path.relative_to(app).as_posix()
        for path in app.rglob("*")
        if path.is_file() and path.name != notices.NOTICES
    }


@mac_libpython
def test_an_unattributed_bundle_file_stops_generation(tmp_path):
    app, audit = fake_app(tmp_path)
    (app / f"{BIN}/cpu/libcurl.4.dylib").write_bytes(macho())
    with pytest.raises(notices.NoticesError, match="libcurl"):
        notices.generate(
            app, bin_dir=BIN, version="1.0.0", banner=BANNER, buildconf=BUILDCONF, audit=audit
        )


@mac_libpython
def test_checker_finds_missing_and_stale_rows(tmp_path):
    app, text, _ = generated(tmp_path)
    path = app / "Contents/Resources" / notices.NOTICES
    path.write_text(
        text.replace(f"| {BIN}/ffmpeg/ffprobe | ffmpeg |\n", "").replace(
            f"| {BIN}/cpu/whisper-cli | whisper.cpp |", f"| {BIN}/cpu/whisper-cli | dusty |"
        ),
        encoding="utf-8",
    )
    (app / f"{FRAMEWORKS}/PySide6/Qt/plugins/platforms/libqminimal.dylib").write_bytes(macho())
    (app / f"{BIN}/cpu/libwhisper.1.dylib").unlink()
    findings = check.notices_findings(app, BIN, BUILDCONF + "\n    --enable-network")
    assert f"Shipped file not listed in the notices: {BIN}/ffmpeg/ffprobe" in findings
    assert f"Notices attribute {BIN}/cpu/whisper-cli without whisper.cpp" in findings
    assert "Qt plugin not listed in the notices: platforms/libqminimal.dylib" in findings
    assert f"Notices list a file that is not shipped: {BIN}/cpu/libwhisper.1.dylib" in findings
    assert "Notices do not carry the bundled ffmpeg's exact -buildconf output" in findings


@mac_libpython
def test_checker_finds_unlisted_qt_modules_and_missing_texts(tmp_path):
    app, text, _ = generated(tmp_path)
    base = app / f"{FRAMEWORKS}/PySide6/Qt/lib/QtNetwork.framework/Versions/A"
    base.mkdir(parents=True)
    (base / "QtNetwork").write_bytes(macho())
    (app / "Contents/Resources/licenses/openssl-Apache-2.0.txt").unlink()
    findings = check.notices_findings(app, BIN)
    assert "Qt module not listed in the notices: QtNetwork" in findings
    assert "Notices reference a missing license text: licenses/openssl-Apache-2.0.txt" in findings


@mac_libpython
def test_the_draft_notices_fail_the_checker(tmp_path):
    app, _, _ = generated(tmp_path)
    (app / "Contents/Resources" / notices.NOTICES).write_text(
        "# Third-party notices (macOS arm64)\n\n| Component | Version |\n", encoding="utf-8"
    )
    findings = check.notices_findings(app, BIN)
    assert any("Shipped native files" in item for item in findings)
    assert any(item.startswith("Shipped file not listed") for item in findings)


@mac_libpython
def test_mac_license_gate_reports_open_items_and_bad_linkage(tmp_path):
    app, _, inventory = generated(tmp_path)
    path = tmp_path / "audit" / notices.INVENTORY
    inventory["open_items"] = ["a license text that is not retained"]
    path.write_text(json.dumps(inventory), encoding="utf-8")
    findings = check_licenses.check_macos_bundle(app, path)
    assert findings == ["Open license item: a license text that is not retained"]
    inventory["components"]["ffmpeg"]["linkage"] = "static"
    inventory["components"]["qt"]["linkage"] = "static"
    inventory["open_items"] = []
    path.write_text(json.dumps(inventory), encoding="utf-8")
    findings = check_licenses.check_macos_bundle(app, path)
    assert "ffmpeg: unapproved or unknown bundled license: LGPL-2.1-or-later" in findings
    assert "qt: unapproved or unknown bundled license: LGPL-3.0-only" in findings


@mac_libpython
def test_mac_license_gate_requires_pinned_texts_and_matching_files(tmp_path):
    app, _, inventory = generated(tmp_path)
    inventory["open_items"] = []
    path = tmp_path / "audit" / notices.INVENTORY
    path.write_text(json.dumps(inventory), encoding="utf-8")
    assert check_licenses.check_macos_bundle(app, path) == []
    (app / "Contents/Resources/licenses/qt-LGPL-3.0.txt").write_text("edited", encoding="utf-8")
    (app / "Contents/Resources/extra.dat").write_bytes(b"x")
    findings = check_licenses.check_macos_bundle(app, path)
    assert "Missing or changed required license text: qt-LGPL-3.0.txt" in findings
    assert "Dusty.app files differ from the notices inventory" in findings
    edited = app / "Contents/Resources/licenses/macos/libpython/bzip2-1.0.8-LICENSE.txt"
    edited.write_text("edited", encoding="utf-8")
    findings = check_licenses.check_macos_bundle(app, path)
    assert (
        "Missing or changed retained Mac license text: libpython/bzip2-1.0.8-LICENSE.txt"
        in findings
    )


def test_retained_texts_are_staged_only_when_they_match_their_record(tmp_path):
    texts = tmp_path / "texts"
    shutil.copytree(notices.MAC_TEXTS, texts)
    app = tmp_path / "Dusty.app"
    sources = notices.stage_texts(app, texts)
    assert "qt/qt-6.9.2-attributions.json" in sources
    assert (app / "Contents/Resources/licenses/macos/models/silero-vad-LICENSE.txt").is_file()
    (texts / "libpython/expat-2.6.3-COPYING.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(notices.NoticesError, match="changed"):
        notices.stage_texts(tmp_path / "Other.app", texts)
    shutil.copyfile(
        notices.MAC_TEXTS / "libpython/expat-2.6.3-COPYING.txt",
        texts / "libpython/expat-2.6.3-COPYING.txt",
    )
    (texts / "libpython/unlisted.txt").write_text("x", encoding="utf-8")
    with pytest.raises(notices.NoticesError, match="sources.json"):
        notices.stage_texts(tmp_path / "Third.app", texts)


def test_retained_texts_record_pinned_upstream_sources():
    sources = json.loads((notices.MAC_TEXTS / "sources.json").read_text(encoding="utf-8"))
    for name, record in sources.items():
        origin = record.get("archive") or record["source"]
        assert origin.startswith("https://"), name
        # Split like tools/check_no_huggingface.py so the host check stays clean.
        assert "hugging" + "face" not in origin and "hf" + ".co" not in origin, name
        assert record["version"] and len(record["sha256"]) == 64, name
    assert sources["libpython/bzip2-1.0.8-LICENSE.txt"]["archive_sha256"] == (
        "ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269"
    )
