"""Offline installed-app decode and transcription check."""

import logging
import shutil
from typing import Literal

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import RuntimePaths


def run_selftest(paths: RuntimePaths, model_id: str, *, backend: str = "auto") -> str:
    """Return a reason code, with no transcript or path in diagnostics."""
    work = paths.user_dir / "work/selftest"
    work.mkdir(parents=True, exist_ok=True)
    try:
        registry = ModelRegistry(
            load_manifest(paths.resources_dir / "models.json"), paths.models_dir
        )
        model = registry.model_path(model_id)
        fixture = paths.resources_dir / "selftest.wav"
        probe = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", fixture)
        if not probe.has_audio:
            return "NO_AUDIO"
        wav = work / "audio.wav"
        transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", fixture, wav)
        backends: list[Literal["cpu", "vulkan"]] = ["cpu"]
        if backend in {"auto", "vulkan"}:
            from dusty.engine.backend import probe_vulkan

            if probe_vulkan(paths, registry, model_id=model_id):
                backends.append("vulkan")
            elif backend == "vulkan":
                return "GPU_ERROR"
        for selected in backends:
            result = run_whisper(
                paths.bin_dir / selected / "whisper-cli.exe",
                model,
                wav,
                work / f"raw-{selected}",
                model_id=model_id,
                task="transcribe",
                language="en",
                threads=4,
                duration_sec=probe.duration_sec,
                backend=selected,
                vad_model=None,
                prompt="",
            )
            text = " ".join(segment.text.lower() for segment in result.transcript.segments)
            if "fellow americans" not in text or "your country" not in text:
                return "TEXT_MISMATCH"
        logging.getLogger("dusty").info("status=done")
        return "OK"
    except Exception:
        logging.getLogger("dusty").info("status=failed")
        return "SELFTEST_FAILED"
    finally:
        shutil.rmtree(work)
