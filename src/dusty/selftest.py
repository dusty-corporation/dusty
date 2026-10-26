"""Offline installed-app decode and transcription check."""

import logging
from typing import Literal

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork


def run_selftest(
    paths: RuntimePaths, model_id: str, *, backend: str = "auto", once: bool = False
) -> str:
    """Return a reason code, with no transcript or path in diagnostics."""
    owned = OwnedWork(paths.user_dir / "work", "selftest")
    work = owned.path
    attempted = "cpu"
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
        if once:
            if backend == "auto":
                from dusty.installer_support import probe as device_probe

                backends = ["vulkan"] if device_probe(paths, work / "probe.json") else ["cpu"]
            else:
                backends = ["vulkan"] if backend == "vulkan" else ["cpu"]
        elif backend in {"auto", "vulkan"}:
            from dusty.engine.backend import probe_vulkan

            if probe_vulkan(paths, registry, model_id=model_id):
                backends.append("vulkan")
            elif backend == "vulkan":
                return "GPU_ERROR"
        for selected in backends:
            attempted = selected
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
                return "TEXT_MISMATCH_" + attempted.upper() if once else "TEXT_MISMATCH"
        logging.getLogger("dusty").info("status=done")
        return "OK_" + backends[0].upper() if once else "OK"
    except Exception:
        logging.getLogger("dusty").info("status=failed")
        return "SELFTEST_FAILED_" + attempted.upper() if once else "SELFTEST_FAILED"
    finally:
        owned.record("audio.wav", "probe.json", "raw-cpu.json", "raw-vulkan.json")
        owned.cleanup(paths.user_dir)
