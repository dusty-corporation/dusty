"""Run one offline file at a time through the shared headless pipeline."""

import logging
import shutil
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry, can_translate
from dusty.runtime_paths import RuntimePaths

from .outputs import OutputExistsError, write_outputs
from .storage import save_batch

_LOG = logging.getLogger("dusty")


def cleanup_orphaned_work(work_root: Path) -> None:
    """Remove only UUID-shaped abandoned per-job work directories."""
    from uuid import UUID

    if not work_root.is_dir():
        return
    for candidate in work_root.iterdir():
        if candidate.is_dir():
            try:
                UUID(candidate.name)
            except ValueError:
                continue
            shutil.rmtree(candidate)


class Coordinator:
    """Process a persisted batch, with per-file GPU fallback and cleanup."""

    def __init__(self, paths: RuntimePaths, registry: ModelRegistry):
        self.paths = paths
        self.registry = registry
        self.state_path = paths.user_dir / "state/queue.json"
        self.work_root = paths.user_dir / "work"

    def run_batch(
        self,
        jobs: list[Job],
        options: BatchOptions,
        *,
        cancel: threading.Event | None = None,
        on_change: Callable[[Job], None] | None = None,
        vulkan_ok: bool | None = None,
    ) -> list[Job]:
        """Save every transition; preserve finished jobs on restart."""
        if options.task == "translate" and not can_translate(
            self.registry.manifest.models[options.model_id]
        ):
            raise ValueError("Selected model cannot translate")
        if options.threads < 1:
            raise ValueError("Threads must be positive")
        self.work_root.mkdir(parents=True, exist_ok=True)
        save_batch(self.state_path, options, jobs)
        for job in jobs:
            if job.status in {JobStatus.DONE, JobStatus.SKIPPED}:
                continue
            if cancel and cancel.is_set():
                job.status = JobStatus.CANCELLED
                save_batch(self.state_path, options, jobs)
                continue

            def changed(current: Job = job) -> None:
                self._changed(current, options, jobs, on_change)

            self._run_one(
                job,
                options,
                cancel,
                vulkan_ok,
                changed,
            )
        return jobs

    def _changed(
        self,
        job: Job,
        options: BatchOptions,
        jobs: list[Job],
        callback: Callable[[Job], None] | None,
    ) -> None:
        save_batch(self.state_path, options, jobs)
        _LOG.info("job_id=%s status=%s", job.id, job.status.value)
        if callback:
            callback(job)

    def _run_one(
        self,
        job: Job,
        options: BatchOptions,
        cancel: threading.Event | None,
        vulkan_ok: bool | None,
        changed: Callable[[], None],
    ) -> None:
        from dusty.engine import (
            DecoderError,
            EngineError,
            probe_audio,
            run_whisper,
            transcode_audio,
        )

        work = self.work_root / str(job.id)
        work.mkdir(parents=True, exist_ok=False)
        try:
            job.status = JobStatus.PREFLIGHT
            changed()
            if not job.source.is_file():
                job.failure = FailureCode.NOT_FOUND
                return
            try:
                size = job.source.stat().st_size
                with job.source.open("rb"):
                    pass
            except OSError:
                job.failure = FailureCode.UNREADABLE
                return
            if size == 0:
                job.failure = FailureCode.EMPTY_FILE
                return
            model = self.registry.model_path(options.model_id)
            vad = self.registry.vad_path() if options.vad else None
            probe = probe_audio(
                self.paths.bin_dir / "ffmpeg/ffprobe.exe", job.source, cancel=cancel
            )
            if not probe.has_audio:
                job.failure = FailureCode.NO_AUDIO
                return
            estimated_wav = int(probe.duration_sec * 16000 * 2 + 4096)
            if shutil.disk_usage(work).free < estimated_wav * 2:
                job.failure = FailureCode.DISK_FULL
                return
            job.status = JobStatus.DECODING
            changed()
            wav = work / "audio.wav"
            decode_sec = transcode_audio(
                self.paths.bin_dir / "ffmpeg/ffmpeg.exe", job.source, wav, cancel=cancel
            )
            job.status = JobStatus.TRANSCRIBING
            changed()
            backend: Literal["cpu", "vulkan"] = (
                "cpu"
                if options.backend == "cpu" or (options.backend == "auto" and not vulkan_ok)
                else "vulkan"
            )
            executable = self.paths.bin_dir / backend / "whisper-cli.exe"
            try:
                result = run_whisper(
                    executable,
                    model,
                    wav,
                    work / "raw",
                    model_id=options.model_id,
                    task=options.task,
                    language=options.language,
                    threads=options.threads,
                    duration_sec=probe.duration_sec,
                    backend=backend,
                    vad_model=vad,
                    prompt=options.prompt,
                    cancel=cancel,
                )
            except EngineError as exc:
                if backend != "vulkan" or not exc.gpu_error or (cancel and cancel.is_set()):
                    raise
                job.gpu_fallback = True
                backend = "cpu"
                result = run_whisper(
                    self.paths.bin_dir / "cpu/whisper-cli.exe",
                    model,
                    wav,
                    work / "raw",
                    model_id=options.model_id,
                    task=options.task,
                    language=options.language,
                    threads=options.threads,
                    duration_sec=probe.duration_sec,
                    backend="cpu",
                    vad_model=vad,
                    prompt=options.prompt,
                    cancel=cancel,
                )
            job.backend_used = backend
            _LOG.info(
                "job_id=%s model=%s backend=%s decode_sec=%.3f "
                "process_sec=%.3f first_progress_sec=%.3f",
                job.id,
                options.model_id,
                backend,
                decode_sec,
                result.process_sec,
                result.first_progress_sec or 0.0,
            )
            for name, milliseconds in result.timings_ms.items():
                _LOG.info("job_id=%s timing_%s_ms=%.3f", job.id, name, milliseconds)
            job.status = JobStatus.EXPORTING
            changed()
            job.outputs = write_outputs(job, options, result.transcript)
            job.progress = 1.0
            job.status = JobStatus.DONE
        except ModelMissing:
            job.failure = FailureCode.MODEL_MISSING
        except ModelCorrupt:
            job.failure = FailureCode.MODEL_CORRUPT
        except OutputExistsError:
            job.failure = FailureCode.OUTPUT_EXISTS_SKIPPED
            job.status = JobStatus.SKIPPED
        except DecoderError:
            if cancel and cancel.is_set():
                job.status = JobStatus.CANCELLED
            else:
                job.failure = FailureCode.DECODE_ERROR
        except EngineError as exc:
            job.failure = FailureCode.GPU_ERROR if exc.gpu_error else FailureCode.ENGINE_ERROR
            if exc.cancelled:
                job.status = JobStatus.CANCELLED
                job.failure = None
        except OSError:
            job.failure = FailureCode.OUTPUT_UNWRITABLE
        except Exception:
            job.failure = FailureCode.INTERNAL_ERROR
        finally:
            if job.failure and job.status not in {JobStatus.SKIPPED, JobStatus.CANCELLED}:
                job.status = JobStatus.FAILED
            shutil.rmtree(work)
            changed()
