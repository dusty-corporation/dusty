"""Qt workers call the shared offline core and emit immutable job snapshots."""

import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from dusty.core import BatchOptions, Job
from dusty.core.types import CollisionPolicy
from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry, cleanup_stale_partials
from dusty.queue import Coordinator, cleanup_orphaned_work, load_batch
from dusty.queue.scanning import scan_inputs
from dusty.queue.storage import load_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import managed_destination, sanitize_output


@dataclass
class Prepared:
    installed: tuple[str, ...]
    vulkan_ok: bool
    settings: dict[str, Any]
    recovered: tuple[BatchOptions, list[Job]] | None = None
    vad_installed: bool = True


class PrepareWorker(QThread):
    ready = Signal(object)
    failed = Signal()

    def __init__(
        self, paths: RuntimePaths, registry: ModelRegistry, *, refresh_probe: bool = False
    ):
        super().__init__()
        self.paths, self.registry = paths, registry
        self.refresh_probe = refresh_probe

    def run(self) -> None:
        from dusty.engine.backend import probe_vulkan

        try:
            sanitize_output(self.paths)
            cleanup_stale_partials(self.paths.models_dir)
            cleanup_orphaned_work(self.paths.user_dir / "work")
            installed = []
            for model_id in self.registry.manifest.models:
                if self.isInterruptionRequested():
                    return
                try:
                    self.registry.model_path(model_id)
                    installed.append(model_id)
                except (ModelMissing, ModelCorrupt):
                    continue
            try:
                self.registry.vad_path()
                vad_installed = True
            except (ModelMissing, ModelCorrupt):
                vad_installed = False
            probe_model = "tiny" if "tiny" in installed else next(iter(installed), "tiny")
            ok = bool(installed) and probe_vulkan(
                self.paths, self.registry, model_id=probe_model, refresh=self.refresh_probe
            )
            settings = load_settings(self.paths.user_dir / "settings.json")
            recovered = load_batch(self.paths.user_dir / "state/queue.json")
            self.ready.emit(Prepared(tuple(installed), ok, settings, recovered, vad_installed))
        except Exception:
            self.failed.emit()


class ScanWorker(QThread):
    ready = Signal(object)
    failed = Signal()

    def __init__(
        self,
        paths: list[Path],
        recursive: bool,
        existing: list[Job],
        runtime: RuntimePaths | None = None,
    ):
        super().__init__()
        self.paths, self.recursive, self.existing = paths, recursive, existing
        self.runtime = runtime

    def run(self) -> None:
        try:
            result = scan_inputs(self.paths, recursive=self.recursive, existing=self.existing)
            if self.runtime:
                allowed = tuple(
                    job for job in result.jobs if not managed_destination(job.source, self.runtime)
                )
                result = replace(result, jobs=allowed, rejected=len(result.jobs) - len(allowed))
                from dusty.engine import DecoderError, probe_audio

                for job in result.jobs:
                    if self.isInterruptionRequested():
                        return
                    try:
                        job.duration_sec = probe_audio(
                            self.runtime.bin_dir / "ffmpeg/ffprobe.exe", job.source
                        ).duration_sec
                    except (DecoderError, OSError):
                        pass
            self.ready.emit(result)
        except (OSError, ValueError):
            self.failed.emit()


class BatchWorker(QThread):
    changed = Signal(object)
    collision = Signal(object)
    failed = Signal()

    def __init__(
        self,
        paths: RuntimePaths,
        registry: ModelRegistry,
        jobs: list[Job],
        options: BatchOptions,
        vulkan_ok: bool,
    ):
        super().__init__()
        self.paths, self.registry, self.jobs = paths, registry, jobs
        self.options, self.vulkan_ok = options, vulkan_ok
        self.cancel_all = threading.Event()
        self.cancel_current = threading.Event()
        self._answer = threading.Event()
        self._policy: CollisionPolicy = "skip"
        self._remembered: CollisionPolicy | None = None

    def choose_collision(self, policy: CollisionPolicy, apply_all: bool) -> None:
        self._policy = policy
        if apply_all:
            self._remembered = policy
        self._answer.set()

    def _collision(self, job: Job) -> CollisionPolicy:
        if self._remembered:
            return self._remembered
        self._answer.clear()
        self.collision.emit(replace(job, outputs=list(job.outputs)))
        while not self._answer.wait(0.1):
            if self.cancel_all.is_set():
                return "skip"
        return self._policy

    def _changed(self, job: Job) -> None:
        self.changed.emit(replace(job, outputs=list(job.outputs)))

    def run(self) -> None:
        try:
            Coordinator(self.paths, self.registry).run_batch(
                self.jobs,
                self.options,
                cancel=self.cancel_all,
                cancel_current=self.cancel_current,
                on_change=self._changed,
                on_collision=self._collision,
                vulkan_ok=self.vulkan_ok,
            )
        except Exception:
            self.failed.emit()


class SelfTestWorker(QThread):
    result = Signal(bool)

    def __init__(self, paths: RuntimePaths, model_id: str):
        super().__init__()
        self.paths, self.model_id = paths, model_id

    def run(self) -> None:
        from dusty.selftest import run_selftest

        self.result.emit(run_selftest(self.paths, self.model_id) == "OK")
