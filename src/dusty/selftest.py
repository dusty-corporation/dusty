"""Offline installed-app decode and transcription check."""

import logging

from dusty.core.types import EngineBackend
from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.engine.binaries import ffmpeg_path, ffprobe_path, gpu_backend, whisper_path
from dusty.models import ModelRegistry, load_manifest
from dusty.platform.cpu_topology import default_threads
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork


def run_selftest(
    paths: RuntimePaths, model_id: str, *, backend: str = "auto", once: bool = False
) -> str:
    """Return a reason code, with no transcript or path in diagnostics.

    ``backend`` is auto, cpu or this platform's GPU backend (vulkan on Windows,
    metal on macOS). The other platform's GPU name returns GPU_UNSUPPORTED.
    """
    gpu = gpu_backend()
    if backend not in {"auto", "cpu", gpu}:
        return "GPU_UNSUPPORTED"
    owned = OwnedWork(paths.user_dir / "work", "selftest")
    work = owned.path
    attempted = "cpu"
    try:
        registry = ModelRegistry(
            load_manifest(paths.resources_dir / "models.json"), paths.models_dir
        )
        model = registry.model_path(model_id)
        fixture = paths.resources_dir / "selftest.wav"
        probe = probe_audio(ffprobe_path(paths.bin_dir), fixture)
        if not probe.has_audio:
            return "NO_AUDIO"
        wav = work / "audio.wav"
        transcode_audio(ffmpeg_path(paths.bin_dir), fixture, wav)
        backends: list[EngineBackend] = ["cpu"]
        if once:
            if backend == "auto":
                # Follow the GPU backend chosen above, so the probe and the
                # program always come from the same platform decision.
                if gpu == "vulkan":
                    from dusty.installer_support import probe as device_probe

                    found = device_probe(paths, work / "probe.json")
                else:
                    from dusty.engine.backend import probe_gpu

                    found = probe_gpu(paths, registry, model_id=model_id)
                backends = [gpu] if found else ["cpu"]
            else:
                backends = [gpu] if backend == gpu else ["cpu"]
        elif backend in {"auto", gpu}:
            from dusty.engine.backend import probe_vulkan

            if probe_vulkan(paths, registry, model_id=model_id):
                backends.append(gpu)
            elif backend == gpu:
                return "GPU_ERROR"
        for selected in backends:
            attempted = selected
            result = run_whisper(
                whisper_path(paths.bin_dir, selected),
                model,
                wav,
                work / f"raw-{selected}",
                model_id=model_id,
                task="transcribe",
                language="en",
                # Never more threads than cores: on a two-thread computer four
                # whisper.cpp threads spin against each other and do not finish.
                threads=min(4, default_threads()),
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
        owned.record("audio.wav", "probe.json", "raw-cpu.json", f"raw-{gpu}.json")
        owned.cleanup(paths.user_dir)
