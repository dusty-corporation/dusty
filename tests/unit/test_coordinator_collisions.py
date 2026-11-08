"""Collision decisions and model option refusals in the Coordinator, with fake natives.

The native process runner is replaced at the shim functions in dusty.engine.ffmpeg
and dusty.engine.whisper, so every ffprobe, ffmpeg and whisper-cli start is
recorded. Skip decisions (D-MAC-021 D1) must be made before any of them, and
English-only refusals (D2) before any job runs.
"""

import json
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.core.types import CollisionPolicy
from dusty.engine import binaries, ffmpeg, whisper
from dusty.models import load_manifest
from dusty.queue import Coordinator
from dusty.queue.coordinator import UnsupportedOptions, check_model_options
from dusty.queue.storage import load_batch
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/engine"
CPU_LINES = (FIXTURES / "mac-cpu-full-stderr.txt").read_text().splitlines()
MANIFEST = load_manifest(ROOT / "resources/models.json")
EXISTING = b"existing transcript"


class FakeNative:
    """Answer ffprobe, ffmpeg and whisper-cli calls without starting processes."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_ffmpeg(self, args, **kwargs):
        name = Path(args[0]).name
        self.calls.append("ffprobe" if name.startswith("ffprobe") else "ffmpeg")
        if name.startswith("ffprobe"):
            kwargs["on_stdout"](
                json.dumps({"streams": [{"codec_type": "audio", "duration": "11.0"}]})
            )
        else:
            Path(args[-1]).write_bytes(b"RIFF fake decoded audio")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.01)

    def run_whisper(self, args, **kwargs):
        self.calls.append("whisper")
        for line in CPU_LINES:
            kwargs["on_stderr"](line)
        shutil.copyfile(FIXTURES / "sample-output.json", args[args.index("-of") + 1] + ".json")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.5)


class Registry:
    """The real bundled catalog; model files are never opened by the fakes."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.manifest = MANIFEST

    def model_path(self, model_id: str) -> Path:
        return self.folder / MANIFEST.models[model_id].file_name

    def vad_path(self) -> Path:
        return self.folder / MANIFEST.vad_file_name


@pytest.fixture
def native(monkeypatch: pytest.MonkeyPatch) -> FakeNative:
    fake = FakeNative()
    monkeypatch.setattr(binaries, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(ffmpeg, "run_job_process", fake.run_ffmpeg)
    monkeypatch.setattr(whisper, "run_job_process", fake.run_whisper)
    return fake


@pytest.fixture
def paths(tmp_path: Path) -> RuntimePaths:
    return RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")


def _source(tmp_path: Path, relative: str) -> Path:
    source = tmp_path / "in" / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"RIFF public fixture stand-in")
    return source


def _options(tmp_path: Path, collision: CollisionPolicy, **kwargs) -> BatchOptions:
    settings = {"formats": ("txt",), "backend": "cpu", **kwargs}
    return BatchOptions("tiny", tmp_path / "out", collision=collision, **settings)


def _existing(tmp_path: Path, *names: str) -> None:
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    for name in names:
        (out / name).write_bytes(EXISTING)


def _work_empty(paths: RuntimePaths) -> bool:
    work = paths.user_dir / "work"
    return not work.exists() or not any(work.iterdir())


# D1: skip before any native process


@pytest.mark.parametrize("policy", ["skip", "ask"])
def test_existing_outputs_are_skipped_before_any_native_process(tmp_path, paths, native, policy):
    source = _source(tmp_path, "clip.wav")
    _existing(tmp_path, "clip.txt")
    seen: list[tuple[JobStatus, FailureCode | None]] = []
    job = Job(source, elapsed_sec=42.0)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [job],
        _options(tmp_path, policy),
        vulkan_ok=False,
        on_change=lambda current: seen.append((current.status, current.failure)),
    )
    assert native.calls == []
    assert job.status == JobStatus.SKIPPED
    assert job.failure == FailureCode.OUTPUT_EXISTS_SKIPPED
    assert job.outputs == [] and job.backend_used is None and job.progress == 0.0
    assert job.elapsed_sec < 5
    assert seen == [(JobStatus.SKIPPED, FailureCode.OUTPUT_EXISTS_SKIPPED)]
    assert (tmp_path / "out/clip.txt").read_bytes() == EXISTING
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["clip.txt"]
    assert _work_empty(paths)
    saved = load_batch(paths.user_dir / "state/queue.json")
    assert saved is not None
    assert [(item.status, item.failure) for item in saved[1]] == [
        (JobStatus.SKIPPED, FailureCode.OUTPUT_EXISTS_SKIPPED)
    ]


def test_partial_existing_outputs_also_skip_before_decoding(tmp_path, paths, native):
    source = _source(tmp_path, "clip.wav")
    _existing(tmp_path, "clip.json")
    job = Job(source)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [job], _options(tmp_path, "skip", formats=("txt", "json")), vulkan_ok=False
    )
    assert native.calls == []
    assert job.status == JobStatus.SKIPPED
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["clip.json"]


def test_skip_continues_with_the_next_file(tmp_path, paths, native):
    skipped = _source(tmp_path, "old.wav")
    fresh = _source(tmp_path, "new.wav")
    _existing(tmp_path, "old.txt")
    jobs = [Job(skipped), Job(fresh)]
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        jobs, _options(tmp_path, "skip"), vulkan_ok=False
    )
    assert [job.status for job in jobs] == [JobStatus.SKIPPED, JobStatus.DONE]
    assert native.calls == ["ffprobe", "ffmpeg", "whisper"]
    assert jobs[1].outputs == [tmp_path / "out/new.txt"]
    assert (tmp_path / "out/old.txt").read_bytes() == EXISTING


def test_cancel_current_does_not_leak_past_an_early_skip(tmp_path, paths, native):
    skipped = _source(tmp_path, "old.wav")
    fresh = _source(tmp_path, "new.wav")
    _existing(tmp_path, "old.txt")
    cancel_current = threading.Event()
    cancel_current.set()
    jobs = [Job(skipped), Job(fresh)]
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        jobs, _options(tmp_path, "skip"), vulkan_ok=False, cancel_current=cancel_current
    )
    assert [job.status for job in jobs] == [JobStatus.SKIPPED, JobStatus.DONE]
    assert not cancel_current.is_set()


def test_cancel_all_still_wins_over_skip(tmp_path, paths, native):
    source = _source(tmp_path, "clip.wav")
    _existing(tmp_path, "clip.txt")
    cancel = threading.Event()
    cancel.set()
    job = Job(source)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [job], _options(tmp_path, "skip"), vulkan_ok=False, cancel=cancel
    )
    assert job.status == JobStatus.CANCELLED
    assert native.calls == []


# Unchanged collision behavior


@pytest.mark.parametrize(
    ("policy", "names"),
    [("overwrite", ["clip.txt"]), ("keep_both", ["clip (1).txt", "clip.txt"])],
)
def test_overwrite_and_keep_both_still_run_the_engine(tmp_path, paths, native, policy, names):
    source = _source(tmp_path, "clip.wav")
    _existing(tmp_path, "clip.txt")
    job = Job(source)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [job], _options(tmp_path, policy), vulkan_ok=False
    )
    assert job.status == JobStatus.DONE
    assert native.calls == ["ffprobe", "ffmpeg", "whisper"]
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == names
    assert (tmp_path / "out/clip.txt").read_bytes() != EXISTING or policy == "keep_both"


@pytest.mark.parametrize(
    ("decision", "status", "calls", "names"),
    [
        ("skip", JobStatus.SKIPPED, [], ["clip.txt"]),
        (
            "keep_both",
            JobStatus.DONE,
            ["ffprobe", "ffmpeg", "whisper"],
            ["clip (1).txt", "clip.txt"],
        ),
        ("overwrite", JobStatus.DONE, ["ffprobe", "ffmpeg", "whisper"], ["clip.txt"]),
    ],
)
def test_ask_with_callback_asks_with_the_prior_outputs(
    tmp_path, paths, native, decision, status, calls, names
):
    source = _source(tmp_path, "clip.wav")
    _existing(tmp_path, "clip.txt")
    asked: list[list[Path]] = []
    seen: list[JobStatus] = []
    job = Job(source)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [job],
        _options(tmp_path, "ask"),
        vulkan_ok=False,
        on_collision=lambda current: asked.append(list(current.outputs)) or decision,
        on_change=lambda current: seen.append(current.status),
    )
    assert asked == [[tmp_path / "out/clip.txt"]]
    assert job.status == status
    assert native.calls == calls
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == names
    if decision != "overwrite":
        assert (tmp_path / "out/clip.txt").read_bytes() == EXISTING
    if decision == "skip":
        assert job.failure == FailureCode.OUTPUT_EXISTS_SKIPPED
        assert seen == [JobStatus.SKIPPED]
        assert _work_empty(paths)


def test_ask_answered_skip_for_all_skips_every_file_without_native_calls(tmp_path, paths, native):
    # Same shape as the GUI worker: the first answer is remembered for later files.
    jobs = [Job(_source(tmp_path, "one.wav")), Job(_source(tmp_path, "two.wav"))]
    _existing(tmp_path, "one.txt", "two.txt")
    remembered: list[CollisionPolicy] = []
    asked: list[str] = []

    def answer(current: Job) -> CollisionPolicy:
        if remembered:
            return remembered[0]
        asked.append(current.source.name)
        remembered.append("skip")
        return "skip"

    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        jobs, _options(tmp_path, "ask"), vulkan_ok=False, on_collision=answer
    )
    assert asked == ["one.wav"]
    assert [(job.status, job.failure) for job in jobs] == [
        (JobStatus.SKIPPED, FailureCode.OUTPUT_EXISTS_SKIPPED)
    ] * 2
    assert native.calls == []
    assert _work_empty(paths)


# The real GUI batch worker, answering its collision signal synchronously.


def _worker(tmp_path, paths, jobs):
    pytest.importorskip("PySide6")
    from dusty.app.workers import BatchWorker

    return BatchWorker(paths, Registry(paths.models_dir), jobs, _options(tmp_path, "ask"), False)  # type: ignore[arg-type]


@pytest.mark.parametrize("apply_all", [True, False])
def test_gui_worker_skip_answer_starts_no_native_process(qapp, tmp_path, paths, native, apply_all):
    jobs = [Job(_source(tmp_path, "one.wav")), Job(_source(tmp_path, "two.wav"))]
    _existing(tmp_path, "one.txt", "two.txt")
    worker = _worker(tmp_path, paths, jobs)
    dialogs: list[str] = []

    def dialog(job: Job) -> None:
        dialogs.append(job.source.name)
        worker.choose_collision("skip", apply_all)

    worker.collision.connect(dialog)
    worker.run()
    assert dialogs == (["one.wav"] if apply_all else ["one.wav", "two.wav"])
    assert [job.status for job in jobs] == [JobStatus.SKIPPED, JobStatus.SKIPPED]
    assert native.calls == []
    assert _work_empty(paths)


def test_gui_worker_cancel_all_during_the_dialog_starts_no_native_process(
    qapp, tmp_path, paths, native
):
    jobs = [Job(_source(tmp_path, "one.wav")), Job(_source(tmp_path, "two.wav"))]
    _existing(tmp_path, "one.txt")
    worker = _worker(tmp_path, paths, jobs)
    worker.collision.connect(lambda job: worker.cancel_all.set())
    worker.run()
    assert [job.status for job in jobs] == [JobStatus.CANCELLED, JobStatus.CANCELLED]
    assert native.calls == []
    assert (tmp_path / "out/one.txt").read_bytes() == EXISTING


@pytest.mark.parametrize("policy", ["skip", "ask"])
def test_names_produced_in_this_batch_are_kept_both_not_skipped(tmp_path, paths, native, policy):
    first = _source(tmp_path, "a/clip.wav")
    second = _source(tmp_path, "b/clip.wav")
    jobs = [Job(first), Job(second)]
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        jobs, _options(tmp_path, policy), vulkan_ok=False
    )
    assert [job.status for job in jobs] == [JobStatus.DONE, JobStatus.DONE]
    assert [job.outputs for job in jobs] == [
        [tmp_path / "out/clip.txt"],
        [tmp_path / "out/clip (1).txt"],
    ]
    assert native.calls.count("whisper") == 2


def test_resumed_batch_keeps_both_for_names_finished_before_restart(tmp_path, paths, native):
    first = _source(tmp_path, "a/clip.wav")
    second = _source(tmp_path, "b/clip.wav")
    _existing(tmp_path, "clip.txt")
    done = Job(first, status=JobStatus.DONE, outputs=[tmp_path / "out/clip.txt"])
    remaining = Job(second)
    Coordinator(paths, Registry(paths.models_dir)).run_batch(
        [done, remaining], _options(tmp_path, "skip"), vulkan_ok=False
    )
    assert done.status == JobStatus.DONE
    assert remaining.status == JobStatus.DONE
    assert remaining.outputs == [tmp_path / "out/clip (1).txt"]
    assert native.calls == ["ffprobe", "ffmpeg", "whisper"]


# D2: English-only models accept auto or en only


@pytest.mark.parametrize("language", ["fa", "es", "EN", "english"])
def test_english_only_model_refuses_other_languages_before_any_job(
    tmp_path, paths, native, language
):
    job = Job(_source(tmp_path, "clip.wav"))
    options = BatchOptions("small.en", tmp_path / "out", formats=("txt",), language=language)
    with pytest.raises(ValueError, match="Selected model is English-only") as refused:
        Coordinator(paths, Registry(paths.models_dir)).run_batch([job], options, vulkan_ok=False)
    assert isinstance(refused.value, UnsupportedOptions)
    assert refused.value.code == "LANGUAGE_UNSUPPORTED"
    assert job.status == JobStatus.QUEUED
    assert native.calls == []
    assert not (tmp_path / "out").exists()
    assert not (paths.user_dir / "state/queue.json").exists()


@pytest.mark.parametrize("language", ["auto", "en"])
def test_english_only_model_accepts_auto_and_english(tmp_path, paths, native, language):
    job = Job(_source(tmp_path, "clip.wav"))
    options = BatchOptions(
        "small.en", tmp_path / "out", formats=("txt",), backend="cpu", language=language
    )
    Coordinator(paths, Registry(paths.models_dir)).run_batch([job], options, vulkan_ok=False)
    assert job.status == JobStatus.DONE
    assert native.calls == ["ffprobe", "ffmpeg", "whisper"]


def test_multilingual_models_still_accept_any_language():
    for model in MANIFEST.models.values():
        if not model.english_only:
            check_model_options(model, BatchOptions(model.id, Path("out"), language="fa"))


def test_only_catalog_english_only_models_refuse_a_language():
    refused = set()
    for model in MANIFEST.models.values():
        try:
            check_model_options(model, BatchOptions(model.id, Path("out"), language="fa"))
        except UnsupportedOptions:
            refused.add(model.id)
    assert refused == {item.id for item in MANIFEST.models.values() if item.english_only}
    assert refused == {"small.en"}


def test_translate_refusal_keeps_its_message_and_gains_a_code():
    options = BatchOptions("small.en", Path("out"), language="en", task="translate")
    with pytest.raises(ValueError, match="Selected model cannot translate") as refused:
        check_model_options(MANIFEST.models["small.en"], options)
    assert refused.value.code == "TRANSLATE_UNSUPPORTED"  # type: ignore[attr-defined]
