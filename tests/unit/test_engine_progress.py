"""Parse only numeric and backend evidence from recorded engine lines."""

import time
from pathlib import Path

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
