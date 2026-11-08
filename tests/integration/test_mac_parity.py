"""Headless Mac parity rows through the real Coordinator, native engine and FFmpeg.

Stage a development bin_dir with tools/stage_macos_dev_bin.py and point
DUSTY_BIN_DIR at it and DUSTY_MODELS_DIR at hash verified catalog models.
Tests that need a model other than Tiny skip when that model is absent.

Rows that ask for Metal expect the backend Dusty uses on this Mac (the mac_gpu
fixture): Metal on a real Mac, or the CPU inside a virtual Mac, where Dusty never
starts the Metal engine. Rows about the Metal engine itself skip there.
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.core.types import CollisionPolicy
from dusty.engine.backend import probe_gpu
from dusty.engine.binaries import lifeline_path, whisper_path
from dusty.models import ModelRegistry, load_manifest
from dusty.platform import virtual_mac
from dusty.privacy.logging import configure_logger
from dusty.queue import Coordinator
from dusty.queue.scanning import scan_inputs
from dusty.queue.storage import load_settings
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "tests/fixtures/audio"
FORMATS = ("txt", "srt", "vtt", "json", "docx")
# Spoken JFK reference ends at 10.5 s; ADR 0018 tolerance is 0.5 s.
SPEECH_WINDOWS = ((0.0, 10.5), (300.0, 310.5))
TOLERANCE = 0.5
PERSIAN = re.compile(r"[؀-ۿ]")


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
        and (Path(models_dir) / "ggml-silero-vad.bin").is_file()
    )


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or not _staged(),
    reason="Needs macOS plus a staged DUSTY_BIN_DIR (cpu, metal, lifeline) and DUSTY_MODELS_DIR",
)


@dataclass
class EngineCalls:
    """Arguments and recognized stderr of each real whisper-cli run, kept in memory."""

    args: list[list[str]] = field(default_factory=list)
    stderr: list[list[str]] = field(default_factory=list)


@pytest.fixture
def paths(tmp_path: Path) -> RuntimePaths:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    return RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")


@pytest.fixture
def registry(paths: RuntimePaths) -> ModelRegistry:
    return ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)


@pytest.fixture
def engine_calls(monkeypatch: pytest.MonkeyPatch) -> EngineCalls:
    """Wrap, never replace, the real runner so the native engine still runs."""
    import dusty.engine.whisper as whisper_module

    original = whisper_module.run_job_process
    calls = EngineCalls()

    def recording(args: list[str], **kwargs):  # type: ignore[no-untyped-def]
        calls.args.append(list(args))
        lines: list[str] = []
        calls.stderr.append(lines)
        feed = kwargs.get("on_stderr")

        def tee(line: str) -> None:
            lines.append(line)
            if feed:
                feed(line)

        kwargs["on_stderr"] = tee
        return original(args, **kwargs)

    monkeypatch.setattr(whisper_module, "run_job_process", recording)
    return calls


def _model(registry: ModelRegistry, model_id: str) -> None:
    file_name = registry.manifest.models[model_id].file_name
    if not (registry.directory / file_name).is_file():
        pytest.skip(f"{model_id} is not in DUSTY_MODELS_DIR")


def _inputs(tmp_path: Path, *names: str) -> list[Path]:
    """Copy public fixtures outside managed folders; return the copies."""
    folder = tmp_path / "in"
    copies = []
    for name in names:
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(AUDIO / name, target)
        copies.append(target)
    return copies


def _run(
    paths: RuntimePaths,
    registry: ModelRegistry,
    jobs: list[Job],
    options: BatchOptions,
    *,
    vulkan_ok: bool = True,
    **kwargs,  # type: ignore[no-untyped-def]
) -> list[Job]:
    configure_logger(paths.user_dir)
    return Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=vulkan_ok, **kwargs)


def _log(paths: RuntimePaths) -> str:
    logger = configure_logger(paths.user_dir)
    for handler in logger.handlers:
        handler.flush()
    return (paths.user_dir / "logs/dusty.log").read_text(encoding="utf-8")


def _work_empty(paths: RuntimePaths) -> bool:
    return list((paths.user_dir / "work").iterdir()) == []


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(transcript: dict) -> str:
    return " ".join(segment["text"] for segment in transcript["segments"]).lower()


def _jfk_words(text: str) -> bool:
    text = text.lower()
    return "country" in text and ("americans" in text or "ask not" in text)


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


# P02, P08: Tiny plus VAD on both backends, with truthful backend reporting.


@pytest.mark.parametrize(
    ("backend", "vulkan_ok", "expected"),
    [
        ("cpu", True, "cpu"),
        ("metal", False, "metal"),
        ("auto", True, "metal"),
        ("auto", False, "cpu"),
    ],
)
def test_backend_selection_is_truthful_with_vad_and_threads(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    mac_gpu: SimpleNamespace,
    tmp_path: Path,
    backend: str,
    vulkan_ok: bool,
    expected: str,
) -> None:
    if expected == "metal" and mac_gpu.reason:
        pytest.skip(mac_gpu.reason)
    (source,) = _inputs(tmp_path, "formats/jfk.wav")
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        formats=("json",),
        backend=backend,
        threads=3,
        vad=True,
        language="en",
    )
    (job,) = _run(paths, registry, [Job(source)], options, vulkan_ok=vulkan_ok)
    assert job.status == JobStatus.DONE, job.failure
    assert job.backend_used == expected and not job.gpu_fallback
    exported = _json(tmp_path / "out/jfk.json")
    assert exported["backend"] == expected
    assert _jfk_words(_text(exported))
    (args,) = engine_calls.args
    assert Path(args[0]) == whisper_path(paths.bin_dir, expected).resolve()
    assert args[args.index("-t") + 1] == "3"
    assert ("-ng" in args) == (expected == "cpu")
    assert "--vad" in args and Path(args[args.index("-vm") + 1]).name == "ggml-silero-vad.bin"
    (stderr,) = engine_calls.stderr
    assert any("n_threads = 3" in line for line in stderr)
    metal_selected = any(re.search(r"using MTL[0-9]+ backend", line) for line in stderr)
    assert metal_selected == (expected == "metal")
    assert f"backend={expected}" in _log(paths)
    assert _work_empty(paths)


def test_virtual_mac_uses_the_cpu_without_starting_the_metal_engine(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inside a virtual Mac the Metal engine never starts and jobs run on the CPU at once.

    On GitHub's M1 runners the Metal engine stalled for over an hour before it
    reported anything. On a real Mac this test makes Dusty see a virtual Mac.
    """
    monkeypatch.setattr(virtual_mac, "is_virtual_mac", lambda: True)
    started = time.monotonic()
    assert probe_gpu(paths, registry, refresh=True) is False
    probe = load_settings(paths.user_dir / "settings.json")["backend_probe"]
    assert probe["ok"] is False and probe["unsupported"] is True and probe["virtual_mac"] is True
    assert probe["device_name"] is None
    assert engine_calls.args == []
    (source,) = _inputs(tmp_path, "formats/jfk.wav")
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=("json",), backend="metal", language="en"
    )
    (job,) = _run(paths, registry, [Job(source)], options, vulkan_ok=False)
    assert time.monotonic() - started < 120
    assert job.status == JobStatus.DONE, job.failure
    assert job.backend_used == "cpu" and job.gpu_fallback
    assert _json(tmp_path / "out/jfk.json")["backend"] == "cpu"
    (cpu_args,) = engine_calls.args
    assert Path(cpu_args[0]) == whisper_path(paths.bin_dir, "cpu").resolve()
    assert "-ng" in cpu_args
    assert "backend=cpu" in _log(paths)
    assert _native_children(paths.bin_dir) == []
    assert _work_empty(paths)


# P06, P07: VAD off by default; hints passed as one argument and never logged.


def test_vad_default_off_and_hints_are_one_argument_not_logged(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    mac_gpu: SimpleNamespace,
    tmp_path: Path,
) -> None:
    (source,) = _inputs(tmp_path, "formats/jfk.wav")
    hints = "CANARYHINT Kennedy, Project Stardust, XYZ"
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=("txt",), backend="metal", prompt=hints
    )
    assert options.vad is False
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    # One run: on Metal, or inside a virtual Mac on the CPU without starting Metal.
    (args,) = engine_calls.args
    assert ("-ng" in args) == (mac_gpu.backend == "cpu")
    assert "--vad" not in args and "-vm" not in args
    assert args.count(hints) == 1 and args[args.index("--prompt") + 1] == hints
    assert _jfk_words((tmp_path / "out/jfk.txt").read_text(encoding="utf-8"))
    log = _log(paths)
    assert "CANARYHINT" not in log and "Stardust" not in log and "/Users/" not in log
    assert _work_empty(paths)


def test_vad_keeps_timestamps_inside_speech_windows(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path
) -> None:
    (source,) = _inputs(tmp_path, "vad/mostly-silence-10min.m4a")
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        formats=("json", "srt"),
        backend="metal",
        language="en",
        vad=True,
    )
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    assert 599 <= job.duration_sec <= 601
    segments = _json(tmp_path / "out/mostly-silence-10min.json")["segments"]
    assert len(segments) == len(SPEECH_WINDOWS)
    for segment, (start, end) in zip(segments, SPEECH_WINDOWS, strict=True):
        assert abs(segment["start"] - start) <= TOLERANCE
        assert abs(segment["end"] - end) <= TOLERANCE
        assert "americans" in segment["text"].lower()
    assert _work_empty(paths)


# P03, P04, P05: languages, translation and model restrictions.


@pytest.mark.parametrize("language", ["auto", "en"])
def test_english_auto_and_selected_language(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    tmp_path: Path,
    language: str,
) -> None:
    (source,) = _inputs(tmp_path, "formats/jfk.m4a")
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=("json",), backend="metal", language=language
    )
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    assert engine_calls.args[0][engine_calls.args[0].index("-l") + 1] == language
    exported = _json(tmp_path / "out/jfk.json")
    assert exported["language"] == "en" and _jfk_words(_text(exported))


# D-MAC-021 D2: English-only models accept auto or en only.
@pytest.mark.parametrize("language", ["fa", "de"])
def test_english_only_model_refuses_other_languages_before_any_work(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    tmp_path: Path,
    language: str,
) -> None:
    (source,) = _inputs(tmp_path, "translate/rubaiyat-fa.wav")
    options = BatchOptions(
        "small.en", tmp_path / "out", formats=("json",), backend="metal", language=language
    )
    job = Job(source)
    with pytest.raises(ValueError, match="Selected model is English-only"):
        Coordinator(paths, registry).run_batch([job], options, vulkan_ok=True)
    assert job.status == JobStatus.QUEUED
    assert engine_calls.args == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("model_id", ["small.en", "large-v3-turbo-q8_0"])
def test_models_without_translation_are_refused_before_any_work(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    tmp_path: Path,
    model_id: str,
) -> None:
    (source,) = _inputs(tmp_path, "translate/rubaiyat-fa.wav")
    options = BatchOptions(
        model_id,
        tmp_path / "out",
        formats=("txt",),
        backend="metal",
        language="fa",
        task="translate",
    )
    job = Job(source)
    with pytest.raises(ValueError, match="cannot translate"):
        Coordinator(paths, registry).run_batch([job], options, vulkan_ok=True)
    assert job.status == JobStatus.QUEUED
    assert engine_calls.args == []
    assert not (tmp_path / "out").exists()


def test_persian_transcribe_auto_detects_and_docx_is_rtl(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path
) -> None:
    _model(registry, "small")
    (source,) = _inputs(tmp_path, "translate/rubaiyat-fa.wav")
    options = BatchOptions(
        "small", tmp_path / "out", formats=("json", "docx", "txt"), backend="metal", language="auto"
    )
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    exported = _json(tmp_path / "out/rubaiyat-fa.json")
    assert exported["language"] == "fa"
    assert len(PERSIAN.findall(_text(exported))) >= 20
    text = (tmp_path / "out/rubaiyat-fa.txt").read_text(encoding="utf-8")
    assert len(PERSIAN.findall(text)) >= 20
    with zipfile.ZipFile(tmp_path / "out/rubaiyat-fa.docx") as archive:
        xml = archive.read("word/document.xml")
    ElementTree.fromstring(xml)
    assert b"<w:bidi/>" in xml and b"<w:rtl/>" in xml and b'w:cs="Arial"' in xml


def test_persian_translate_to_english(
    paths: RuntimePaths, registry: ModelRegistry, engine_calls: EngineCalls, tmp_path: Path
) -> None:
    _model(registry, "small")
    (source,) = _inputs(tmp_path, "translate/rubaiyat-fa.wav")
    options = BatchOptions(
        "small",
        tmp_path / "out",
        formats=("json",),
        backend="metal",
        language="fa",
        task="translate",
    )
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    assert "-tr" in engine_calls.args[0]
    exported = _json(tmp_path / "out/rubaiyat-fa.en.json")
    assert exported["task"] == "translate"
    translated = _text(exported)
    assert not PERSIAN.search(translated)
    words = set(re.findall(r"[a-z]+", translated))
    assert len(words & {"who", "you", "your", "the", "is", "and", "was", "it", "in", "to"}) >= 3


# P09, P12: every format decodes; bad files fail with the right code; batch continues.


def test_every_format_fixture_decodes_and_transcribes(
    paths: RuntimePaths, registry: ModelRegistry, mac_gpu: SimpleNamespace, tmp_path: Path
) -> None:
    long_path = next((AUDIO / "long-path").rglob("jfk.m4a")).relative_to(AUDIO)
    names = sorted(
        str(path.relative_to(AUDIO)) for path in (AUDIO / "formats").iterdir() if path.is_file()
    )
    copies = _inputs(tmp_path, *names, str(long_path))
    scanned = scan_inputs([tmp_path / "in"], recursive=True)
    assert scanned.unsupported == 0 and len(scanned.jobs) == len(copies) == 19
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        formats=("txt",),
        backend="metal",
        language="en",
        keep_structure=True,
    )
    jobs = _run(paths, registry, list(scanned.jobs), options)
    for job in jobs:
        assert job.status == JobStatus.DONE, (job.source.name, job.failure)
        assert job.backend_used == mac_gpu.backend
        (output,) = job.outputs
        assert _jfk_words(output.read_text(encoding="utf-8")), job.source.name
    assert (tmp_path / "out/formats/تست ضبط.txt").is_file()
    assert (tmp_path / "out" / long_path.parent / "jfk.txt").is_file()
    assert _work_empty(paths)


def test_mixed_batch_continues_past_bad_files(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path
) -> None:
    good, corrupt, empty, silent, other = _inputs(
        tmp_path,
        "formats/jfk.wav",
        "bad/corrupt.mp3",
        "bad/zero-byte.mp3",
        "bad/no-audio.mp4",
        "formats/jfk.ogg",
    )
    jobs = [
        Job(good),
        Job(corrupt),
        Job(empty),
        Job(tmp_path / "in/missing.wav"),
        Job(silent),
        Job(other),
    ]
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=("txt", "json"), backend="metal", language="en"
    )
    _run(paths, registry, jobs, options)
    assert [job.status for job in jobs] == [
        JobStatus.DONE,
        JobStatus.FAILED,
        JobStatus.FAILED,
        JobStatus.FAILED,
        JobStatus.FAILED,
        JobStatus.DONE,
    ]
    assert [job.failure for job in jobs] == [
        None,
        FailureCode.DECODE_ERROR,
        FailureCode.EMPTY_FILE,
        FailureCode.NOT_FOUND,
        FailureCode.NO_AUDIO,
        None,
    ]
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == [
        "jfk (1).json",
        "jfk (1).txt",
        "jfk.json",
        "jfk.txt",
    ]
    assert _work_empty(paths)


# P16, P17: all five formats are structurally valid.


TIMESTAMP = r"\d{2}:\d{2}:\d{2}[,.]\d{3}"


def _cue_times(text: str, separator: str) -> list[tuple[float, float]]:
    pattern = (
        rf"^(\d{{2}}):(\d{{2}}):(\d{{2}}){separator}(\d{{3}}) --> "
        rf"(\d{{2}}):(\d{{2}}):(\d{{2}}){separator}(\d{{3}})$"
    )
    times = []
    for match in re.finditer(pattern, text, flags=re.MULTILINE):
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(value) for value in match.groups())
        times.append((h1 * 3600 + m1 * 60 + s1 + ms1 / 1000, h2 * 3600 + m2 * 60 + s2 + ms2 / 1000))
    return times


def _monotonic(times: list[tuple[float, float]]) -> bool:
    return all(start <= end for start, end in times) and all(
        earlier[1] <= later[0] + 1e-9 for earlier, later in pairwise(times)
    )


def test_all_formats_are_valid(
    paths: RuntimePaths, registry: ModelRegistry, mac_gpu: SimpleNamespace, tmp_path: Path
) -> None:
    (source,) = _inputs(tmp_path, "vad/mostly-silence-10min.m4a")
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=FORMATS, backend="metal", language="en", vad=True
    )
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.DONE, job.failure
    out = tmp_path / "out"
    stem = "mostly-silence-10min"
    raw = {fmt: (out / f"{stem}.{fmt}").read_bytes() for fmt in FORMATS}
    for fmt in ("txt", "srt", "vtt"):
        raw[fmt].decode("utf-8")
        assert b"\r\n" in raw[fmt] and b"\n" not in raw[fmt].replace(b"\r\n", b"")
    srt = raw["srt"].decode("utf-8")
    blocks = [block for block in srt.split("\r\n\r\n") if block.strip()]
    assert [block.split("\r\n")[0] for block in blocks] == [
        str(n) for n in range(1, len(blocks) + 1)
    ]
    srt_times = _cue_times(srt.replace("\r\n", "\n"), ",")
    assert len(srt_times) == len(blocks) >= 2 and _monotonic(srt_times)
    assert any(start >= 299.5 for start, _ in srt_times)
    vtt = raw["vtt"].decode("utf-8")
    assert vtt.startswith("WEBVTT\r\n\r\n")
    vtt_times = _cue_times(vtt.replace("\r\n", "\n"), r"\.")
    assert vtt_times == srt_times
    exported = json.loads(raw["json"])
    assert set(exported) == {
        "schema",
        "schema_version",
        "app_version",
        "model_id",
        "backend",
        "task",
        "language",
        "duration_sec",
        "source_file_name",
        "created_utc",
        "segments",
    }
    assert exported["schema"] == "dusty.transcript" and exported["schema_version"] == 1
    assert exported["source_file_name"] == source.name
    assert exported["backend"] == mac_gpu.backend
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", exported["created_utc"])
    starts = [segment["start"] for segment in exported["segments"]]
    assert starts == sorted(starts)
    assert [segment["index"] for segment in exported["segments"]] == list(range(len(starts)))
    assert str(tmp_path) not in raw["json"].decode("utf-8")
    with zipfile.ZipFile(io.BytesIO(raw["docx"])) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= names
        for name in names:
            ElementTree.fromstring(archive.read(name))
        document = archive.read("word/document.xml").decode("utf-8")
        assert "[00:00:00]" in document and "[00:05:00]" in document
        assert str(tmp_path) not in document and "<dc:creator" not in archive.read(
            "docProps/core.xml"
        ).decode("utf-8")
    assert _jfk_words(raw["txt"].decode("utf-8"))


# P18: collision policies with pre-existing outputs; sources never change.


@pytest.mark.parametrize("policy", ["skip", "overwrite", "keep_both"])
def test_collision_policies_with_existing_outputs(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path, policy: CollisionPolicy
) -> None:
    (source,) = _inputs(tmp_path, "formats/jfk.flac")
    original = source.read_bytes()
    out = tmp_path / "out"
    out.mkdir()
    for fmt in ("txt", "json"):
        (out / f"jfk.{fmt}").write_bytes(b"existing transcript")
    options = BatchOptions("tiny", out, formats=("txt", "json"), backend="metal", collision=policy)
    (job,) = _run(paths, registry, [Job(source)], options)
    names = sorted(path.name for path in out.iterdir())
    if policy == "skip":
        assert job.status == JobStatus.SKIPPED
        assert job.failure == FailureCode.OUTPUT_EXISTS_SKIPPED
        assert names == ["jfk.json", "jfk.txt"]
        assert (out / "jfk.txt").read_bytes() == b"existing transcript"
    elif policy == "overwrite":
        assert job.status == JobStatus.DONE
        assert names == ["jfk.json", "jfk.txt"]
        assert _jfk_words((out / "jfk.txt").read_text(encoding="utf-8"))
        assert _json(out / "jfk.json")["model_id"] == "tiny"
    else:
        assert job.status == JobStatus.DONE
        assert names == ["jfk (1).json", "jfk (1).txt", "jfk.json", "jfk.txt"]
        assert (out / "jfk.txt").read_bytes() == b"existing transcript"
        assert _jfk_words((out / "jfk (1).txt").read_text(encoding="utf-8"))
    assert source.read_bytes() == original
    assert not list(out.glob("*.dusty-tmp"))
    assert _work_empty(paths)


# D-MAC-021 D1: skip, or ask with no one to answer, decides before decoding.
@pytest.mark.parametrize("policy", ["skip", "ask"])
def test_skip_policy_does_not_run_the_engine_for_existing_outputs(
    paths: RuntimePaths,
    registry: ModelRegistry,
    engine_calls: EngineCalls,
    tmp_path: Path,
    policy: CollisionPolicy,
) -> None:
    (source,) = _inputs(tmp_path, "formats/jfk.wav")
    out = tmp_path / "out"
    out.mkdir()
    (out / "jfk.txt").write_bytes(b"existing transcript")
    options = BatchOptions("tiny", out, formats=("txt",), backend="metal", collision=policy)
    (job,) = _run(paths, registry, [Job(source)], options)
    assert job.status == JobStatus.SKIPPED
    assert job.failure == FailureCode.OUTPUT_EXISTS_SKIPPED
    assert (out / "jfk.txt").read_bytes() == b"existing transcript"
    assert engine_calls.args == []
    assert job.backend_used is None and job.duration_sec == 0.0
    assert _work_empty(paths)


# P19: same folder, selected folder and keep structure with duplicate basenames.


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "in"
    for relative in ("jfk.wav", "a/jfk.wav", "a/deep/jfk.mp3", "b/jfk.wav"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(AUDIO / "formats" / Path(relative).name, target)
    return root


@pytest.mark.parametrize("layout", ["selected", "keep_structure", "same_folder"])
def test_output_layouts_with_duplicate_basenames(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path, layout: str
) -> None:
    root = _tree(tmp_path)
    scanned = scan_inputs([root], recursive=True)
    assert len(scanned.jobs) == 4
    out = tmp_path / "out"
    options = BatchOptions(
        "tiny",
        None if layout == "same_folder" else out,
        formats=("txt",),
        backend="metal",
        same_folder=layout == "same_folder",
        keep_structure=layout == "keep_structure",
    )
    jobs = _run(paths, registry, list(scanned.jobs), options)
    assert all(job.status == JobStatus.DONE for job in jobs), [job.failure for job in jobs]
    produced = sorted(str(path.relative_to(tmp_path)) for job in jobs for path in job.outputs)
    if layout == "selected":
        assert produced == ["out/jfk (1).txt", "out/jfk (2).txt", "out/jfk (3).txt", "out/jfk.txt"]
    elif layout == "keep_structure":
        assert produced == ["out/a/deep/jfk.txt", "out/a/jfk.txt", "out/b/jfk.txt", "out/jfk.txt"]
    else:
        assert produced == ["in/a/deep/jfk.txt", "in/a/jfk.txt", "in/b/jfk.txt", "in/jfk.txt"]
        assert not out.exists()
    for job in jobs:
        assert _jfk_words(job.outputs[0].read_text(encoding="utf-8"))
    assert _work_empty(paths)


# P14: cancel current and cancel all during a Metal run.


@pytest.fixture
def long_source(tmp_path: Path) -> Iterator[Path]:
    (source,) = _inputs(tmp_path, "bench/swineherd.mp3")
    yield source


def _cancel_once_transcribing(
    jobs: list[Job], event: threading.Event, seen: list[float], running: list[str], bin_dir: Path
):
    def changed(job: Job) -> None:
        if (
            job is jobs[0]
            and job.status == JobStatus.TRANSCRIBING
            and job.progress > 0
            and not seen
        ):
            # Prove the process check can see the live engine before cancelling.
            running.extend(_native_children(bin_dir))
            seen.append(time.monotonic())
            event.set()

    return changed


@pytest.mark.parametrize("scope", ["current", "all"])
@pytest.mark.usefixtures("metal_gpu")
def test_cancel_during_metal_run_leaves_no_children_or_work(
    paths: RuntimePaths, registry: ModelRegistry, tmp_path: Path, long_source: Path, scope: str
) -> None:
    (short,) = _inputs(tmp_path, "formats/jfk.wav")
    jobs = [Job(long_source), Job(short)]
    event = threading.Event()
    seen: list[float] = []
    running: list[str] = []
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=("txt", "docx"), backend="metal", language="en"
    )
    kwargs = {"cancel_current": event} if scope == "current" else {"cancel": event}
    _run(
        paths,
        registry,
        jobs,
        options,
        on_change=_cancel_once_transcribing(jobs, event, seen, running, paths.bin_dir),
        **kwargs,
    )
    returned = time.monotonic()
    assert seen, "Cancellation must happen during native transcription"
    assert any(line.endswith("/metal/whisper-cli") for line in running)
    assert any(line.endswith("/lifeline/dusty-lifeline") for line in running)
    assert returned - seen[0] < 10
    assert jobs[0].status == JobStatus.CANCELLED and not jobs[0].outputs
    assert jobs[0].failure is None
    if scope == "current":
        assert jobs[1].status == JobStatus.DONE and not event.is_set()
        assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["jfk.docx", "jfk.txt"]
    else:
        assert jobs[1].status == JobStatus.CANCELLED
        assert not (tmp_path / "out").exists() or not list((tmp_path / "out").iterdir())
    assert _native_children(paths.bin_dir) == []
    assert _work_empty(paths)


# P31: a guarded batch never needs Python networking.


def test_guarded_batch_makes_no_python_network_attempt(
    mac_gpu: SimpleNamespace, tmp_path: Path
) -> None:
    (source,) = _inputs(tmp_path, "formats/jfk.mp3")
    appdata = tmp_path / "appdata-guarded"
    script = (
        "import sys\n"
        "from dusty.privacy.network_guard import install_guard\n"
        "install_guard()\n"
        "from dusty import devcli\n"
        "sys.exit(devcli.main(sys.argv[1:]))\n"
    )
    environment = {
        **os.environ,
        "LOCALAPPDATA": str(appdata),
        "PYTHONPATH": str(ROOT / "src"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            "transcribe",
            str(source),
            "--model",
            "tiny",
            "--backend",
            "auto",
            "--format",
            "txt",
            "--format",
            "json",
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        env=environment,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-500:]
    assert "done OK" in result.stdout
    log = (appdata / "Dusty/logs/dusty.log").read_text(encoding="utf-8")
    assert "network_blocked" not in log
    # Automatic runs its own GPU check, so it chooses what the mac_gpu check found.
    assert f"backend={mac_gpu.backend}" in log
    assert _json(tmp_path / "out/jfk.json")["backend"] == mac_gpu.backend
