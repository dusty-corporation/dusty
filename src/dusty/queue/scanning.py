"""Collect supported local recordings without duplicates or network access."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from dusty.core import Job

SUPPORTED_EXTENSIONS = frozenset(
    "." + extension
    for extension in (
        "mp3 m4a aac wav flac ogg oga opus wma webm mp4 m4v mov mkv avi 3gp amr".split()
    )
)


@dataclass(frozen=True)
class ScanResult:
    jobs: tuple[Job, ...]
    unsupported: int
    duplicates: int
    duplicate_paths: tuple[Path, ...] = ()
    rejected: int = 0


def scan_inputs(
    inputs: Iterable[Path], *, recursive: bool = False, existing: Iterable[Job] = ()
) -> ScanResult:
    """Scan in stable order; preserve directories relative to each selected root."""
    seen = {job.source.resolve() for job in existing}
    jobs = []
    duplicate_paths = []
    unsupported = duplicates = 0
    for source in inputs:
        root = source.resolve()
        candidates = (
            sorted(
                root.rglob("*") if recursive else root.iterdir(), key=lambda p: str(p).casefold()
            )
            if root.is_dir()
            else [root]
        )
        for candidate in candidates:
            if candidate.is_dir():
                continue
            if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
                unsupported += 1
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                duplicates += 1
                duplicate_paths.append(resolved)
                continue
            seen.add(resolved)
            relative_dir = candidate.parent.relative_to(root) if root.is_dir() else None
            jobs.append(Job(resolved, relative_dir=relative_dir))
    return ScanResult(tuple(jobs), unsupported, duplicates, tuple(duplicate_paths))
