"""Extract only numeric progress, backend, and timings from native stderr."""

import re
import time
from dataclasses import dataclass, field
from typing import Literal

_PROGRESS = re.compile(r"whisper_print_progress_callback: progress =\s*(\d+)%")
_TIMING = re.compile(
    r"whisper_print_timings:\s*(load|mel|sample|encode|decode|batchd|prompt|total) "
    r"time =\s*([0-9.]+) ms"
)
_TEXT_CTX = re.compile(r"whisper_model_load: n_text_ctx\s*=\s*(\d+)")


@dataclass
class ProgressState:
    started_at: float
    progress: float = 0.0
    first_progress_sec: float | None = None
    backend: Literal["cpu", "vulkan"] | None = None
    device_name: str | None = None
    gpu_error: bool = False
    text_context: int | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)

    def feed(self, line: str) -> None:
        """Discard all unrecognized stderr, including paths and transcript text."""
        match = _PROGRESS.search(line)
        if match:
            self.progress = min(1.0, max(0.0, int(match.group(1)) / 100))
            if self.first_progress_sec is None:
                self.first_progress_sec = time.monotonic() - self.started_at
        if "whisper_backend_init_gpu: using Vulkan" in line:
            self.backend = "vulkan"
        if line.startswith("ggml_vulkan: 0 = "):
            self.device_name = line.removeprefix("ggml_vulkan: 0 = ").split(" (")[0][:120]
        elif "whisper_backend_init_gpu: no GPU found" in line and self.backend is None:
            self.backend = "cpu"
        if "vulkan" in line.lower() and ("error" in line.lower() or "failed" in line.lower()):
            self.gpu_error = True
        timing = _TIMING.search(line)
        if timing:
            self.timings_ms[timing.group(1)] = float(timing.group(2))
        context = _TEXT_CTX.search(line)
        if context:
            self.text_context = int(context.group(1))
