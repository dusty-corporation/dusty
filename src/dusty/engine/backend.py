"""Probe Vulkan locally and cache only non-sensitive status and signatures."""

import hashlib
import shutil
from pathlib import Path

from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry
from dusty.platform.gpu_signature import display_driver_signature
from dusty.queue.storage import load_settings, save_settings
from dusty.runtime_paths import RuntimePaths

from .ffmpeg import probe_audio, transcode_audio
from .whisper import EngineError, run_whisper


def _engine_signature(executable: Path) -> str:
    digest = hashlib.sha256()
    with executable.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_vulkan(
    paths: RuntimePaths, registry: ModelRegistry, *, refresh: bool = False, model_id: str = "tiny"
) -> bool:
    """Recheck whenever the pinned engine or display-driver signature changes."""
    executable = paths.bin_dir / "vulkan/whisper-cli.exe"
    try:
        identity = {"engine": _engine_signature(executable), "driver": display_driver_signature()}
    except OSError:
        return False
    settings_path = paths.user_dir / "settings.json"
    settings = load_settings(settings_path)
    if not refresh:
        cached = settings.get("backend_probe", {})
        if isinstance(cached, dict) and all(
            cached.get(key) == value for key, value in identity.items()
        ):
            return cached.get("ok") is True
    work = paths.user_dir / "work/probe"
    work.mkdir(parents=True, exist_ok=True)
    ok = False
    device_name = None
    try:
        fixture = paths.resources_dir / "selftest.wav"
        audio = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", fixture)
        transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", fixture, work / "audio.wav")
        run = run_whisper(
            executable,
            registry.model_path(model_id),
            work / "audio.wav",
            work / "raw",
            model_id=model_id,
            task="transcribe",
            language="en",
            threads=4,
            duration_sec=audio.duration_sec,
            backend="vulkan",
            vad_model=None,
            prompt="",
        )
        ok = bool(run.transcript.segments)
        device_name = run.device_name
    except (OSError, EngineError, ValueError, ModelMissing, ModelCorrupt):
        ok = False
    finally:
        shutil.rmtree(work)
    settings["backend_probe"] = {**identity, "ok": ok, "device_name": device_name}
    save_settings(settings_path, settings)
    return ok
