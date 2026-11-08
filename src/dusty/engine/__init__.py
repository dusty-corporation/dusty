"""Offline native adapters, loaded only when their public API is requested."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ffmpeg import AudioProbe as AudioProbe
    from .ffmpeg import DecoderError as DecoderError
    from .ffmpeg import probe_audio as probe_audio
    from .ffmpeg import transcode_audio as transcode_audio
    from .whisper import EngineError as EngineError
    from .whisper import EngineRun as EngineRun
    from .whisper import run_whisper as run_whisper

__all__ = [
    "AudioProbe",
    "DecoderError",
    "EngineError",
    "EngineRun",
    "probe_audio",
    "run_whisper",
    "transcode_audio",
]


def __getattr__(name: str) -> Any:
    """Preserve runner exports without importing process APIs for pure parsers."""
    if name in {"AudioProbe", "DecoderError", "probe_audio", "transcode_audio"}:
        from . import ffmpeg

        value = getattr(ffmpeg, name)
    elif name in {"EngineError", "EngineRun", "run_whisper"}:
        from . import whisper

        value = getattr(whisper, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
