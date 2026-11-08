"""External drive outputs and full, read-only and ejected volumes on macOS (P19, P28).

Disk images made with hdiutil stand in for external drives: APFS, exFAT and
FAT32, attached without Finder under pytest's tmp_path and always detached in
teardown. The real Coordinator, native engine and FFmpeg run with the Tiny model.
Stage a development bin_dir with tools/stage_macos_dev_bin.py and point
DUSTY_BIN_DIR at it and DUSTY_MODELS_DIR at hash verified catalog models.
"""

import os
import shutil
import signal
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine.binaries import lifeline_path, whisper_path
from dusty.models import ModelRegistry, load_manifest
from dusty.privacy.logging import configure_logger
from dusty.queue import Coordinator
from dusty.queue.scanning import scan_inputs
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "tests/fixtures/audio"
HDIUTIL = Path("/usr/bin/hdiutil")
FILESYSTEMS = {"apfs": "APFS", "exfat": "ExFAT", "fat32": "MS-DOS FAT32"}
# hdiutil refuses FAT32 images below about 33 MB.
SIZES_MB = {"apfs": 20, "exfat": 20, "fat32": 40}


def _staged() -> bool:
    bin_dir = os.environ.get("DUSTY_BIN_DIR")
    models_dir = os.environ.get("DUSTY_MODELS_DIR")
    if not bin_dir or not models_dir:
        return False
    return (
        whisper_path(Path(bin_dir), "cpu", "darwin").is_file()
        and whisper_path(Path(bin_dir), "metal", "darwin").is_file()
        and lifeline_path(Path(bin_dir)).is_file()
        and (Path(models_dir) / "ggml-tiny.bin").is_file()
    )


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or not HDIUTIL.is_file() or not _staged(),
    reason="Needs macOS, hdiutil and a staged DUSTY_BIN_DIR (cpu, metal, lifeline) "
    "plus DUSTY_MODELS_DIR",
)


def _hdiutil(*args: str) -> None:
    subprocess.run(
        [str(HDIUTIL), *args],
        check=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"},
    )


@dataclass
class Volumes:
    """Disk images attached for one test; teardown detaches every one of them."""

    folder: Path
    attached: list[Path] = field(default_factory=list)
    locked: list[Path] = field(default_factory=list)

    def attach(
        self,
        fs: str,
        *,
        readonly: bool = False,
        prepare: Callable[[Path], None] | None = None,
    ) -> Path:
        index = len(list(self.folder.glob("*.dmg")))
        image = self.folder / f"volume{index}-{fs}.dmg"
        # Each mount point gets its own parent folder, like /Volumes.
        mount = self.folder / f"mounts{index}" / "Dusty Test"
        mount.parent.mkdir(parents=True)
        _hdiutil(
            "create",
            "-quiet",
            "-size",
            f"{SIZES_MB[fs]}m",
            "-fs",
            FILESYSTEMS[fs],
            "-volname",
            "DUSTYTEST",
            str(image),
        )
        if prepare:
            self._mount(image, mount, [])
            try:
                prepare(mount)
            finally:
                self.detach(mount)
        self._mount(image, mount, ["-readonly"] if readonly else [])
        return mount

    def _mount(self, image: Path, mount: Path, extra: list[str]) -> None:
        self.attached.append(mount)
        _hdiutil(
            "attach",
            "-quiet",
            "-nobrowse",
            "-noautoopen",
            *extra,
            "-mountpoint",
            str(mount),
            str(image),
        )

    def detach(self, mount: Path, *, eject: bool = False) -> None:
        """Detach; an eject also stops anyone recreating the folder, as /Volumes does."""
        _hdiutil("detach", "-quiet", "-force", str(mount))
        self.attached.remove(mount)
        if eject:
            mount.parent.chmod(0o555)
            self.locked.append(mount.parent)

    def close(self) -> None:
        for folder in self.locked:
            folder.chmod(0o755)
        for mount in reversed(self.attached):
            if os.path.ismount(mount):
                subprocess.run(
                    [str(HDIUTIL), "detach", "-quiet", "-force", str(mount)],
                    check=False,
                    capture_output=True,
                )
        self.attached.clear()


@pytest.fixture
def volumes(tmp_path: Path) -> Iterator[Volumes]:
    folder = tmp_path / "images"
    folder.mkdir()
    created = Volumes(folder)
    try:
        yield created
    finally:
        created.close()


def _paths(base: Path) -> tuple[RuntimePaths, ModelRegistry]:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, base / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    return paths, registry


@pytest.fixture
def runtime(tmp_path: Path) -> tuple[RuntimePaths, ModelRegistry]:
    return _paths(tmp_path)


def _run(
    runtime: tuple[RuntimePaths, ModelRegistry],
    jobs: list[Job],
    options: BatchOptions,
    **kwargs,  # type: ignore[no-untyped-def]
) -> list[Job]:
    paths, registry = runtime
    configure_logger(paths.user_dir)
    return Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=True, **kwargs)


def _copy(relative: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AUDIO / relative, target)
    return target


def _files(folder: Path) -> list[str]:
    """Every file and folder below a volume folder, except the system event store."""
    if not folder.exists():
        return []
    return sorted(
        str(path.relative_to(folder))
        for path in folder.rglob("*")
        if ".fseventsd" not in path.relative_to(folder).parts
    )


def _sidecars(listing: list[str]) -> list[str]:
    return [name for name in listing if Path(name).name.startswith("._")]


def _keeps_provenance_sidecars(mount: Path) -> bool:
    """Whether new files on this volume get a "._" sidecar on this Mac.

    macOS stores the com.apple.provenance attribute of every file a process
    creates in a "._" AppleDouble file on FAT and exFAT, which have no extended
    attributes of their own. Not every Mac tags new files (a CI virtual machine
    may not), so the tests probe the mounted volume instead of assuming.
    """
    probe = mount / "provenance-probe"
    probe.write_bytes(b"probe")
    sidecar = mount / "._provenance-probe"
    keeps = sidecar.exists()
    probe.unlink()
    sidecar.unlink(missing_ok=True)
    return keeps


def _orphan_sidecars(listing: list[str]) -> list[str]:
    """AppleDouble files whose own file or folder is gone, which Dusty must never leave."""
    present = set(listing)
    return [
        name
        for name in _sidecars(listing)
        if str(Path(name).with_name(Path(name).name[2:])) not in present
    ]


def _native_children(bin_dir: Path) -> list[str]:
    """Running processes whose executable lives in this staged bin_dir."""
    listing = subprocess.run(
        ["/bin/ps", "-A", "-o", "pid=,comm="],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    ).stdout
    root = str(bin_dir.resolve())
    return [line for line in listing.splitlines() if root in line]


def _work_empty(paths: RuntimePaths) -> bool:
    return list((paths.user_dir / "work").iterdir()) == []


def _jfk_words(text: str) -> bool:
    text = text.lower()
    return "country" in text and ("americans" in text or "ask not" in text)


def _tree(root: Path) -> Path:
    for relative in ("jfk.wav", "a/jfk.wav", "a/deep/jfk.mp3", "b/jfk.wav"):
        _copy("formats/" + Path(relative).name, root / relative)
    return root


# P19: kept structure and duplicate basenames on external drive formats.


@pytest.mark.parametrize(
    ("fs", "backend"), [("apfs", "metal"), ("exfat", "metal"), ("fat32", "cpu")]
)
def test_outputs_on_external_formats_keep_structure_and_duplicate_names(
    runtime: tuple[RuntimePaths, ModelRegistry],
    volumes: Volumes,
    mac_gpu: SimpleNamespace,
    tmp_path: Path,
    fs: str,
    backend: str,
) -> None:
    paths, _ = runtime
    # A Metal request runs on the CPU where the engine reports it cannot use the GPU.
    used = mac_gpu.backend if backend == "metal" else backend
    root = _tree(tmp_path / "in")
    mount = volumes.attach(fs)
    sidecars_expected = _keeps_provenance_sidecars(mount)
    assert not sidecars_expected or fs != "apfs"
    produced: dict[str, list[str]] = {}
    for layout in ("kept", "flat"):
        jobs = list(scan_inputs([root], recursive=True).jobs)
        options = BatchOptions(
            "tiny",
            mount / layout,
            formats=("txt", "docx"),
            backend=backend,
            language="en",
            keep_structure=layout == "kept",
        )
        _run(runtime, jobs, options)
        assert [job.status for job in jobs] == [JobStatus.DONE] * 4, [job.failure for job in jobs]
        assert {job.backend_used for job in jobs} == {used}
        produced[layout] = sorted(
            str(path.relative_to(mount / layout)) for job in jobs for path in job.outputs
        )
        for job in jobs:
            assert _jfk_words(job.outputs[0].read_text(encoding="utf-8"))
    assert produced["kept"] == [
        f"{folder}jfk.{fmt}" for folder in ("a/deep/", "a/", "b/", "") for fmt in ("docx", "txt")
    ]
    assert produced["flat"] == [
        f"jfk{number}.{fmt}" for number in (" (1)", " (2)", " (3)", "") for fmt in ("docx", "txt")
    ]
    listing = _files(mount)
    assert not [name for name in listing if "dusty-tmp" in name]
    # Where macOS keeps provenance sidecars (FAT and exFAT on a Mac that tags new
    # files), every new file and folder has one. Only those sidecars may appear.
    sidecars = _sidecars(listing)
    assert not _orphan_sidecars(listing)
    assert (sidecars != []) == sidecars_expected
    assert _work_empty(paths)
    assert _native_children(paths.bin_dir) == []


# P28: read-only volume.


@pytest.mark.parametrize(("fs", "folder_exists"), [("apfs", True), ("exfat", False)])
def test_read_only_volume_fails_every_job_plainly_and_changes_nothing(
    runtime: tuple[RuntimePaths, ModelRegistry],
    volumes: Volumes,
    tmp_path: Path,
    fs: str,
    folder_exists: bool,
) -> None:
    paths, _ = runtime
    sources = [
        _copy("formats/jfk.wav", tmp_path / "in/one.wav"),
        _copy("formats/jfk.mp3", tmp_path / "in/two.mp3"),
    ]
    before = [source.read_bytes() for source in sources]
    prepare = (lambda mount: (mount / "out").mkdir()) if folder_exists else None
    mount = volumes.attach(fs, readonly=True, prepare=prepare)
    listing = _files(mount)
    jobs = [Job(source) for source in sources]
    options = BatchOptions("tiny", mount / "out", formats=("txt", "docx"), backend="metal")
    _run(runtime, jobs, options)
    assert [(job.status, job.failure) for job in jobs] == [
        (JobStatus.FAILED, FailureCode.OUTPUT_UNWRITABLE)
    ] * 2
    assert not any(job.outputs for job in jobs)
    assert _files(mount) == listing
    assert [source.read_bytes() for source in sources] == before
    assert _work_empty(paths)
    assert _native_children(paths.bin_dir) == []


# P28: full volume.


def _fill(mount: Path) -> None:
    """Fill the volume with filler files until no further write succeeds."""
    size, index = 1 << 20, 0
    while size >= 512:
        filler = mount / f"filler{index}.bin"
        try:
            with filler.open("wb") as stream:
                stream.write(bytes(size))
                stream.flush()
                os.fsync(stream.fileno())
            index += 1
        except OSError:
            filler.unlink(missing_ok=True)
            size //= 2


@pytest.mark.parametrize("fs", ["apfs", "fat32"])
def test_full_volume_fails_with_disk_full_and_leaves_no_partial_output(
    runtime: tuple[RuntimePaths, ModelRegistry],
    volumes: Volumes,
    tmp_path: Path,
    fs: str,
) -> None:
    paths, _ = runtime
    mount = volumes.attach(fs)
    (mount / "out").mkdir()
    on_volume = _copy("formats/jfk.mp3", mount / "recordings/clip.mp3")
    local = _copy("formats/jfk.wav", tmp_path / "in/second.wav")
    before = on_volume.read_bytes()
    _fill(mount)
    jobs = [Job(on_volume), Job(local)]
    options = BatchOptions(
        "tiny", mount / "out", formats=("txt", "srt", "json", "docx"), backend="cpu"
    )
    _run(runtime, jobs, options)
    assert [(job.status, job.failure) for job in jobs] == [
        (JobStatus.FAILED, FailureCode.DISK_FULL)
    ] * 2
    assert _files(mount / "out") == []
    assert on_volume.read_bytes() == before
    assert _work_empty(paths)
    assert _native_children(paths.bin_dir) == []


# P28: volumes ejected while a batch runs.


def _when(job: Job, status: JobStatus, action: Callable[[], None]) -> Callable[[Job], None]:
    done: list[bool] = []

    def changed(current: Job) -> None:
        if current is job and current.status == status and not done:
            done.append(True)
            action()

    return changed


def test_output_volume_ejected_during_a_batch_fails_plainly(
    runtime: tuple[RuntimePaths, ModelRegistry], volumes: Volumes, tmp_path: Path
) -> None:
    paths, _ = runtime
    mount = volumes.attach("exfat")
    jobs = [
        Job(_copy("formats/jfk.wav", tmp_path / "in/one.wav")),
        Job(_copy("formats/jfk.mp3", tmp_path / "in/two.mp3")),
    ]
    options = BatchOptions("tiny", mount / "out", formats=("txt", "docx"), backend="metal")
    _run(
        runtime,
        jobs,
        options,
        on_change=_when(jobs[0], JobStatus.TRANSCRIBING, lambda: volumes.detach(mount, eject=True)),
    )
    assert [(job.status, job.failure) for job in jobs] == [
        (JobStatus.FAILED, FailureCode.OUTPUT_UNWRITABLE)
    ] * 2
    assert not mount.exists()
    assert _work_empty(paths)
    assert _native_children(paths.bin_dir) == []


def test_input_volume_ejected_after_decoding_keeps_the_batch_going(
    runtime: tuple[RuntimePaths, ModelRegistry], volumes: Volumes, tmp_path: Path
) -> None:
    paths, _ = runtime
    mount = volumes.attach("apfs")
    jobs = [
        Job(_copy("formats/jfk.wav", mount / "recordings/first.wav")),
        Job(_copy("formats/jfk.mp3", mount / "recordings/second.mp3")),
        Job(_copy("formats/jfk.wav", tmp_path / "in/local.wav")),
    ]
    options = BatchOptions("tiny", tmp_path / "out", formats=("txt",), backend="metal")
    _run(
        runtime,
        jobs,
        options,
        on_change=_when(jobs[0], JobStatus.TRANSCRIBING, lambda: volumes.detach(mount)),
    )
    # The first file was fully decoded into private work before the eject.
    assert [(job.status, job.failure) for job in jobs] == [
        (JobStatus.DONE, None),
        (JobStatus.FAILED, FailureCode.NOT_FOUND),
        (JobStatus.DONE, None),
    ]
    assert _jfk_words((tmp_path / "out/first.txt").read_text(encoding="utf-8"))
    assert _work_empty(paths)
    assert _native_children(paths.bin_dir) == []


@dataclass
class MidDecode:
    jobs: list[Job]
    paused: bool
    children: list[str]
    work_empty: bool
    words: int


def _ffmpeg_pid(executable: Path, wav: str) -> int | None:
    listing = subprocess.run(
        ["/bin/ps", "-A", "-o", "pid=,args="],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    ).stdout
    for line in listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        if command.startswith(str(executable)) and wav in command:
            return int(pid)
    return None


@pytest.fixture(scope="module")
def mid_decode(tmp_path_factory: pytest.TempPathFactory) -> Iterator[MidDecode]:
    """Eject the input volume while FFmpeg is paused partway through decoding it."""
    import dusty.engine.ffmpeg as ffmpeg_module

    base = tmp_path_factory.mktemp("mid-decode")
    runtime = _paths(base)
    paths, _ = runtime
    created = Volumes(base / "images")
    created.folder.mkdir()
    original = ffmpeg_module.run_job_process
    paused: list[bool] = []
    try:
        mount = created.attach("exfat")
        long = _copy("bench/swineherd.mp3", mount / "recordings/long.mp3")
        later = _copy("formats/jfk.wav", mount / "recordings/later.wav")
        local = _copy("formats/jfk.wav", base / "in/local.wav")

        def paused_eject(args: list[str], **kwargs):  # type: ignore[no-untyped-def]
            if str(long) not in args or "pcm_s16le" not in args or paused:
                return original(args, **kwargs)

            def on_poll() -> None:
                if paused:
                    return
                pid = _ffmpeg_pid(Path(args[0]), args[-1])
                if pid is None:
                    return
                paused.append(True)
                os.kill(pid, signal.SIGSTOP)
                try:
                    created.detach(mount)
                finally:
                    os.kill(pid, signal.SIGCONT)

            return original(args, **{**kwargs, "on_poll": on_poll})

        ffmpeg_module.run_job_process = paused_eject
        jobs = [Job(long), Job(later), Job(local)]
        options = BatchOptions("tiny", base / "out", formats=("txt",), backend="metal")
        _run(runtime, jobs, options)
        transcript = base / "out/long.txt"
        words = len(transcript.read_text(encoding="utf-8").split()) if transcript.exists() else 0
        yield MidDecode(
            jobs, bool(paused), _native_children(paths.bin_dir), _work_empty(paths), words
        )
    finally:
        ffmpeg_module.run_job_process = original
        created.close()


def test_input_volume_ejected_mid_decode_leaves_no_children_or_work(
    mid_decode: MidDecode,
) -> None:
    if not mid_decode.paused:
        pytest.skip("FFmpeg finished before it could be paused; nothing was ejected mid-decode")
    jobs = mid_decode.jobs
    assert (jobs[1].status, jobs[1].failure) == (JobStatus.FAILED, FailureCode.NOT_FOUND)
    assert (jobs[2].status, jobs[2].failure) == (JobStatus.DONE, None)
    assert mid_decode.children == []
    assert mid_decode.work_empty


def test_input_volume_ejected_mid_decode_is_not_reported_done(mid_decode: MidDecode) -> None:
    """D-MAC-023: FFmpeg exits 0 after the read error; Dusty still fails the job."""
    if not mid_decode.paused:
        pytest.skip("FFmpeg finished before it could be paused; nothing was ejected mid-decode")
    job = mid_decode.jobs[0]
    assert (job.status, job.failure) == (JobStatus.FAILED, FailureCode.NOT_FOUND)
    assert not job.outputs and mid_decode.words == 0


# P19, P28: Unicode and spaces in folder names on the volume.


@pytest.mark.parametrize("fs", ["apfs", "exfat"])
def test_unicode_and_spaces_on_the_volume_for_inputs_and_outputs(
    runtime: tuple[RuntimePaths, ModelRegistry],
    volumes: Volumes,
    fs: str,
) -> None:
    paths, _ = runtime
    mount = volumes.attach(fs)
    sidecars_expected = _keeps_provenance_sidecars(mount)
    assert not sidecars_expected or fs != "apfs"
    root = mount / "ضبط های جلسه"
    names = ["jfk.wav", "Cafe\u0301 notes/jfk.mp3", "پوشه دوم/re\u0301sume\u0301 2.wav"]
    sources = [
        _copy("formats/jfk.mp3" if name.endswith(".mp3") else "formats/jfk.wav", root / name)
        for name in names
    ]
    before = [source.read_bytes() for source in sources]
    scanned = scan_inputs([root], recursive=True)
    # Where macOS keeps "._" provenance sidecars, they sit next to the copies and
    # folders. The ones next to recordings are skipped, never queued as recordings.
    assert len(scanned.jobs) == 3
    assert scanned.unsupported == (5 if sidecars_expected else 0)
    out = mount / "خروجی نهایی" / "Re\u0301sultats"
    jobs = list(scanned.jobs)
    options = BatchOptions(
        "tiny", out, formats=("txt", "json"), backend="metal", keep_structure=True
    )
    _run(runtime, jobs, options)
    assert [job.status for job in jobs] == [JobStatus.DONE] * 3, [job.failure for job in jobs]

    def nfc(path: Path) -> str:
        return unicodedata.normalize("NFC", str(path))

    produced = sorted(nfc(path.relative_to(out)) for job in jobs for path in job.outputs)
    expected = sorted(
        nfc(Path(name).with_suffix(f".{fmt}")) for name in names for fmt in ("txt", "json")
    )
    assert produced == expected
    for job in jobs:
        assert all(path.is_file() for path in job.outputs)
        assert _jfk_words(job.outputs[0].read_text(encoding="utf-8"))
    listing = _files(mount)
    assert not [name for name in listing if "dusty-tmp" in name]
    assert not _orphan_sidecars(listing)
    assert [source.read_bytes() for source in sources] == before
    assert _work_empty(paths)
