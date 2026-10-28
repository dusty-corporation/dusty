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
    deadline = time.monotonic() + 2.0
    while True:
        try:
            case.folder.rename(held)
            break
        except OSError as error:
            # Windows can briefly hold the generated model receipt while the
            # tracing gate runs. This only prepares the fixture; a persistent
            # denial still fails before any product assertion is reached.
            if getattr(error, "winerror", None) not in {5, 32, 33} or time.monotonic() >= deadline:
                raise
            time.sleep(0.025)
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
        # An interrupted first cleanup may leave recorded files absent. The
        # second attempt removes only the remaining proven work, not output.
        assert invoke(case)
        assert not case.folder.exists()
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


def atomic_writer(folder, kind):
    from dusty.core import BatchOptions, Job, Segment, Transcript
    from dusty.queue.outputs import write_outputs
    from dusty.queue.storage import atomic_json

    folder.mkdir(parents=True, exist_ok=True)
    if kind == "state":
        target = folder / "settings.json"
        return target, lambda: atomic_json(target, {"schema_version": 1, "theme": "dark"})
    target = folder / "clip.txt"
    options = BatchOptions("tiny", folder, formats=("txt",), collision="overwrite")
    text = Transcript((Segment(0, 0, 1, "Hello"),), "en", "transcribe", "tiny", "cpu", 1)
    return target, lambda: write_outputs(Job(folder.parent / "clip.wav"), options, text)


@pytest.mark.parametrize("kind", ["state", "export"])
@pytest.mark.parametrize("obstacle", ["read-only", "other-process-lock"])
def test_atomic_overwrite_retains_inaccessible_original(tmp_path, kind, obstacle):
    target, write = atomic_writer(tmp_path / "OneDrive/Transcripts", kind)
    target.write_bytes(b'{"original":"keep"}')
    if obstacle == "read-only":
        target.chmod(stat.S_IREAD)
        try:
            with pytest.raises(OSError):
                write()
        finally:
            target.chmod(stat.S_IWRITE | stat.S_IREAD)
    else:
        with exclusive_file(target), pytest.raises(OSError):
            write()
    assert target.read_bytes() == b'{"original":"keep"}'
    assert not list(target.parent.glob("*.dusty-tmp"))


@pytest.mark.parametrize("kind", ["state", "export"])
@pytest.mark.parametrize("alias", ["junction", "symlink"])
def test_atomic_write_refuses_linked_output_parent(tmp_path, kind, alias):
    outside = tmp_path / "outside"
    target, _ = atomic_writer(outside, kind)
    target.write_bytes(b"private synthetic sentinel")
    link = tmp_path / "linked-output"
    if alias == "junction":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    _, write = atomic_writer(link, kind)
    with pytest.raises(OSError):
        write()
    assert target.read_bytes() == b"private synthetic sentinel"


@pytest.mark.parametrize("kind", ["state", "export"])
@pytest.mark.parametrize("long", [False, True])
def test_atomic_write_handles_unicode_and_extended_long_path(tmp_path, kind, long):
    folder = tmp_path / "گفتگو_日本語"
    if long:
        folder = Path("\\\\?\\" + str(folder.joinpath(*(["length-1234567890"] * 16)).resolve()))
        assert len(str(folder)) > 300
    target, write = atomic_writer(folder, kind)
    write()
    assert target.read_bytes() in (b"Hello\r\n", b'{\n  "schema_version": 1,\n  "theme": "dark"\n}')


@pytest.mark.parametrize("kind", ["state", "export"])
@pytest.mark.parametrize("point", ["before", "after"])
def test_crash_at_atomic_replace_keeps_complete_original_or_result(tmp_path, kind, point):
    import json

    target, _ = atomic_writer(tmp_path / "destination", kind)
    original = b'{"original":"keep"}'
    target.write_bytes(original)
    code = """
import os,sys
from pathlib import Path
from dusty.queue.storage import atomic_json
from dusty.queue.outputs import write_outputs
from dusty.core import BatchOptions,Job,Segment,Transcript
folder=Path(sys.argv[1]); kind=sys.argv[2]; point=sys.argv[3]
replace=os.replace
def die(*a,**kw):
    if point=='after': replace(*a,**kw)
    os._exit(91)
os.replace=die
if kind=='state': atomic_json(folder/'settings.json',{'schema_version':1,'theme':'dark'})
else:
    text=Transcript((Segment(0,0,1,'Hello'),),'en','transcribe','tiny','cpu',1)
    write_outputs(Job(folder.parent/'clip.wav'),BatchOptions('tiny',folder,formats=('txt',),collision='overwrite'),text)
"""
    run = subprocess.run(
        [sys.executable, "-c", code, str(target.parent), kind, point],
        capture_output=True,
        timeout=20,
    )
    assert run.returncode == 91, run.stderr.decode(errors="replace")
    if point == "before":
        assert target.read_bytes() == original
    elif kind == "state":
        assert json.loads(target.read_bytes()) == {"schema_version": 1, "theme": "dark"}
    else:
        assert target.read_bytes() == b"Hello\r\n"
