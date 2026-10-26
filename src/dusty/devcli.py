"""Development-only headless entry point for the shared offline coordinator."""

import argparse
import sys
from pathlib import Path
from typing import cast

from dusty.core import BatchOptions, JobStatus
from dusty.core.types import Backend, CollisionPolicy, OutputFormat, Task
from dusty.engine.backend import probe_vulkan
from dusty.models import ModelRegistry, load_manifest
from dusty.platform.cpu_topology import default_threads
from dusty.privacy.logging import configure_logger
from dusty.privacy.sync import is_synced
from dusty.queue import Coordinator, cleanup_orphaned_work
from dusty.queue.scanning import scan_inputs
from dusty.runtime_paths import resolve_paths


def transcribe(
    files: list[Path],
    out: Path,
    *,
    model: str,
    backend: Backend,
    formats: tuple[OutputFormat, ...],
    language: str = "auto",
    task: Task = "transcribe",
    threads: int | None = None,
    vad: bool = False,
    prompt: str = "",
    collision: CollisionPolicy = "ask",
    recursive: bool = False,
    keep_structure: bool = False,
) -> int:
    paths = resolve_paths()
    configure_logger(paths.user_dir)
    cleanup_orphaned_work(paths.user_dir / "work")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    if model not in registry.manifest.models:
        print("MODEL_UNKNOWN")
        return 2
    if not formats or len(set(formats)) != len(formats):
        print("FORMATS_INVALID")
        return 2
    if is_synced(out):
        print("Warning: this output folder may sync files to a cloud service.")
    if len(prompt) / 4 > 200:
        print("Warning: vocabulary hints may exceed the engine prompt window.")
    vulkan_ok = probe_vulkan(paths, registry) if backend in {"auto", "vulkan"} else False
    options = BatchOptions(
        model_id=model,
        output_dir=out,
        formats=formats,
        language=language,
        task=task,
        backend=backend,
        threads=default_threads() if threads is None else threads,
        vad=vad,
        prompt=prompt,
        collision=collision,
        keep_structure=keep_structure,
    )
    scanned = scan_inputs(files, recursive=recursive)
    jobs = list(scanned.jobs)
    print(f"added={len(jobs)} unsupported={scanned.unsupported} duplicates={scanned.duplicates}")
    if not jobs:
        return 1
    Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=vulkan_ok)
    for job in jobs:
        print(f"{job.status.value} {job.failure.value if job.failure else 'OK'}")
    return 0 if all(job.status == JobStatus.DONE for job in jobs) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m dusty.devcli")
    parser.add_argument("action", choices=("transcribe",))
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "cpu", "vulkan"), default="auto")
    parser.add_argument("--format", action="append", choices=("txt", "srt", "vtt", "json", "docx"))
    parser.add_argument("--language", default="auto")
    parser.add_argument("--task", choices=("transcribe", "translate"), default="transcribe")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--vad", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--keep-structure", action="store_true")
    parser.add_argument("--prompt", default="")
    parser.add_argument(
        "--collision", choices=("ask", "skip", "overwrite", "keep_both"), default="ask"
    )
    args = parser.parse_args(argv)
    return transcribe(
        args.files,
        args.out,
        model=args.model,
        backend=cast(Backend, args.backend),
        formats=cast(tuple[OutputFormat, ...], tuple(args.format or ("txt", "docx"))),
        language=args.language,
        task=cast(Task, args.task),
        threads=args.threads,
        vad=args.vad,
        prompt=args.prompt,
        collision=cast(CollisionPolicy, args.collision),
        recursive=args.recursive,
        keep_structure=args.keep_structure,
    )


if __name__ == "__main__":
    sys.exit(main())
