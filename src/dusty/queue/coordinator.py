"""Run one offline file at a time through the shared headless pipeline."""

import errno
import logging
import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.core.types import Cancellation, CollisionPolicy, EngineBackend
from dusty.engine.binaries import ffmpeg_path, ffprobe_path, gpu_backend, whisper_path
from dusty.models import Model, ModelCorrupt, ModelMissing, ModelRegistry, can_translate
from dusty.platform.power import prevent_sleep
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork, cleanup_owned, linked, managed_destination, protected_paths

from .outputs import OutputExistsError, output_targets, write_outputs
from .storage import StateSaveError, save_batch

_LOG = logging.getLogger("dusty")


@dataclass(frozen=True)
class _CancellationGroup:
    events: tuple[Cancellation, ...]

    def is_set(self) -> bool:
        return any(event.is_set() for event in self.events)


class UnsupportedOptions(ValueError):
    """The selected model cannot honor these batch options; nothing was started."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


ENGLISH_ONLY_LANGUAGES = frozenset({"auto", "en"})


def check_model_options(model: Model, options: BatchOptions) -> None:
    """Refuse task and language choices the selected model cannot honor."""
    if options.task == "translate" and not can_translate(model):
        raise UnsupportedOptions("Selected model cannot translate", "TRANSLATE_UNSUPPORTED")
    if options.language not in ENGLISH_ONLY_LANGUAGES and model.english_only:
        raise UnsupportedOptions("Selected model is English-only", "LANGUAGE_UNSUPPORTED")


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    """Device, file ID (inode on macOS, file index on Windows), size and mtime."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _source_lost(source: Path, identity: tuple[int, int, int, int]) -> FailureCode | None:
    """After decoding, refuse a recording that vanished or changed (D-MAC-023)."""
    try:
        current = source.stat()
    except FileNotFoundError:
        return FailureCode.NOT_FOUND
    except OSError:
        return FailureCode.UNREADABLE
    return None if _identity(current) == identity else FailureCode.UNREADABLE


def cleanup_orphaned_work(work_root: Path) -> None:
    """Preserve legacy/unrecognized work; remove only a matching owned inventory."""
    if linked(work_root) or not work_root.is_dir():
        return
    protected = protected_paths(work_root.parent)
    for candidate in work_root.iterdir():
        if candidate.is_dir():
            cleanup_owned(candidate, protected=protected, work_root=work_root)


class Coordinator:
    """Process a persisted batch, with per-file GPU fallback and cleanup."""

    def __init__(self, paths: RuntimePaths, registry: ModelRegistry):
        self.paths = paths
        self.registry = registry
        self.state_path = paths.user_dir / "state/queue.json"
        self.work_root = paths.user_dir / "work"

    @prevent_sleep()
    def run_batch(
        self,
        jobs: list[Job],
        options: BatchOptions,
        *,
        cancel: threading.Event | None = None,
        cancel_current: threading.Event | None = None,
        on_change: Callable[[Job], None] | None = None,
        vulkan_ok: bool | None = None,
        on_collision: Callable[[Job], CollisionPolicy] | None = None,
    ) -> list[Job]:
        """Save every transition; preserve finished jobs on restart."""
        check_model_options(self.registry.manifest.models[options.model_id], options)
        if options.threads < 1:
            raise ValueError("Threads must be positive")
        for job in jobs:
            if managed_destination(job.source, self.paths) or any(
                managed_destination(target, self.paths)
                for target in output_targets(job, replace(options, collision="overwrite"))
            ):
                raise ValueError("Managed folders cannot contain recordings or transcripts")
        self.work_root.mkdir(parents=True, exist_ok=True)
        save_batch(self.state_path, options, jobs)
        preexisting = {
            target.resolve()
            for entry in jobs
            for target in output_targets(entry, replace(options, collision="overwrite"))
            if target.exists()
        }
        produced: set[Path] = set()
        claimed = {
            target.resolve()
            for entry in jobs
            if entry.status in {JobStatus.DONE, JobStatus.SKIPPED}
            for target in output_targets(entry, replace(options, collision="overwrite"))
        }
        for job in jobs:
            if job.status in {JobStatus.DONE, JobStatus.SKIPPED}:
                continue
            if cancel and cancel.is_set():
                job.status = JobStatus.CANCELLED
                save_batch(self.state_path, options, jobs)
                continue

            job.elapsed_sec = 0.0

            signals = _CancellationGroup(
                tuple(event for event in (cancel, cancel_current) if event)
            )
            current_options = options
            nominal = output_targets(job, replace(options, collision="overwrite"))
            existing = [target for target in nominal if target.exists()]
            prior = [
                target
                for target in existing
                if target.resolve() in preexisting and target.resolve() not in produced
            ]
            repeated_name = any(target.resolve() in claimed for target in nominal)
            claimed.update(target.resolve() for target in nominal)
            skip_existing = False
            if repeated_name or (existing and not prior):
                current_options = replace(options, collision="keep_both")
            elif prior and options.collision == "ask" and on_collision:
                decision = on_collision(replace(job, outputs=prior))
                current_options = replace(options, collision=decision)
                skip_existing = decision == "skip"
            elif prior and options.collision in {"skip", "ask"}:
                skip_existing = True
            # Skip, an Ask answered with Skip, or an Ask with nobody to answer is
            # decided before any probing, decoding or inference, so no native
            # process starts for a file that is skipped.
            if cancel and cancel.is_set():
                job.status = JobStatus.CANCELLED
                self._changed(job, options, jobs, on_change)
                continue
            try:
                job_started = time.monotonic()

                def changed(current: Job = job, started: float = job_started) -> None:
                    current.elapsed_sec = time.monotonic() - started
                    self._changed(current, options, jobs, on_change)

                job.failure = None
                job.progress = 0.0
                job.gpu_fallback = False
                if skip_existing:
                    job.failure = FailureCode.OUTPUT_EXISTS_SKIPPED
                    job.status = JobStatus.SKIPPED
                    changed()
                    continue
                self._run_one(job, current_options, signals, vulkan_ok, changed)
                if job.status == JobStatus.DONE:
                    produced.update(path.resolve() for path in job.outputs)
            except StateSaveError:
                job.failure = FailureCode.STATE_SAVE_FAILED
                job.status = JobStatus.FAILED
                if on_change:
                    on_change(job)
                break  # Do not run more files without a durable recovery record.
            finally:
                if cancel_current:
                    cancel_current.clear()
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
        cancel: Cancellation | None,
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

        owned = OwnedWork(self.work_root, "job")
        work = owned.path
        identity: tuple[int, int, int, int] | None = None
        try:
            job.status = JobStatus.PREFLIGHT
            changed()
            if not job.source.is_file():
                job.failure = FailureCode.NOT_FOUND
                return
            try:
                info = job.source.stat()
                size = info.st_size
                with job.source.open("rb"):
                    pass
            except OSError:
                job.failure = FailureCode.UNREADABLE
                return
            identity = _identity(info)
            if size == 0:
                job.failure = FailureCode.EMPTY_FILE
                return
            model = self.registry.model_path(options.model_id)
            vad = self.registry.vad_path() if options.vad else None
            probe = probe_audio(ffprobe_path(self.paths.bin_dir), job.source, cancel=cancel)
            if not probe.has_audio:
                job.failure = FailureCode.NO_AUDIO
                return
            job.duration_sec = probe.duration_sec
            estimated_wav = int(probe.duration_sec * 16000 * 2 + 4096)
            if shutil.disk_usage(work).free < estimated_wav * 2:
                job.failure = FailureCode.DISK_FULL
                return
            job.status = JobStatus.DECODING
            changed()
            wav = work / "audio.wav"
            decode_sec = transcode_audio(
                ffmpeg_path(self.paths.bin_dir), job.source, wav, cancel=cancel
            )
            owned.record("audio.wav")
            lost = _source_lost(job.source, identity)
            if lost:
                job.failure = lost
                return
            if probe.duration_sec == 0:
                probe = probe_audio(ffprobe_path(self.paths.bin_dir), wav, cancel=cancel)
                job.duration_sec = probe.duration_sec
            job.status = JobStatus.TRANSCRIBING
            changed()
            # vulkan_ok means the platform GPU probe passed. Any explicit GPU request
            # runs this platform's single GPU backend; backend_used records which.
            backend: EngineBackend = (
                "cpu"
                if options.backend == "cpu" or (options.backend == "auto" and not vulkan_ok)
                else gpu_backend()
            )
            executable = whisper_path(self.paths.bin_dir, backend)

            def progress(value: float) -> None:
                job.progress = value
                changed()

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
                    on_progress=progress,
                )
            except EngineError as exc:
                if backend == "cpu" or not exc.gpu_error or (cancel and cancel.is_set()):
                    raise
                job.gpu_fallback = True
                job.progress = 0.0
                backend = "cpu"
                result = run_whisper(
                    whisper_path(self.paths.bin_dir, "cpu"),
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
                    on_progress=progress,
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
            # SPEC 5.9: future extension hook after parsing, before export.
            # V1 does not execute diarization or text-translation extensions.
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
        except DecoderError as exc:
            if cancel and cancel.is_set():
                job.status = JobStatus.CANCELLED
            elif exc.disk_full:
                job.failure = FailureCode.DISK_FULL
            elif exc.unreadable:
                lost = _source_lost(job.source, identity) if identity else None
                job.failure = lost or FailureCode.UNREADABLE
            else:
                job.failure = FailureCode.DECODE_ERROR
        except EngineError as exc:
            job.failure = FailureCode.GPU_ERROR if exc.gpu_error else FailureCode.ENGINE_ERROR
            if exc.cancelled:
                job.status = JobStatus.CANCELLED
                job.failure = None
        except StateSaveError:
            raise
        except OSError as exc:
            job.failure = (
                FailureCode.DISK_FULL
                if exc.errno == errno.ENOSPC or getattr(exc, "winerror", None) == 112
                else FailureCode.OUTPUT_UNWRITABLE
            )
        except Exception:
            job.failure = FailureCode.INTERNAL_ERROR
        finally:
            if job.failure and job.status not in {JobStatus.SKIPPED, JobStatus.CANCELLED}:
                job.status = JobStatus.FAILED
            owned.record("audio.wav", "raw.json")
            owned.cleanup(self.paths.user_dir)
            changed()
