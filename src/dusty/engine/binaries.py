"""Platform-specific names for the fixed native programs inside bin_dir.

Layout (Windows adds .exe): ffmpeg/ffmpeg, ffmpeg/ffprobe, cpu/whisper-cli,
vulkan/whisper-cli (Windows) or metal/whisper-cli (Mac), and on Mac only
lifeline/dusty-lifeline, which owns each child's process group (ADR 0037).
"""

import sys
from pathlib import Path
from typing import Literal

from dusty.core.types import EngineBackend


def _suffix(platform: str | None) -> str:
    return ".exe" if (sys.platform if platform is None else platform) == "win32" else ""


def gpu_backend(platform: str | None = None) -> Literal["vulkan", "metal"]:
    """The single GPU backend this platform ships."""
    return "metal" if (sys.platform if platform is None else platform) == "darwin" else "vulkan"


def ffmpeg_path(bin_dir: Path, platform: str | None = None) -> Path:
    return bin_dir / "ffmpeg" / f"ffmpeg{_suffix(platform)}"


def ffprobe_path(bin_dir: Path, platform: str | None = None) -> Path:
    return bin_dir / "ffmpeg" / f"ffprobe{_suffix(platform)}"


def whisper_path(bin_dir: Path, backend: EngineBackend, platform: str | None = None) -> Path:
    return bin_dir / backend / f"whisper-cli{_suffix(platform)}"


def lifeline_path(bin_dir: Path) -> Path:
    return bin_dir / "lifeline" / "dusty-lifeline"
