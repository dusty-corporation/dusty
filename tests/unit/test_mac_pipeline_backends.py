"""Backend selection, program paths and GPU retry on both platforms, with fake natives.

The native process runner is replaced at the shim functions in dusty.engine.ffmpeg
and dusty.engine.whisper, so argument building, stderr parsing, JSON parsing,
export and work cleanup are the real code. Recorded Mac stderr comes from the
pinned whisper.cpp CPU and Metal builds with path lines removed.
"""

import hashlib
import json
import logging
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine import binaries, ffmpeg, whisper
from dusty.engine.whisper import EngineError
from dusty.privacy.logging import RedactionFilter, configure_logger
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/engine"
METAL_LINES = (FIXTURES / "mac-metal-full-stderr.txt").read_text().splitlines()
MAC_CPU_LINES = (FIXTURES / "mac-cpu-full-stderr.txt").read_text().splitlines()
VULKAN_LINES = [
    "ggml_vulkan: 0 = Intel(R) Iris(R) Xe Graphics (Intel driver)",
    "whisper_backend_init_gpu: using Vulkan0 backend",
    "whisper_print_progress_callback: progress = 100%",
]
METAL_FAILURE = "ggml_metal_synchronize: error: command buffer 0 failed with status 5"
FORMATS = ("txt", "srt", "vtt", "json", "docx")


def _virtual_gpu(line: str) -> str:
    """The recorded M2 report as Apple's paravirtual GPU on GitHub's Mac runners gives it."""
    if line.startswith("ggml_metal_device_init: GPU name:"):
        return line.replace("(Apple M2)", "(Apple Paravirtual device)")
    if line.startswith("ggml_metal_device_init: simdgroup "):
        return line.replace("= true", "= false")
    return line


VIRTUAL_GPU_LINES = [_virtual_gpu(line) for line in METAL_LINES]


class FakeNative:
    """Answer ffprobe, ffmpeg and whisper-cli calls without starting processes."""

    def __init__(self, outcomes: dict[str, list[dict]] | None = None):
        self.outcomes = outcomes or {}
        self.ffmpeg_calls: list[list[str]] = []
        self.whisper_calls: list[list[str]] = []
        # Whether the engine was asked to stop once its stderr was read, and
        # the time limit each run was given.
        self.stop_requested: list[bool] = []
        self.whisper_timeouts: list[float | None] = []

    def run_ffmpeg(self, args, **kwargs):
        self.ffmpeg_calls.append(list(args))
        if Path(args[0]).name.startswith("ffprobe"):
            kwargs["on_stdout"](
                json.dumps({"streams": [{"codec_type": "audio", "duration": "11.0"}]})
            )
        else:
            Path(args[-1]).write_bytes(b"RIFF fake decoded audio")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.01)

    def run_whisper(self, args, **kwargs):
        self.whisper_calls.append(list(args))
        backend = Path(args[0]).parent.name
        default = {"lines": MAC_CPU_LINES if backend == "cpu" else METAL_LINES}
        outcome = (
            self.outcomes.get(backend, [default]).pop(0) if backend in self.outcomes else (default)
        )
        for line in outcome.get("lines", ()):
            kwargs["on_stderr"](line)
        stop = kwargs.get("cancel")
        self.stop_requested.append(stop is not None and stop.is_set())
        self.whisper_timeouts.append(kwargs.get("timeout_sec"))
        if kwargs.get("on_poll"):
            kwargs["on_poll"]()
        if outcome.get("set_cancel"):
            outcome["set_cancel"].set()
        exit_code = outcome.get("exit_code", 0)
        if not exit_code and not outcome.get("cancelled"):
            stem = args[args.index("-of") + 1]
            shutil.copyfile(FIXTURES / "sample-output.json", stem + ".json")
        return SimpleNamespace(
            cancelled=outcome.get("cancelled", False), exit_code=exit_code, elapsed_sec=0.5
        )

    @property
    def whisper_programs(self) -> list[Path]:
        return [Path(call[0]) for call in self.whisper_calls]


class StubRegistry:
    def __init__(self, folder: Path):
        self.folder = folder
        self.manifest = SimpleNamespace(models={"tiny": SimpleNamespace()})

    def model_path(self, model_id: str) -> Path:
        return self.folder / f"ggml-{model_id}.bin"

    def vad_path(self) -> Path:
        return self.folder / "ggml-silero-vad.bin"


@pytest.fixture
def platform(monkeypatch):
    def select(name: str) -> None:
        monkeypatch.setattr(binaries, "sys", SimpleNamespace(platform=name))

    return select


@pytest.fixture
def native(monkeypatch):
    def install(outcomes: dict[str, list[dict]] | None = None) -> FakeNative:
        fake = FakeNative(outcomes)
        monkeypatch.setattr(ffmpeg, "run_job_process", fake.run_ffmpeg)
        monkeypatch.setattr(whisper, "run_job_process", fake.run_whisper)
        return fake

    return install


def _setup(tmp_path: Path) -> tuple[RuntimePaths, StubRegistry, Job]:
    paths = RuntimePaths(
        tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "user"
    )
    source = tmp_path / "input/CANARY_PATIENT.wav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"RIFF public fixture stand-in")
    return paths, StubRegistry(paths.models_dir), Job(source)


def _run(tmp_path, options_backend="auto", *, vulkan_ok=True, formats=("json",), cancel=None):
    paths, registry, job = _setup(tmp_path)
    options = BatchOptions(
        "tiny", tmp_path / "out", formats=formats, backend=options_backend, prompt="CANARYHINT"
    )
    Coordinator(paths, registry).run_batch([job], options, vulkan_ok=vulkan_ok, cancel=cancel)
    return paths, job


def _exported_backend(tmp_path: Path) -> str:
    return json.loads((tmp_path / "out/CANARY_PATIENT.json").read_text("utf-8"))["backend"]


# Program path helpers


def test_windows_program_paths_are_identical_to_legacy_strings(tmp_path):
    bin_dir = tmp_path / "bin"
    assert binaries.gpu_backend("win32") == "vulkan"
    assert binaries.ffprobe_path(bin_dir, "win32") == bin_dir / "ffmpeg/ffprobe.exe"
    assert binaries.ffmpeg_path(bin_dir, "win32") == bin_dir / "ffmpeg/ffmpeg.exe"
    assert binaries.whisper_path(bin_dir, "vulkan", "win32") == bin_dir / "vulkan/whisper-cli.exe"
    assert binaries.whisper_path(bin_dir, "cpu", "win32") == bin_dir / "cpu/whisper-cli.exe"


def test_mac_program_paths_have_no_suffix(tmp_path):
    bin_dir = tmp_path / "bin"
    assert binaries.gpu_backend("darwin") == "metal"
    assert binaries.ffprobe_path(bin_dir, "darwin") == bin_dir / "ffmpeg/ffprobe"
    assert binaries.ffmpeg_path(bin_dir, "darwin") == bin_dir / "ffmpeg/ffmpeg"
    assert binaries.whisper_path(bin_dir, "metal", "darwin") == bin_dir / "metal/whisper-cli"
    assert binaries.whisper_path(bin_dir, "cpu", "darwin") == bin_dir / "cpu/whisper-cli"
    assert binaries.lifeline_path(bin_dir) == bin_dir / "lifeline/dusty-lifeline"


# Coordinator on macOS


def test_mac_gpu_run_uses_metal_without_ng_and_exports_truthfully(tmp_path, platform, native):
    platform("darwin")
    fake = native()
    paths, registry, job = _setup(tmp_path)
    logger = configure_logger(paths.user_dir)
    options = BatchOptions("tiny", tmp_path / "out", formats=FORMATS, prompt="CANARYHINT")
    Coordinator(paths, registry).run_batch([job], options, vulkan_ok=True)
    assert job.status == JobStatus.DONE and job.failure is None
    assert job.backend_used == "metal" and not job.gpu_fallback
    assert fake.whisper_programs == [(paths.bin_dir / "metal/whisper-cli").resolve()]
    assert "-ng" not in fake.whisper_calls[0]
    assert [Path(call[0]) for call in fake.ffmpeg_calls] == [
        (paths.bin_dir / "ffmpeg/ffprobe").resolve(),
        (paths.bin_dir / "ffmpeg/ffmpeg").resolve(),
    ]
    assert sorted(path.suffix for path in job.outputs) == sorted(f".{fmt}" for fmt in FORMATS)
    assert _exported_backend(tmp_path) == "metal"
    assert list((paths.user_dir / "work").iterdir()) == []
    for handler in logger.handlers:
        handler.flush()
    log = (paths.user_dir / "logs/dusty.log").read_text("utf-8")
    assert "backend=metal" in log
    assert "CANARY" not in log


@pytest.mark.parametrize(("requested", "vulkan_ok"), [("cpu", True), ("auto", False)])
def test_mac_cpu_run_uses_cpu_program_with_ng(tmp_path, platform, native, requested, vulkan_ok):
    platform("darwin")
    fake = native()
    paths, job = _run(tmp_path, requested, vulkan_ok=vulkan_ok)
    assert job.status == JobStatus.DONE and job.backend_used == "cpu"
    assert fake.whisper_programs == [(paths.bin_dir / "cpu/whisper-cli").resolve()]
    assert "-ng" in fake.whisper_calls[0]
    assert _exported_backend(tmp_path) == "cpu"


@pytest.mark.parametrize("requested", ["metal", "vulkan"])
def test_explicit_gpu_request_runs_the_platform_gpu_backend(tmp_path, platform, native, requested):
    platform("darwin")
    fake = native()
    paths, job = _run(tmp_path, requested, vulkan_ok=False)
    assert fake.whisper_programs == [(paths.bin_dir / "metal/whisper-cli").resolve()]
    assert job.backend_used == "metal" and _exported_backend(tmp_path) == "metal"


@pytest.mark.parametrize(
    "metal_outcome",
    [
        {"lines": MAC_CPU_LINES},  # Metal requested, but stderr shows no GPU selected.
        {"lines": [line for line in METAL_LINES if "using MTL0" not in line]},
        {"lines": METAL_LINES + [METAL_FAILURE]},  # Exit 0 with a known Metal failure.
        {"lines": METAL_LINES[:10] + [METAL_FAILURE], "exit_code": 1},
    ],
)
def test_metal_failure_retries_on_cpu_exactly_once(tmp_path, platform, native, metal_outcome):
    platform("darwin")
    fake = native({"metal": [metal_outcome]})
    paths, job = _run(tmp_path)
    assert fake.whisper_programs == [
        (paths.bin_dir / "metal/whisper-cli").resolve(),
        (paths.bin_dir / "cpu/whisper-cli").resolve(),
    ]
    assert "-ng" not in fake.whisper_calls[0] and "-ng" in fake.whisper_calls[1]
    assert job.status == JobStatus.DONE
    assert job.backend_used == "cpu" and job.gpu_fallback
    assert _exported_backend(tmp_path) == "cpu"
    assert list((paths.user_dir / "work").iterdir()) == []


@pytest.mark.parametrize(
    ("cpu_outcome", "failure"),
    [
        ({"lines": MAC_CPU_LINES[:5], "exit_code": 1}, FailureCode.ENGINE_ERROR),
        ({"lines": [METAL_FAILURE], "exit_code": 1}, FailureCode.GPU_ERROR),
    ],
)
def test_failed_cpu_retry_is_not_retried_again(tmp_path, platform, native, cpu_outcome, failure):
    platform("darwin")
    fake = native({"metal": [{"lines": [METAL_FAILURE], "exit_code": 1}], "cpu": [cpu_outcome]})
    paths, job = _run(tmp_path)
    assert len(fake.whisper_calls) == 2
    assert job.status == JobStatus.FAILED and job.failure == failure
    assert not (tmp_path / "out/CANARY_PATIENT.json").exists()
    assert list((paths.user_dir / "work").iterdir()) == []


def test_non_gpu_engine_failure_is_not_retried(tmp_path, platform, native):
    platform("darwin")
    fake = native({"metal": [{"lines": METAL_LINES[:20], "exit_code": 3}]})
    _paths, job = _run(tmp_path)
    assert len(fake.whisper_calls) == 1
    assert job.status == JobStatus.FAILED and job.failure == FailureCode.ENGINE_ERROR


@pytest.mark.parametrize("cancelled_result", [True, False])
def test_no_cpu_retry_after_cancel(tmp_path, platform, native, cancelled_result):
    platform("darwin")
    cancel = threading.Event()
    outcome = {"lines": [METAL_FAILURE], "set_cancel": cancel}
    outcome.update({"cancelled": True} if cancelled_result else {"exit_code": 1})
    fake = native({"metal": [outcome]})
    paths, job = _run(tmp_path, cancel=cancel)
    assert len(fake.whisper_calls) == 1
    assert job.status in {JobStatus.CANCELLED, JobStatus.FAILED}
    if cancelled_result:
        assert job.status == JobStatus.CANCELLED and job.failure is None
    else:
        assert job.failure == FailureCode.GPU_ERROR
    assert list((paths.user_dir / "work").iterdir()) == []


@pytest.mark.parametrize(("requested", "vulkan_ok"), [("metal", False), ("auto", True)])
def test_gpu_without_the_metal_features_is_stopped_and_the_job_runs_on_cpu(
    tmp_path, platform, native, requested, vulkan_ok
):
    """GitHub's virtual Macs report a GPU without simdgroup support; M1 hosts stall on it."""
    platform("darwin")
    # The runner reports a stopped engine as cancelled and leaves no output.
    fake = native({"metal": [{"lines": VIRTUAL_GPU_LINES, "cancelled": True}]})
    paths, job = _run(tmp_path, requested, vulkan_ok=vulkan_ok)
    assert fake.stop_requested == [True, False]
    assert fake.whisper_programs == [
        (paths.bin_dir / "metal/whisper-cli").resolve(),
        (paths.bin_dir / "cpu/whisper-cli").resolve(),
    ]
    assert job.status == JobStatus.DONE and job.failure is None
    assert job.backend_used == "cpu" and job.gpu_fallback
    assert _exported_backend(tmp_path) == "cpu"
    assert list((paths.user_dir / "work").iterdir()) == []


def test_metal_failure_stops_the_engine_at_once_and_retries_on_cpu(tmp_path, platform, native):
    platform("darwin")
    fake = native({"metal": [{"lines": METAL_LINES[:20] + [METAL_FAILURE], "cancelled": True}]})
    _paths, job = _run(tmp_path)
    assert fake.stop_requested == [True, False]
    assert job.status == JobStatus.DONE and job.backend_used == "cpu" and job.gpu_fallback


def test_user_cancel_wins_over_a_gpu_the_engine_cannot_use(tmp_path, platform, native):
    platform("darwin")
    cancel = threading.Event()
    outcome = {"lines": VIRTUAL_GPU_LINES, "set_cancel": cancel, "cancelled": True}
    fake = native({"metal": [outcome]})
    paths, job = _run(tmp_path, cancel=cancel)
    assert len(fake.whisper_calls) == 1
    assert job.status == JobStatus.CANCELLED and job.failure is None
    assert list((paths.user_dir / "work").iterdir()) == []


def test_a_working_gpu_report_never_stops_the_engine(tmp_path, platform, native):
    platform("darwin")
    fake = native()
    _paths, job = _run(tmp_path)
    assert fake.stop_requested == [False]
    assert fake.whisper_timeouts == [whisper.WHISPER_LIMIT_SEC]
    assert job.backend_used == "metal" and not job.gpu_fallback


# Coordinator on Windows: same programs and Vulkan behavior as before


def test_windows_vulkan_run_and_retry_use_legacy_program_paths(tmp_path, platform, native):
    platform("win32")
    fake = native({"vulkan": [{"lines": ["ggml_vulkan: failed to allocate"], "exit_code": 1}]})
    paths, job = _run(tmp_path)
    assert fake.whisper_programs == [
        (paths.bin_dir / "vulkan/whisper-cli.exe").resolve(),
        (paths.bin_dir / "cpu/whisper-cli.exe").resolve(),
    ]
    assert [Path(call[0]) for call in fake.ffmpeg_calls] == [
        (paths.bin_dir / "ffmpeg/ffprobe.exe").resolve(),
        (paths.bin_dir / "ffmpeg/ffmpeg.exe").resolve(),
    ]
    assert job.status == JobStatus.DONE and job.backend_used == "cpu" and job.gpu_fallback


def test_windows_vulkan_selection_is_verified(tmp_path, platform, native):
    platform("win32")
    fake = native({"vulkan": [{"lines": VULKAN_LINES}]})
    paths, job = _run(tmp_path)
    assert fake.whisper_programs == [(paths.bin_dir / "vulkan/whisper-cli.exe").resolve()]
    assert "-ng" not in fake.whisper_calls[0]
    assert job.backend_used == "vulkan" and _exported_backend(tmp_path) == "vulkan"


# run_whisper backend verification


def _whisper(tmp_path: Path, backend, lines, exit_code=0, monkeypatch=None):
    fake = FakeNative({backend: [{"lines": lines, "exit_code": exit_code}]})
    monkeypatch.setattr(whisper, "run_job_process", fake.run_whisper)
    folder = tmp_path / backend
    folder.mkdir(exist_ok=True)
    return whisper.run_whisper(
        folder / "whisper-cli",
        tmp_path / "model.bin",
        tmp_path / "audio.wav",
        tmp_path / "raw",
        model_id="tiny",
        task="transcribe",
        language="en",
        threads=4,
        duration_sec=11.0,
        backend=backend,
        vad_model=None,
        prompt="",
    )


def test_real_metal_stderr_is_accepted_with_device_name(tmp_path, monkeypatch):
    run = _whisper(tmp_path, "metal", METAL_LINES, monkeypatch=monkeypatch)
    assert run.transcript.backend == "metal" and run.device_name == "Apple M2"
    assert run.timings_ms["total"] == 257.91 and run.text_context == 448


def test_real_mac_cpu_stderr_is_accepted(tmp_path, monkeypatch):
    run = _whisper(tmp_path, "cpu", MAC_CPU_LINES, monkeypatch=monkeypatch)
    assert run.transcript.backend == "cpu" and run.device_name is None


def test_cpu_request_that_selected_metal_is_rejected_without_gpu_retry(tmp_path, monkeypatch):
    with pytest.raises(EngineError, match="Requested backend was not selected") as raised:
        _whisper(tmp_path, "cpu", METAL_LINES, monkeypatch=monkeypatch)
    assert not raised.value.gpu_error


@pytest.mark.parametrize("lines", [MAC_CPU_LINES, [], VULKAN_LINES])
def test_metal_request_without_metal_selection_is_a_gpu_error(tmp_path, monkeypatch, lines):
    with pytest.raises(EngineError, match="Requested backend was not selected") as raised:
        _whisper(tmp_path, "metal", lines, monkeypatch=monkeypatch)
    assert raised.value.gpu_error


def test_vulkan_request_requires_vulkan_selection(tmp_path, monkeypatch):
    with pytest.raises(EngineError) as raised:
        _whisper(tmp_path, "vulkan", METAL_LINES, monkeypatch=monkeypatch)
    assert raised.value.gpu_error


def test_gpu_without_the_metal_features_is_an_unsupported_gpu_error(tmp_path, monkeypatch):
    # Even when the engine exits by itself with an output, the GPU run fails.
    with pytest.raises(EngineError, match="GPU cannot run the Metal engine") as raised:
        _whisper(tmp_path, "metal", VIRTUAL_GPU_LINES, monkeypatch=monkeypatch)
    error = raised.value
    assert error.gpu_error and error.unsupported_gpu and not error.cancelled
    assert error.device_name == "Apple Paravirtual device"


def test_metal_features_do_not_matter_for_cpu_runs(tmp_path, monkeypatch):
    lines = MAC_CPU_LINES + [line for line in VIRTUAL_GPU_LINES if "simdgroup" in line]
    run = _whisper(tmp_path, "cpu", lines, monkeypatch=monkeypatch)
    assert run.transcript.backend == "cpu"


# Logging allowlist


def _allowed(message: str) -> bool:
    return RedactionFilter().filter(
        logging.LogRecord("dusty", logging.INFO, "", 0, message, (), None)
    )


@pytest.mark.parametrize("backend", ["cpu", "vulkan", "metal"])
def test_log_allowlist_accepts_each_engine_backend(backend):
    job = "12345678-1234-1234-1234-123456789abc"
    assert _allowed(f"job_id={job} model=tiny backend={backend} decode_sec=0.100")


@pytest.mark.parametrize("value", ["metalx", "Metal", "metal/Users/x", "gpu", "auto"])
def test_log_allowlist_rejects_other_backend_values(value):
    assert not _allowed(f"job_id=12345678-1234-1234-1234-123456789abc backend={value}")


# Platform GPU probe


def _probe_paths(tmp_path: Path, executable: str) -> RuntimePaths:
    paths = RuntimePaths(
        tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "user"
    )
    program = paths.bin_dir / executable
    program.parent.mkdir(parents=True)
    program.write_bytes(b"pinned engine v1")
    return paths


def test_mac_probe_keys_cache_on_metal_engine_and_mac_signature(
    tmp_path, platform, native, monkeypatch
):
    from dusty.engine import backend
    from dusty.queue.storage import load_settings

    platform("darwin")
    fake = native()
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "mac-signature")
    paths = _probe_paths(tmp_path, "metal/whisper-cli")
    registry = StubRegistry(paths.models_dir)
    assert backend.probe_gpu(paths, registry) is True
    assert fake.whisper_programs == [(paths.bin_dir / "metal/whisper-cli").resolve()]
    cached = load_settings(paths.user_dir / "settings.json")["backend_probe"]
    assert cached == {
        "engine": hashlib.sha256(b"pinned engine v1").hexdigest(),
        "driver": "mac-signature",
        "ok": True,
        "device_name": "Apple M2",
    }
    assert backend.probe_vulkan(paths, registry) is True
    assert len(fake.whisper_calls) == 1  # Cached by identity.
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "after-os-update")
    fake.outcomes["metal"] = [{"lines": MAC_CPU_LINES}]
    assert backend.probe_vulkan(paths, registry) is False
    assert len(fake.whisper_calls) == 2
    assert list((paths.user_dir / "work").iterdir()) == []


def test_mac_probe_records_a_gpu_the_engine_cannot_use(tmp_path, platform, native, monkeypatch):
    from dusty.engine import backend
    from dusty.queue.storage import load_settings

    platform("darwin")
    fake = native({"metal": [{"lines": VIRTUAL_GPU_LINES, "cancelled": True}]})
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "mac-signature")
    paths = _probe_paths(tmp_path, "metal/whisper-cli")
    registry = StubRegistry(paths.models_dir)
    assert backend.probe_gpu(paths, registry) is False
    assert fake.stop_requested == [True]
    assert fake.whisper_timeouts == [backend.GPU_CHECK_LIMIT_SEC]
    cached = load_settings(paths.user_dir / "settings.json")["backend_probe"]
    assert cached == {
        "engine": hashlib.sha256(b"pinned engine v1").hexdigest(),
        "driver": "mac-signature",
        "ok": False,
        "device_name": "Apple Paravirtual device",
        "unsupported": True,
    }
    assert backend.probe_gpu(paths, registry) is False
    assert len(fake.whisper_calls) == 1  # Remembered for this engine and GPU.
    assert list((paths.user_dir / "work").iterdir()) == []


def test_mac_probe_that_reaches_its_time_limit_uses_the_cpu(
    tmp_path, platform, native, monkeypatch
):
    from dusty.engine import backend
    from dusty.queue.storage import load_settings

    platform("darwin")
    # The runner stops a run at its time limit and reports it as cancelled.
    stalled = {"lines": METAL_LINES[:20], "cancelled": True}
    fake = native({"metal": [stalled]})
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "mac-signature")
    paths = _probe_paths(tmp_path, "metal/whisper-cli")
    assert backend.probe_gpu(paths, StubRegistry(paths.models_dir)) is False
    assert fake.whisper_timeouts == [backend.GPU_CHECK_LIMIT_SEC]
    cached = load_settings(paths.user_dir / "settings.json")["backend_probe"]
    assert cached["ok"] is False and "unsupported" not in cached
    assert list((paths.user_dir / "work").iterdir()) == []


def test_windows_probe_alias_uses_vulkan_engine(tmp_path, platform, native, monkeypatch):
    from dusty.engine import backend

    platform("win32")
    fake = native({"vulkan": [{"lines": VULKAN_LINES}]})
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "driver")
    paths = _probe_paths(tmp_path, "vulkan/whisper-cli.exe")
    assert backend.probe_vulkan(paths, StubRegistry(paths.models_dir)) is True
    assert fake.whisper_programs == [(paths.bin_dir / "vulkan/whisper-cli.exe").resolve()]
    # Windows keeps its engine time limit: the Mac GPU check limit is Mac only.
    assert fake.whisper_timeouts == [whisper.WHISPER_LIMIT_SEC]


def test_probe_without_gpu_engine_is_false_without_running(tmp_path, platform, native):
    from dusty.engine import backend

    platform("darwin")
    fake = native()
    paths = RuntimePaths(
        tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "user"
    )
    assert backend.probe_gpu(paths, StubRegistry(paths.models_dir)) is False
    assert fake.whisper_calls == [] and fake.ffmpeg_calls == []


class UninstalledRegistry(StubRegistry):
    """A registry whose model is missing or damaged until ``error`` is cleared."""

    def __init__(self, folder: Path, error: type[Exception] | None):
        super().__init__(folder)
        self.error = error

    def model_path(self, model_id: str) -> Path:
        if self.error is not None:
            raise self.error("not installed")
        return super().model_path(model_id)


@pytest.mark.parametrize(
    ("name", "executable"),
    [("darwin", "metal/whisper-cli"), ("win32", "vulkan/whisper-cli.exe")],
)
@pytest.mark.parametrize("missing", ["ModelMissing", "ModelCorrupt"])
def test_probe_without_usable_model_caches_nothing(
    tmp_path, platform, native, monkeypatch, name, executable, missing
):
    """A headless run before the first model must not record the GPU as unusable.

    MAC10-UPGRADE: a headless batch with no model cached ok false for this engine
    and GPU, so Automatic stayed on the processor after a model was installed.
    """
    from dusty import models
    from dusty.engine import backend
    from dusty.queue.storage import load_settings

    platform(name)
    fake = native({"vulkan": [{"lines": VULKAN_LINES}]} if name == "win32" else None)
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "signature")
    paths = _probe_paths(tmp_path, executable)
    registry = UninstalledRegistry(paths.models_dir, getattr(models, missing))
    settings = paths.user_dir / "settings.json"
    assert backend.probe_gpu(paths, registry) is False
    assert fake.whisper_calls == [] and fake.ffmpeg_calls == []
    assert "backend_probe" not in load_settings(settings)
    registry.error = None
    assert backend.probe_gpu(paths, registry) is True
    assert len(fake.whisper_calls) == 1
    assert load_settings(settings)["backend_probe"]["ok"] is True
    assert list((paths.user_dir / "work").iterdir()) == []


# devcli and selftest


def test_devcli_accepts_only_this_platforms_gpu_name(platform, monkeypatch, capsys):
    from dusty import devcli

    seen = []
    monkeypatch.setattr(devcli, "transcribe", lambda *args, **kwargs: seen.append(kwargs) or 0)
    base = ["transcribe", "clip.wav", "--out", "output", "--backend"]
    platform("darwin")
    assert devcli.main([*base, "metal"]) == 0 and seen[-1]["backend"] == "metal"
    assert devcli.main([*base, "vulkan"]) == 2
    assert capsys.readouterr().out.strip().endswith("BACKEND_UNSUPPORTED")
    platform("win32")
    assert devcli.main([*base, "vulkan"]) == 0 and seen[-1]["backend"] == "vulkan"
    assert devcli.main([*base, "metal"]) == 2
    assert len(seen) == 2


def test_devcli_api_rejects_wrong_gpu_before_touching_app_data(platform, monkeypatch, tmp_path):
    from dusty import devcli

    platform("darwin")
    monkeypatch.setattr(devcli, "resolve_paths", lambda: pytest.fail("paths resolved"))
    assert devcli.transcribe([], tmp_path, model="tiny", backend="vulkan", formats=("txt",)) == 2


def test_selftest_rejects_other_platform_gpu(tmp_path, platform):
    from dusty.selftest import run_selftest

    platform("darwin")
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    assert run_selftest(paths, "tiny", backend="vulkan") == "GPU_UNSUPPORTED"
    assert not (paths.user_dir / "work").exists()


@pytest.mark.parametrize(
    ("backend", "once", "probe_ok", "code", "programs"),
    [
        ("metal", False, True, "OK", ["cpu", "metal"]),
        ("auto", False, False, "OK", ["cpu"]),
        ("metal", False, False, "GPU_ERROR", []),
        ("auto", True, True, "OK_METAL", ["metal"]),
        ("metal", True, False, "OK_METAL", ["metal"]),
        ("cpu", True, True, "OK_CPU", ["cpu"]),
    ],
)
def test_mac_selftest_runs_metal_program(
    tmp_path, platform, native, monkeypatch, backend, once, probe_ok, code, programs
):
    from dusty import selftest
    from dusty.engine import backend as backend_module

    platform("darwin")
    fake = native()
    monkeypatch.setattr(selftest, "ModelRegistry", lambda *_args: StubRegistry(tmp_path))
    monkeypatch.setattr(backend_module, "probe_vulkan", lambda *_a, **_k: probe_ok)
    monkeypatch.setattr(backend_module, "probe_gpu", lambda *_a, **_k: probe_ok)
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    assert selftest.run_selftest(paths, "tiny", backend=backend, once=once) == code
    expected = {"cpu": "cpu/whisper-cli", "metal": "metal/whisper-cli"}
    assert fake.whisper_programs == [(paths.bin_dir / expected[b]).resolve() for b in programs]
    assert list((paths.user_dir / "work").iterdir()) == []


@pytest.mark.parametrize("host", ["darwin", "win32"])
def test_selftest_gpu_probe_follows_the_backend_not_the_host(
    tmp_path, platform, native, monkeypatch, host
):
    """The Auto self-test probes the GPU of the build it runs, on any test host.

    It once asked the host separately: on a Windows CI runner a Metal build then
    used the Windows device probe, found no GPU and fell back to the processor.
    """
    from dusty import installer_support, selftest
    from dusty.engine import backend as backend_module

    def windows_probe(*_args, **_kwargs):
        raise AssertionError("a Metal build used the Windows device probe")

    platform("darwin")
    fake = native()
    monkeypatch.setattr(selftest, "sys", SimpleNamespace(platform=host), raising=False)
    monkeypatch.setattr(installer_support, "probe", windows_probe)
    monkeypatch.setattr(selftest, "ModelRegistry", lambda *_args: StubRegistry(tmp_path))
    monkeypatch.setattr(backend_module, "probe_gpu", lambda *_a, **_k: True)
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    assert selftest.run_selftest(paths, "tiny", backend="auto", once=True) == "OK_METAL"
    assert fake.whisper_programs == [(paths.bin_dir / "metal/whisper-cli").resolve()]


def test_mac_selftest_reports_metal_failure_by_name(tmp_path, platform, native, monkeypatch):
    from dusty import selftest

    platform("darwin")
    native({"metal": [{"lines": MAC_CPU_LINES}]})
    monkeypatch.setattr(selftest, "ModelRegistry", lambda *_args: StubRegistry(tmp_path))
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    assert selftest.run_selftest(paths, "tiny", backend="metal", once=True) == (
        "SELFTEST_FAILED_METAL"
    )
    assert list((paths.user_dir / "work").iterdir()) == []


# Inside a virtual Mac (GitHub's runners) the Metal engine never starts. On the
# M1 runners it stalled while compiling its shaders, before it reported anything.


@pytest.fixture
def virtual_host(monkeypatch):
    monkeypatch.setattr("dusty.platform.virtual_mac.is_virtual_mac", lambda: True)


@pytest.mark.usefixtures("virtual_host")
@pytest.mark.parametrize(
    ("requested", "vulkan_ok", "fallback"),
    [("metal", False, True), ("metal", True, True), ("auto", True, True), ("auto", False, False)],
)
def test_virtual_mac_runs_jobs_on_the_cpu_without_starting_metal(
    tmp_path, platform, native, requested, vulkan_ok, fallback
):
    platform("darwin")
    fake = native()
    paths, job = _run(tmp_path, requested, vulkan_ok=vulkan_ok)
    assert fake.whisper_programs == [(paths.bin_dir / "cpu/whisper-cli").resolve()]
    assert "-ng" in fake.whisper_calls[0]
    assert job.status == JobStatus.DONE and job.failure is None
    assert job.backend_used == "cpu" and job.gpu_fallback is fallback
    assert _exported_backend(tmp_path) == "cpu"
    assert list((paths.user_dir / "work").iterdir()) == []


def _metal_run(tmp_path: Path, fake: FakeNative, monkeypatch, cancel=None):
    monkeypatch.setattr(whisper, "run_job_process", fake.run_whisper)
    return whisper.run_whisper(
        tmp_path / "metal/whisper-cli",
        tmp_path / "model.bin",
        tmp_path / "audio.wav",
        tmp_path / "raw",
        model_id="tiny",
        task="transcribe",
        language="en",
        threads=4,
        duration_sec=11.0,
        backend="metal",
        vad_model=None,
        prompt="",
        cancel=cancel,
    )


@pytest.mark.usefixtures("virtual_host")
def test_virtual_mac_metal_request_fails_on_the_gpu_without_a_process(tmp_path, monkeypatch):
    fake = FakeNative()
    with pytest.raises(EngineError, match="does not use the GPU inside a virtual Mac") as raised:
        _metal_run(tmp_path, fake, monkeypatch)
    error = raised.value
    assert error.gpu_error and error.unsupported_gpu and error.virtual_mac
    assert not error.cancelled and error.device_name is None
    assert fake.whisper_calls == []


@pytest.mark.usefixtures("virtual_host")
def test_virtual_mac_cancel_before_a_metal_run_is_a_cancel(tmp_path, monkeypatch):
    cancel = threading.Event()
    cancel.set()
    fake = FakeNative()
    with pytest.raises(EngineError) as raised:
        _metal_run(tmp_path, fake, monkeypatch, cancel)
    assert raised.value.cancelled and not raised.value.gpu_error
    assert fake.whisper_calls == []


@pytest.mark.parametrize(("backend", "lines"), [("cpu", MAC_CPU_LINES), ("vulkan", VULKAN_LINES)])
def test_cpu_and_windows_runs_never_ask_whether_this_is_a_virtual_mac(
    tmp_path, monkeypatch, backend, lines
):
    def asked() -> bool:
        raise AssertionError("only a Metal run asks whether this is a virtual Mac")

    monkeypatch.setattr("dusty.platform.virtual_mac.is_virtual_mac", asked)
    assert _whisper(tmp_path, backend, lines, monkeypatch=monkeypatch).transcript.backend == backend


@pytest.mark.usefixtures("virtual_host")
def test_mac_probe_records_a_virtual_mac_without_starting_metal(
    tmp_path, platform, native, monkeypatch
):
    from dusty.engine import backend
    from dusty.queue.storage import load_settings

    platform("darwin")
    fake = native()
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "mac-signature")
    paths = _probe_paths(tmp_path, "metal/whisper-cli")
    registry = StubRegistry(paths.models_dir)
    assert backend.probe_gpu(paths, registry) is False
    assert fake.whisper_calls == []
    cached = load_settings(paths.user_dir / "settings.json")["backend_probe"]
    assert cached == {
        "engine": hashlib.sha256(b"pinned engine v1").hexdigest(),
        "driver": "mac-signature",
        "ok": False,
        "device_name": None,
        "unsupported": True,
        "virtual_mac": True,
    }
    assert backend.probe_gpu(paths, registry) is False
    assert list((paths.user_dir / "work").iterdir()) == []


@pytest.mark.usefixtures("virtual_host")
def test_virtual_mac_selftest_reports_a_gpu_error_and_auto_uses_the_cpu(
    tmp_path, platform, native, monkeypatch
):
    from dusty import selftest
    from dusty.engine import backend

    platform("darwin")
    fake = native()
    monkeypatch.setattr(selftest, "ModelRegistry", lambda *_args: StubRegistry(tmp_path))
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "mac-signature")
    paths = _probe_paths(tmp_path, "metal/whisper-cli")
    assert selftest.run_selftest(paths, "tiny", backend="metal") == "GPU_ERROR"
    assert fake.whisper_calls == []
    assert selftest.run_selftest(paths, "tiny", backend="auto", once=True) == "OK_CPU"
    assert fake.whisper_programs == [(paths.bin_dir / "cpu/whisper-cli").resolve()]
    assert list((paths.user_dir / "work").iterdir()) == []
