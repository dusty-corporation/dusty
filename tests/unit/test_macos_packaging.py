"""Pure logic of the macOS bundle build and audit tools (MAC10-PACKAGE)."""

import os
import plistlib
import shutil
import struct
import sys
from pathlib import Path

import pytest

from dusty.engine.binaries import ffmpeg_path, ffprobe_path, lifeline_path, whisper_path
from dusty.runtime_paths import resolve_fetch_command, resolve_paths
from dusty_fetch.tls import ROOTS, resource_dir
from tools import build_macos_app as build
from tools import check_macos_bundle as check

ROOT = Path(__file__).resolve().parents[2]
darwin_only = pytest.mark.skipif(
    sys.platform != "darwin" or not Path("/usr/bin/codesign").exists(),
    reason="needs macOS codesign",
)
mac_app_paths = pytest.mark.skipif(
    sys.platform != "darwin", reason="Mac app paths are POSIX absolute paths"
)


def macho(
    *,
    dylibs=("/usr/lib/libSystem.B.dylib",),
    rpaths=("@loader_path",),
    minos=(13, 0, 0),
    filetype=check.MH_EXECUTE,
    code=b"\x01" * 64,
    signature=b"",
    cputype=0x0100000C,
) -> bytes:
    """A small but well formed thin Mach-O image with optional code signature."""

    def padded(text: str, header: int) -> tuple[bytes, int]:
        raw = text.encode() + b"\0"
        size = (header + len(raw) + 7) // 8 * 8
        return raw.ljust(size - header, b"\0"), size

    commands = []
    for name in dylibs:
        raw, size = padded(name, 24)
        commands.append(struct.pack("<IIIIII", 0xC, size, 24, 0, 0, 0) + raw)
    for entry in rpaths:
        raw, size = padded(entry, 12)
        commands.append(struct.pack("<III", check.LC_RPATH, size, 12) + raw)
    version = (minos[0] << 16) | (minos[1] << 8) | minos[2]
    commands.append(struct.pack("<IIIIII", check.LC_BUILD_VERSION, 24, 1, version, version, 0))
    linkedit_at = len(commands)
    commands.append(b"")  # placeholder for __LINKEDIT
    if signature:
        commands.append(b"")  # placeholder for LC_CODE_SIGNATURE
    sizeofcmds = sum(len(item) for item in commands) + 72 + (16 if signature else 0)
    body_start = 32 + sizeofcmds
    dataoff = body_start + len(code)
    commands[linkedit_at] = struct.pack(
        "<II16sQQQQIIII",
        check.LC_SEGMENT_64,
        72,
        b"__LINKEDIT",
        0x4000,
        0x4000 + len(signature) * 3,
        body_start,
        len(code) + len(signature),
        1,
        1,
        0,
        0,
    )
    if signature:
        commands[-1] = struct.pack("<IIII", check.LC_CODE_SIGNATURE, 16, dataoff, len(signature))
    header = struct.pack(
        "<IiiIIIII", check.MH_MAGIC_64, cputype, 0, filetype, len(commands), sizeofcmds, 0, 0
    )
    return header + b"".join(commands) + code + signature


# Layout agreement with the application's own path rules.


def test_layout_choices_and_refusal() -> None:
    assert build.layout("helpers")["bin_dir"] == "Contents/Helpers/bin"
    assert build.layout("resources")["bin_dir"] == "Contents/Resources/bin"
    with pytest.raises(build.BuildError):
        build.layout("macos")


@mac_app_paths
def test_fetch_and_tls_locations_match_the_application() -> None:
    app = Path("/Volumes/Test é/Dusty.app")
    executable = app / "Contents/MacOS/Dusty"
    command = resolve_fetch_command(frozen=True, executable=executable, platform="darwin")
    assert Path(command[0]) == app / check.FETCH_EXECUTABLE
    helper = app / check.FETCH_EXECUTABLE
    assert resource_dir(frozen=True, executable=helper, platform="darwin") == app / check.TLS_DIR
    assert set(ROOTS) == set(check.TLS_FILES)


@mac_app_paths
def test_current_runtime_bin_dir_is_a_supported_build_choice() -> None:
    executable = Path("/Applications/Dusty.app/Contents/MacOS/Dusty")
    paths = resolve_paths(frozen=True, executable=executable, environment={}, platform="darwin")
    relative = paths.bin_dir.relative_to(Path("/Applications/Dusty.app")).as_posix()
    assert relative in check.BIN_DIRS.values()
    assert paths.resources_dir == Path("/Applications/Dusty.app") / check.RESOURCES


def test_native_program_names_match_engine_binaries() -> None:
    bin_dir = Path("/x")
    expected = {
        ffmpeg_path(bin_dir, "darwin"),
        ffprobe_path(bin_dir, "darwin"),
        whisper_path(bin_dir, "cpu", "darwin"),
        whisper_path(bin_dir, "metal", "darwin"),
        lifeline_path(bin_dir),
    }
    assert expected <= {bin_dir / name for name in check.NATIVE_PROGRAMS}


# Output folder rules.


def test_output_must_be_new(tmp_path: Path) -> None:
    elsewhere = tmp_path / "repository"  # the default root contains pytest's tmp_path
    existing = tmp_path / "out"
    existing.mkdir()
    with pytest.raises(build.BuildError, match="existing"):
        build.validate_output(existing, elsewhere)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "missing")
    with pytest.raises(build.BuildError, match="existing"):
        build.validate_output(link, elsewhere)
    with pytest.raises(build.BuildError, match="parent"):
        build.validate_output(tmp_path / "no/such/out", elsewhere)
    assert build.validate_output(tmp_path / "fresh", elsewhere) == tmp_path.resolve() / "fresh"


def test_output_inside_repository_must_be_under_build(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    (repository / "build").mkdir(parents=True)
    (repository / "src").mkdir()
    with pytest.raises(build.BuildError, match="build/"):
        build.validate_output(repository / "src/app", repository)
    assert build.validate_output(repository / "build/app", repository).name == "app"


def test_read_sums(tmp_path: Path) -> None:
    sums = tmp_path / "SHA256SUMS.txt"
    sums.write_text("a" * 64 + "  whisper-cli\n" + "b" * 64 + " *LICENSE.txt\n", encoding="utf-8")
    assert build.read_sums(sums) == {"whisper-cli": "a" * 64, "LICENSE.txt": "b" * 64}
    sums.write_text("nothex  whisper-cli\n", encoding="utf-8")
    with pytest.raises(build.BuildError):
        build.read_sums(sums)


# Mach-O parsing and signature-neutral comparison.


def test_parse_macho_reads_dependencies_rpaths_and_minimum_os() -> None:
    image = check.parse_macho(
        macho(dylibs=("@rpath/libwhisper.1.dylib", "/usr/lib/libc++.1.dylib"), minos=(26, 0, 0))
    )
    assert image.thin_arm64
    assert image.dylibs == ["@rpath/libwhisper.1.dylib", "/usr/lib/libc++.1.dylib"]
    assert image.rpaths == ["@loader_path"]
    assert image.minos == (26, 0, 0)
    assert check.version_text(image.minos) == "26.0"
    assert not check.parse_macho(macho(cputype=0x01000007)).thin_arm64


def test_fat_files_are_reported_by_architecture() -> None:
    fat = struct.pack(">II", 0xCAFEBABE, 2)
    fat += struct.pack(">IIIII", 0x01000007, 3, 0, 0, 0) + struct.pack(
        ">IIIII", 0x0100000C, 0, 0, 0, 0
    )
    assert check.macho_magic(fat[:8]) == "fat"
    assert check.parse_macho(fat).arches == ["x86_64", "arm64"]
    assert check.macho_magic(b"\xca\xfe\xba\xbe\x00\x00\x00\x37") is None  # Java class file
    assert check.macho_magic(b"PK\x03\x04") is None


def test_signature_neutral_digest_ignores_only_the_signature() -> None:
    original = macho(signature=b"S" * 32)
    resigned = macho(signature=b"T" * 48)  # different blob and recorded sizes
    assert original != resigned
    assert check.signature_neutral_digest(original) == check.signature_neutral_digest(resigned)
    changed = macho(signature=b"S" * 32, code=b"\x02" + b"\x01" * 63)
    assert check.signature_neutral_digest(changed) != check.signature_neutral_digest(original)
    moved = macho(signature=b"S" * 32, rpaths=("@executable_path",))
    assert check.signature_neutral_digest(moved) != check.signature_neutral_digest(original)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("/usr/lib/libSystem.B.dylib", "system"),
        ("/System/Library/Frameworks/Metal.framework/Versions/A/Metal", "system"),
        ("@rpath/QtCore", "relative"),
        ("@loader_path/libggml.0.dylib", "relative"),
        ("@executable_path/../Frameworks/libpython3.12.dylib", "relative"),
        ("/opt/homebrew/lib/libavcodec.dylib", "outside"),
        ("/usr/local/lib/libssl.dylib", "outside"),
        ("/Users/someone/project/.venv/lib/libpython3.12.dylib", "outside"),
        ("/usr/lib/../../opt/homebrew/lib/x.dylib", "outside"),
        ("libbare.dylib", "outside"),
    ],
)
def test_dependency_classification(name: str, kind: str) -> None:
    assert check.classify_dependency(name) == kind


def test_resolve_dependency_inside_and_outside(tmp_path: Path) -> None:
    folder = tmp_path / "bin/cpu"
    folder.mkdir(parents=True)
    loader = folder / "whisper-cli"
    (folder / "libwhisper.1.dylib").write_bytes(b"x")
    found = check.resolve_dependency("@rpath/libwhisper.1.dylib", loader, ["@loader_path"], folder)
    assert found == folder / "libwhisper.1.dylib"
    assert (
        check.resolve_dependency("@rpath/libmissing.dylib", loader, ["@loader_path"], folder)
        is None
    )
    assert check.resolve_dependency("@rpath/libwhisper.1.dylib", loader, [], folder) is None


def test_dependency_findings_flag_leaks(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    folder = app / "Contents/Helpers/bin/cpu"
    folder.mkdir(parents=True)
    (folder / "whisper-cli").write_bytes(
        macho(dylibs=("@rpath/libwhisper.1.dylib", "/opt/homebrew/lib/libz.dylib"))
    )
    (folder / "libwhisper.1.dylib").write_bytes(
        macho(dylibs=("@rpath/libwhisper.1.dylib",), filetype=6, rpaths=("/usr/local/lib",))
    )
    (folder / "x86").write_bytes(macho(cputype=0x01000007))
    findings = "\n".join(check.dependency_findings(app))
    assert "Non-system absolute dependency /opt/homebrew/lib/libz.dylib" in findings
    assert "Absolute LC_RPATH /usr/local/lib" in findings
    assert "Not thin arm64" in findings
    assert (
        "Unresolved dependency @rpath/libwhisper.1.dylib: Contents/Helpers/bin/cpu/whisper-cli"
        not in findings
    )
    assert (
        "Unresolved dependency @rpath/libwhisper.1.dylib: Contents/Helpers/bin/cpu/libwhisper"
        in findings
    )


# Info.plist, modules, entitlements and file policy.


def good_plist(**changes) -> dict:
    info = {
        "CFBundleIdentifier": "org.dusty.Dusty",
        "CFBundleExecutable": "Dusty",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSMinimumSystemVersion": "26.0",
    }
    info.update(changes)
    return info


def test_plist_findings() -> None:
    assert check.plist_findings(good_plist(), version="1.0.0", minimum=(26, 0, 0)) == []
    low = check.plist_findings(
        good_plist(LSMinimumSystemVersion="13.0"), version="1.0.0", minimum=(26, 0, 0)
    )
    assert any("below the binaries" in item for item in low)
    usage = check.plist_findings(
        good_plist(NSLocalNetworkUsageDescription="x", NSAppTransportSecurity={}),
        version="1.0.0",
        minimum=None,
    )
    assert len(usage) == 2
    assert check.plist_findings(good_plist(), version="2.0.0", minimum=None)


def test_module_findings() -> None:
    fine_gui = ["dusty.app.window", "urllib.parse", "http", "PySide6.QtWidgets"]
    fine_fetch = ["ssl", "socket", "http.client", "dusty_fetch", "dusty_fetch.tls"]
    assert check.module_findings(fine_gui, fine_fetch) == []
    findings = check.module_findings(
        [*fine_gui, "socket", "urllib.request", "PySide6.QtNetwork", "dusty_fetch.tls"],
        ["dusty.runtime_paths", "PySide6.QtCore"],
    )
    text = "\n".join(findings)
    for name in ("socket", "urllib.request", "PySide6.QtNetwork", "dusty_fetch.tls"):
        assert f"prohibited module {name}" in text
    assert "Downloader embeds GUI module dusty.runtime_paths" in text
    assert "Downloader is missing module ssl" in text


def test_entitlement_policy() -> None:
    relaxed = {check.ADHOC_ENTITLEMENT: True}
    assert check.entitlement_policy({}, entitled=False, adhoc=False) == []
    assert check.entitlement_policy(relaxed, entitled=True, adhoc=True) == []
    assert check.entitlement_policy(relaxed, entitled=False, adhoc=True)
    assert check.entitlement_policy(relaxed, entitled=True, adhoc=False)
    jit = {check.ADHOC_ENTITLEMENT: True, "com.apple.security.cs.allow-jit": True}
    assert check.entitlement_policy(jit, entitled=True, adhoc=True)


def test_gui_file_policy(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    frameworks = app / "Contents/Frameworks/PySide6/Qt/lib"
    (frameworks / "QtCore.framework").mkdir(parents=True)
    (frameworks / "QtNetwork.framework").mkdir()
    (app / "Contents/Frameworks/_ssl.cpython-312-darwin.so").write_bytes(b"x")
    fetch = app / check.FETCH_DIR / "_internal"
    fetch.mkdir(parents=True)
    (fetch / "_ssl.cpython-312-darwin.so").write_bytes(b"x")  # allowed in the downloader
    (fetch / "QtCore").write_bytes(b"x")
    text = "\n".join(check.gui_file_findings(app))
    assert "QtNetwork" in text and "QtCore.framework" not in text
    assert "Contents/Frameworks/_ssl" in text and "Helpers/dusty-fetch/_internal/_ssl" not in text
    assert "Downloader contains Qt" in text


def test_nested_code_and_bundle_root_rules(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    helper = app / "Contents/Helpers/bin/cpu"
    helper.mkdir(parents=True)
    (helper / "whisper-cli").write_bytes(macho())
    (helper / "LICENSE.txt").write_text("license", encoding="utf-8")
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({}))
    (app / "Contents/NOTES.md").write_text("x", encoding="utf-8")
    (app / "Contents/Resources").mkdir()
    (app / "Contents/Resources/THIRD_PARTY_NOTICES.md").write_text("x", encoding="utf-8")
    (app / "Contents/THIRD_PARTY_NOTICES.md").symlink_to("Resources/THIRD_PARTY_NOTICES.md")
    findings = check.nested_code_findings(app)
    assert findings == [
        "Data file in a code location: Contents/Helpers/bin/cpu/LICENSE.txt",
        "Unsealable file at the bundle root: Contents/NOTES.md",
    ]


def test_symlinks_must_stay_inside(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents/inside").symlink_to("Info.plist")
    (app / "Contents/Info.plist").write_bytes(b"x")
    (app / "Contents/absolute").symlink_to("/usr/lib")
    (app / "Contents/escape").symlink_to("../../outside")
    (tmp_path / "outside").write_text("x", encoding="utf-8")
    assert set(check.symlink_findings(app)) == {
        "Absolute symlink: Contents/absolute",
        "Symlink leaves the bundle or is broken: Contents/escape",
    }


def test_model_weights_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "Contents").mkdir()
    (tmp_path / "Contents/ggml-tiny.bin").write_bytes(b"x")
    (tmp_path / "Contents/weights").write_bytes(b"x")
    manifest = {"models": [{"file_name": "weights"}], "vad": []}
    assert len(check.model_findings(tmp_path, manifest)) == 2


# Build steps that work on plain files.


def test_relocate_data_files_links_back_into_resources(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    internal = app / check.FETCH_DIR / "_internal"
    internal.mkdir(parents=True)
    (app / check.FETCH_DIR / "dusty-fetch").write_bytes(macho())
    (internal / "libpython3.12.dylib").write_bytes(macho(filetype=6))
    (internal / "base_library.zip").write_bytes(b"PK\x03\x04data")
    moved = build.relocate_data_files(app, check.FETCH_DIR, check.FETCH_DATA)
    assert moved == ["_internal/base_library.zip"]
    link = internal / "base_library.zip"
    assert link.is_symlink() and not os.path.isabs(os.readlink(link))
    assert link.resolve() == (app / check.FETCH_DATA / "_internal/base_library.zip").resolve()
    assert link.read_bytes() == b"PK\x03\x04data"
    assert not (internal / "libpython3.12.dylib").is_symlink()
    assert check.nested_code_findings(app) == []


def test_signing_order_is_inside_out(tmp_path: Path) -> None:
    app = tmp_path / "Dusty.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Dusty"}))
    (contents / "MacOS/Dusty").write_bytes(macho())
    version = contents / "Frameworks/PySide6/Qt/lib/QtCore.framework/Versions/A"
    version.mkdir(parents=True)
    (version / "QtCore").write_bytes(macho(filetype=6))
    (version.parent / "Current").symlink_to("A")
    plugin = contents / "Frameworks/PySide6/Qt/plugins/platforms/libqcocoa.dylib"
    plugin.parent.mkdir(parents=True)
    plugin.write_bytes(macho(filetype=6))
    helper = contents / "Helpers/bin/cpu/whisper-cli"
    helper.parent.mkdir(parents=True)
    helper.write_bytes(macho(dylibs=("@rpath/libwhisper.1.dylib",)))
    order = build.signing_order(app)
    assert order[-1] == app
    assert contents / "MacOS/Dusty" not in order  # signed as the app's main executable
    assert version / "QtCore" not in order  # signed with its framework
    assert version.resolve() in order and plugin in order and helper in order
    assert build.loads_bundled_code(app, helper)
    assert not build.loads_bundled_code(app, plugin)
    assert build.entitlements_for(app, helper, "-", None) == build.ADHOC_ENTITLEMENTS
    assert build.entitlements_for(app, helper, "Developer ID Application: X", None) is None
    assert build.entitlements_for(app, plugin, "-", None) is None


def test_codesign_arguments() -> None:
    adhoc = build.codesign_args("-", None, executable=False, loose=True)
    assert adhoc[:7] == [
        "/usr/bin/codesign",
        "--force",
        "--sign",
        "-",
        "--options",
        "runtime",
        "--timestamp=none",
    ]
    named = build.codesign_args(
        "Developer ID Application: X", Path("e.plist"), executable=True, loose=False
    )
    assert "--timestamp" in named and "--entitlements" in named and "--prefix" not in named


def test_adhoc_entitlements_file_holds_only_library_validation() -> None:
    data = plistlib.loads(build.ADHOC_ENTITLEMENTS.read_bytes())
    assert data == {check.ADHOC_ENTITLEMENT: True}


def test_project_version_matches_package() -> None:
    from dusty import __version__

    assert build.project_version() == __version__


# Real codesign on a tiny bundle (macOS only).


@darwin_only
def test_adhoc_signing_of_a_small_bundle(tmp_path: Path) -> None:
    app = tmp_path / "Folder é/T.app"
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/Helpers/bin/tool").mkdir(parents=True)
    shutil.copyfile("/usr/bin/true", app / "Contents/MacOS/T")
    shutil.copyfile("/usr/bin/true", app / "Contents/Helpers/bin/tool/tool")
    os.chmod(app / "Contents/MacOS/T", 0o755)
    os.chmod(app / "Contents/Helpers/bin/tool/tool", 0o755)
    (app / "Contents/Info.plist").write_bytes(
        plistlib.dumps(
            {
                "CFBundleExecutable": "T",
                "CFBundleIdentifier": "org.dusty.test",
                "CFBundlePackageType": "APPL",
            }
        )
    )
    build.sign_bundle(app)
    build.verify_signature(app, tmp_path / "verify.txt")
    assert check.signature_findings(app) == []
    (app / "Contents/Helpers/bin/tool/LICENSE.txt").write_text("x", encoding="utf-8")
    assert check.signature_findings(app)  # the seal no longer matches
    with pytest.raises(build.BuildError):
        build.sign_bundle(app)  # codesign refuses data in a code location


# Choice of native builds: native-v3 when present, otherwise runtime-v1 plus native-v2.


def _sums_package(folder: Path, files: dict[str, bytes]) -> dict[str, str]:
    import hashlib

    (folder / "package").mkdir(parents=True)
    sums = {}
    for name, data in files.items():
        (folder / "package" / name).write_bytes(data)
        sums[name] = hashlib.sha256(data).hexdigest()
    (folder / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sums.items()), encoding="utf-8"
    )
    return sums


def _native_v3(root: Path) -> dict[str, dict[str, str]]:
    cli = macho()
    return {
        "ffmpeg": _sums_package(
            root / "native-v3/ffmpeg", {"ffmpeg": b"ff", "ffprobe": b"fp", "LICENSE.txt": b"L"}
        ),
        "whisper-cpu": _sums_package(
            root / "native-v3/whisper-cpu", {"whisper-cli": cli, "LICENSE.txt": b"MIT"}
        ),
        "whisper-metal": _sums_package(
            root / "native-v3/whisper-metal", {"whisper-cli": cli, "LICENSE.txt": b"MIT"}
        ),
    }


def test_native_generation_falls_back_without_native_v3(tmp_path: Path) -> None:
    assert build.native_generation(tmp_path) == "native-v2"


def test_incomplete_native_v3_is_refused_rather_than_mixed(tmp_path: Path) -> None:
    _sums_package(tmp_path / "native-v3/whisper-cpu", {"whisper-cli": macho()})
    with pytest.raises(build.BuildError, match="incomplete.*whisper-metal, ffmpeg"):
        build.native_generation(tmp_path)
    with pytest.raises(build.BuildError, match="incomplete"):
        build.ffmpeg_natives(tmp_path)


def test_native_v3_supplies_every_native_program(tmp_path: Path) -> None:
    sums = _native_v3(tmp_path)
    assert build.native_generation(tmp_path) == "native-v3"
    ffmpeg = build.ffmpeg_natives(tmp_path)
    assert [item.destination for item in ffmpeg] == ["ffmpeg/ffmpeg", "ffmpeg/ffprobe"]
    assert [item.sha256 for item in ffmpeg] == [sums["ffmpeg"]["ffmpeg"], sums["ffmpeg"]["ffprobe"]]
    assert {item.trust for item in ffmpeg} == {str(tmp_path / "native-v3/ffmpeg/SHA256SUMS.txt")}
    for backend in ("cpu", "metal"):
        (native,) = build.whisper_natives(tmp_path, backend)
        assert native.source == (tmp_path / f"native-v3/whisper-{backend}/package/whisper-cli")
        assert native.sha256 == sums[f"whisper-{backend}"]["whisper-cli"]
    license_file = build.whisper_license(tmp_path)
    assert license_file.source == tmp_path / "native-v3/whisper-cpu/package/LICENSE.txt"
    for native in [*ffmpeg, license_file]:
        build.verify_source(native)


def test_native_v3_ffmpeg_must_match_its_sums(tmp_path: Path) -> None:
    _native_v3(tmp_path)
    package = tmp_path / "native-v3/ffmpeg/package"
    (package / "ffprobe").write_bytes(b"changed")
    with pytest.raises(build.BuildError, match="does not match"):
        for native in build.ffmpeg_natives(tmp_path):
            build.verify_source(native)
    (package / "ffprobe").unlink()
    (package / "ffprobe").symlink_to(package / "ffmpeg")
    with pytest.raises(build.BuildError, match="ffprobe is missing"):
        build.ffmpeg_natives(tmp_path)
