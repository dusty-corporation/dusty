"""Probe the platform GPU backend locally and cache only non-sensitive signatures.

Windows probes Vulkan and keys the cache on the Vulkan whisper-cli hash plus the
display driver signature. macOS probes Metal and keys it on the Metal whisper-cli
hash plus a hardware and OS signature.
"""

import hashlib
from pathlib import Path

from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry
from dusty.platform.cpu_topology import default_threads
from dusty.platform.gpu_signature import display_driver_signature
from dusty.queue.storage import load_settings, save_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork

from .binaries import ffmpeg_path, ffprobe_path, gpu_backend, whisper_path
from .ffmpeg import probe_audio, transcode_audio
from .whisper import WHISPER_LIMIT_SEC, EngineError, run_whisper

# The Mac GPU check transcribes a few seconds of speech with Tiny, which a
# working Apple GPU does in about a second. A check still running after this
# long is stalled: it is stopped and Dusty uses the CPU.
GPU_CHECK_LIMIT_SEC = 120.0


def _engine_signature(executable: Path) -> str:
    digest = hashlib.sha256()
    with executable.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_gpu(
    paths: RuntimePaths, registry: ModelRegistry, *, refresh: bool = False, model_id: str = "tiny"
) -> bool:
    """Recheck whenever the pinned engine or GPU identity signature changes."""
    backend = gpu_backend()
    executable = whisper_path(paths.bin_dir, backend)
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
    try:
        model = registry.model_path(model_id)
    except (ModelMissing, ModelCorrupt):
        # Without a usable model the GPU was not tested. Record nothing, so the
        # probe still runs once a model is installed (MAC10-UPGRADE defect D1).
        return False
    owned = OwnedWork(paths.user_dir / "work", "probe")
    work = owned.path
    ok = False
    unsupported = False
    virtual = False
    device_name = None
    try:
        fixture = paths.resources_dir / "selftest.wav"
        audio = probe_audio(ffprobe_path(paths.bin_dir), fixture)
        transcode_audio(ffmpeg_path(paths.bin_dir), fixture, work / "audio.wav")
        run = run_whisper(
            executable,
            model,
            work / "audio.wav",
            work / "raw",
            model_id=model_id,
            task="transcribe",
            language="en",
            # Never more threads than cores (see selftest.run_selftest).
            threads=min(4, default_threads()),
            duration_sec=audio.duration_sec,
            backend=backend,
            vad_model=None,
            prompt="",
            timeout_sec=GPU_CHECK_LIMIT_SEC if backend == "metal" else WHISPER_LIMIT_SEC,
        )
        ok = bool(run.transcript.segments)
        device_name = run.device_name
    except EngineError as exc:
        ok = False
        unsupported = exc.unsupported_gpu
        virtual = exc.virtual_mac
        device_name = exc.device_name
    except (OSError, ValueError, ModelMissing, ModelCorrupt):
        ok = False
    finally:
        owned.record("audio.wav", "raw.json")
        owned.cleanup(paths.user_dir)
    settings["backend_probe"] = {**identity, "ok": ok, "device_name": device_name}
    if unsupported:
        # The engine itself reported a GPU it cannot use, or this is a virtual
        # Mac where it never starts: not a failed run.
        settings["backend_probe"]["unsupported"] = True
    if virtual:
        settings["backend_probe"]["virtual_mac"] = True
    save_settings(settings_path, settings)
    return ok


def probe_vulkan(
    paths: RuntimePaths, registry: ModelRegistry, *, refresh: bool = False, model_id: str = "tiny"
) -> bool:
    """Historical name kept for callers: probes the platform GPU backend."""
    return probe_gpu(paths, registry, refresh=refresh, model_id=model_id)
