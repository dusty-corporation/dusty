"""Parse only numeric and backend evidence from recorded engine lines."""

import time
from pathlib import Path

import pytest

from dusty.engine.progress import ProgressState

ROOT = Path(__file__).resolve().parents[2]


def test_recorded_progress_reaches_completion() -> None:
    state = ProgressState(started_at=time.monotonic())
    for line in (ROOT / "tests/fixtures/engine/progress-stderr.txt").read_text().splitlines():
        state.feed(line)
    assert state.progress == 1.0
    assert state.first_progress_sec is not None


def test_vulkan_selection_survives_later_vad_cpu_message() -> None:
    state = ProgressState(started_at=time.monotonic())
    state.feed("whisper_backend_init_gpu: using Vulkan0 backend")
    state.feed("whisper_backend_init_gpu: no GPU found")
    state.feed("whisper_print_timings: load time = 81.93 ms")
    state.feed("whisper_model_load: n_text_ctx = 448")
    state.feed("main: processing a private path and transcript text")
    assert state.backend == "vulkan"
    assert state.timings_ms == {"load": 81.93}
    assert state.text_context == 448
    assert "private" not in repr(state)


def test_gpu_failure_is_reduced_to_boolean() -> None:
    state = ProgressState(started_at=time.monotonic())
    state.feed("ggml_vulkan: failed to allocate device buffer")
    assert state.gpu_error


def test_recorded_metal_selection_and_device_without_raw_stderr() -> None:
    state = ProgressState(started_at=time.monotonic())
    for line in (ROOT / "tests/fixtures/engine/metal-progress-stderr.txt").read_text().splitlines():
        state.feed(line)
    assert state.backend == "metal"
    assert state.device_name == "Apple M2"
    assert state.progress == 1.0
    assert state.text_context == 448
    assert state.timings_ms == {"load": 46.53}
    state.feed("whisper_backend_init_gpu: no GPU found")
    assert state.backend == "metal"


def test_metal_device_detection_alone_does_not_claim_backend_selection() -> None:
    state = ProgressState(started_at=0)
    state.feed("ggml_metal_device_init: GPU name:   MTL0 (Apple M2)")
    assert state.device_name == "Apple M2"
    assert state.backend is None


def test_metal_failure_recognition_is_anchored_and_retains_only_boolean() -> None:
    state = ProgressState(started_at=0)
    state.feed("ggml_metal_synchronize: error: command buffer 0 failed with status 5")
    assert state.gpu_error
    assert state.backend is None


def test_metal_messages_discard_paths_transcript_and_unknown_device_text() -> None:
    state = ProgressState(started_at=0)
    for line in (
        "/Users/CANARY_PATIENT/metal error failed.wav",
        "[00:00.000 --> 00:01.000] metal error failed CANARY_TRANSCRIPT",
        "main: whisper_backend_init_gpu: using MTL0 backend CANARY_HINT",
        "ggml_metal_device_init: GPU name:   MTL0 (/Users/CANARY_PATIENT/audio.wav)",
        "ggml_metal_device_init: GPU name:   MTL0 (CANARY_TRANSCRIPT)",
        "ggml_metal_init: expected error tests passed CANARY_HINT",
    ):
        state.feed(line)
    assert state.backend is None
    assert state.device_name is None
    assert not state.gpu_error
    assert "CANARY" not in repr(state)


@pytest.mark.parametrize(
    "line",
    [
        "ggml_metal_init: error: failed to create command queue",
        "ggml_metal_init: error: failed to initialize the Metal library",
        "ggml_metal_synchronize: error: command buffer 1 failed with status 5",
        "ggml_metal_graph_compute: command buffer 2 failed with status 5",
    ],
)
def test_known_metal_failures_remain_errors_after_selection(line: str) -> None:
    state = ProgressState(started_at=0)
    state.feed("whisper_backend_init_gpu: using MTL0 backend")
    state.feed(line + "\n")
    state.feed("whisper_backend_init_gpu: no GPU found")
    assert state.gpu_error
    assert state.backend == "metal"


@pytest.mark.parametrize(
    "line",
    [
        "whisper_backend_init_gpu: using MTL0 backend: private text",
        "main: whisper_backend_init_gpu: using MTL0 backend",
        "ggml_metal_init: error: failed to create command queue /Users/CANARY/a.wav",
        "ggml_metal_init: error compiling source: CANARY_TRANSCRIPT",
        "ggml_metal_synchronize: error: command buffer CANARY failed with status 5",
        "ggml_metal_device_init: GPU name:   MTL0 (Apple M2/Users/CANARY)",
        "ggml_metal_device_init: GPU name:   MTL0 (Apple M2) CANARY_HINT",
    ],
)
def test_unrecognized_or_embedded_metal_evidence_does_not_change_state(line: str) -> None:
    state = ProgressState(started_at=0)
    state.feed(line)
    assert state.backend is None
    assert state.device_name is None
    assert not state.gpu_error
    assert "CANARY" not in repr(state)


@pytest.mark.parametrize("name", ["Apple M1", "Apple M2 Pro", "Apple M3 Max", "Apple M4 Ultra"])
def test_recognized_apple_silicon_device_descriptions(name: str) -> None:
    state = ProgressState(started_at=0)
    state.feed(f"ggml_metal_device_init: GPU name:   MTL0 ({name})\r\n")
    assert state.device_name == name
    assert state.backend is None


def test_cpu_evidence_can_be_followed_by_actual_metal_selection() -> None:
    state = ProgressState(started_at=0)
    state.feed("whisper_backend_init_gpu: no GPU found")
    assert state.backend == "cpu"
    state.feed("whisper_backend_init_gpu: using MTL0 backend")
    state.feed("whisper_backend_init_gpu: no GPU found")
    assert state.backend == "metal"


def test_vulkan_device_name_format_preserved() -> None:
    state = ProgressState(started_at=0)
    state.feed("ggml_vulkan: 0 = Intel(R) Iris(R) Xe Graphics (Intel driver)")
    assert state.device_name == "Intel(R) Iris(R) Xe Graphics"


def test_recorded_apple_silicon_report_has_both_metal_features() -> None:
    state = ProgressState(started_at=0)
    for line in (ROOT / "tests/fixtures/engine/mac-metal-full-stderr.txt").read_text().splitlines():
        state.feed(line)
    assert state.backend == "metal" and state.device_name == "Apple M2"
    assert not state.metal_unsupported


# What the pinned engine prints on Apple's paravirtual GPU (GitHub's Mac runners).
PARAVIRTUAL_REPORT = (
    "ggml_metal_device_init: GPU name:   MTL0 (Apple Paravirtual device)",
    "ggml_metal_device_init: GPU family: MTLGPUFamilyApple5  (1005)",
    "ggml_metal_device_init: simdgroup reduction   = false",
    "ggml_metal_device_init: simdgroup matrix mul. = false",
)


@pytest.mark.parametrize("missing", [2, 3])
def test_a_gpu_missing_either_metal_feature_is_unsupported(missing: int) -> None:
    state = ProgressState(started_at=0)
    for index, line in enumerate(PARAVIRTUAL_REPORT):
        state.feed(line if index in (0, 1, missing) else line.replace("false", "true"))
    assert state.metal_unsupported
    assert state.device_name == "Apple Paravirtual device"
    assert state.backend is None and not state.gpu_error


@pytest.mark.parametrize(
    "line",
    [
        "ggml_metal_device_init: simdgroup reduction   = true",
        "ggml_metal_device_init: simdgroup matrix mul. = true\r\n",
        "main: ggml_metal_device_init: simdgroup reduction   = false",
        "ggml_metal_device_init: simdgroup reduction   = false CANARY_HINT",
        "ggml_metal_device_init: has bfloat            = false",
        "[00:00.000 --> 00:01.000] simdgroup reduction = false CANARY_TRANSCRIPT",
        "ggml_metal_device_init: GPU name:   MTL0 (Apple Paravirtual device) CANARY",
    ],
)
def test_metal_feature_evidence_is_anchored(line: str) -> None:
    state = ProgressState(started_at=0)
    state.feed(line)
    assert not state.metal_unsupported
    assert state.device_name is None
    assert "CANARY" not in repr(state)
