"""M5 second review: real OS locks and isolated cleanup failure injection."""

import os
import shutil
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.installer_cleanup import cleanup
from dusty.installer_upgrade import tidy_license_copies
from dusty.models.partials import cleanup_stale_partials
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import MARKER, OwnedWork, cleanup_owned, protected_paths
from dusty_fetch.downloader import download_lock, record_partial

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("work", "upgrade", "partial", "uninstall")


def scenario(base: Path, kind: str, *, replacement: Path):
    user = base / "Dusty"
    paths = RuntimePaths(base / "bin", user / "models", ROOT / "resources", user)
    if kind == "work":
        owned = OwnedWork(user / "work", "job")
        folder = owned.path
        file = folder / "audio.wav"
        file.write_bytes(b"generated audio")
        (folder / "raw.json").write_bytes(b"generated result")
        owned.record("audio.wav", "raw.json")
    elif kind == "upgrade":
        source = replacement / "licenses/dusty/dusty-0.5.0.dev12.dist-info/licenses"
        folder = base / "install/licenses/dusty/dusty-0.5.0.dev9.dist-info"
        for texts in (source, folder / "licenses"):
            texts.mkdir(parents=True)
            (texts / "LICENSE").write_bytes(b"same Apache license")
            (texts / "NOTICE").write_bytes(b"same notice")
        paths = RuntimePaths(base / "bin", user / "models", replacement / "resources", user)
        file = folder / "licenses/LICENSE"
    elif kind == "partial":
        folder = paths.models_dir
        folder.mkdir(parents=True)
        file = folder / "ggml-test.bin.part"
        file.write_bytes(b"generated prefix")
        record_partial(file)
        old = time.time() - 9 * 24 * 60 * 60
        os.utime(file, (old, old))
    else:
        folder = user
        (folder / "logs").mkdir(parents=True)
        file = folder / "logs/dusty.log"
        file.write_bytes(b"status=done")
    return SimpleNamespace(kind=kind, paths=paths, folder=folder, file=file, base=base)


def invoke(case):
    if case.kind == "work":
        return cleanup_owned(case.folder, protected=protected_paths(case.paths.user_dir))
    if case.kind == "upgrade":
        return tidy_license_copies(case.paths, case.base / "install")
    if case.kind == "partial":
        return bool(cleanup_stale_partials(case.folder))
    return cleanup(case.paths, remove_models=True)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("link_kind", ["junction", "symlink"])
def test_cleanup_reparse_target_survives(tmp_path, kind, link_kind):
    case = scenario(tmp_path, kind, replacement=tmp_path / "replacement")
    outside = tmp_path / "external-target"
    shutil.copytree(case.folder, outside)
    relative = case.file.relative_to(case.folder)
    before = (outside / relative).read_bytes()
    held = case.folder.with_name(case.folder.name + "-held")
    case.folder.rename(held)
    if link_kind == "junction":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(case.folder), str(outside)],
            check=True,
            capture_output=True,
        )
    else:
        case.folder.symlink_to(outside, target_is_directory=True)
    assert not invoke(case)
    assert (outside / relative).read_bytes() == before


@contextmanager
def exclusive_file(path: Path):
    code = """
import ctypes, sys
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.restype=ctypes.c_void_p
k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
h=k.CreateFileW(sys.argv[1],0x80000000,0,None,3,0x80,None)
if h==ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
print('locked',flush=True)
sys.stdin.readline()
k.CloseHandle.argtypes=[ctypes.c_void_p]
k.CloseHandle(h)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "locked"
        yield
    finally:
        child.communicate("close\n", timeout=10)
        assert child.returncode == 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("obstacle", ["read-only", "other-process-lock"])
def test_cleanup_preserves_os_inaccessible_file(tmp_path, kind, obstacle):
    case = scenario(tmp_path, kind, replacement=tmp_path / "replacement")
    before = case.file.read_bytes()

    def attempt():
        try:
            assert not invoke(case)
        except PermissionError:
            # Upgrade's CLI converts filesystem exceptions into its nonzero result.
            assert kind == "upgrade"
        assert case.file.exists()

    if obstacle == "read-only":
        case.file.chmod(stat.S_IREAD)
        try:
            attempt()
        finally:
            case.file.chmod(stat.S_IWRITE | stat.S_IREAD)
    else:
        with exclusive_file(case.file):
            attempt()
    assert case.file.read_bytes() == before


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("path_kind", ["unicode", "long", "OneDrive-output"])
def test_cleanup_handles_paths_and_preserves_synced_output(tmp_path, monkeypatch, kind, path_kind):
    base = tmp_path / "گفتگو_日本語"
    if path_kind == "long":
        base = tmp_path.joinpath(*(["long-path-segment-1234567890"] * 10))
        base = Path("\\\\?\\" + str(base.resolve()))
        assert len(str(base)) > 300
    case = scenario(base, kind, replacement=tmp_path / "replacement")
    output = tmp_path / "OneDrive/Transcripts"
    output.mkdir(parents=True)
    sentinel = output / "owner-keep.txt"
    sentinel.write_bytes(b"synthetic protected transcript")
    monkeypatch.setenv("OneDrive", str(output.parent))
    save_settings(
        case.paths.user_dir / "settings.json", {"schema_version": 1, "output_dir": str(output)}
    )
    assert invoke(case)
    assert not case.file.exists()
    assert sentinel.read_bytes() == b"synthetic protected transcript"


@pytest.mark.parametrize("kind", KINDS)
def test_abrupt_exit_mid_cleanup_preserves_unrelated_data(tmp_path, kind):
    case = scenario(tmp_path, kind, replacement=tmp_path / "replacement")
    sentinel = tmp_path / "OneDrive/Transcripts/owner-keep.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"synthetic protected transcript")
    save_settings(
        case.paths.user_dir / "settings.json",
        {"schema_version": 1, "output_dir": str(sentinel.parent)},
    )
    code = """
import os, sys
from pathlib import Path
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import cleanup_owned, protected_paths
from dusty.installer_cleanup import cleanup
from dusty.installer_upgrade import tidy_license_copies
from dusty.models.partials import cleanup_stale_partials
base,resources,folder=map(Path,sys.argv[2:])
paths=RuntimePaths(base/'bin',base/'Dusty/models',resources,base/'Dusty')
original=Path.unlink
def die(self,*a,**kw):
    original(self,*a,**kw)
    os._exit(91)
Path.unlink=die
kind=sys.argv[1]
if kind=='work': cleanup_owned(folder,protected=protected_paths(paths.user_dir))
elif kind=='upgrade': tidy_license_copies(paths,base/'install')
elif kind=='partial': cleanup_stale_partials(folder)
else: cleanup(paths,remove_models=True)
"""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            kind,
            str(case.base),
            str(case.paths.resources_dir),
            str(case.folder),
        ],
        timeout=20,
        capture_output=True,
    )
    assert child.returncode == 91, child.stderr.decode(errors="replace")
    assert sentinel.read_bytes() == b"synthetic protected transcript"
    if kind == "work":
        assert (case.folder / MARKER).exists()
        assert not invoke(case)  # Incomplete inventory stays conservative.
        assert len(list(case.folder.glob("*"))) >= 2
    elif kind == "upgrade":
        assert (case.folder / "licenses/NOTICE").exists()
        # A subsequent attempt must recover its proven cleanup transaction.
        assert invoke(case)
    else:
        invoke(case)
    assert sentinel.read_bytes() == b"synthetic protected transcript"


def test_stale_partial_cleanup_respects_active_downloader_lock(tmp_path):
    models = tmp_path / "user/models"
    models.mkdir(parents=True)
    part = models / "ggml-test.bin.part"
    part.write_bytes(b"old resumable bytes")
    record_partial(part)
    old = time.time() - 9 * 24 * 60 * 60
    os.utime(part, (old, old))
    with download_lock(models / "ggml-test.bin.lock"):
        assert cleanup_stale_partials(models) == 0
        assert part.read_bytes() == b"old resumable bytes"
    assert cleanup_stale_partials(models) == 1
