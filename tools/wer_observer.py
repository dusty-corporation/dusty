"""Observe real WER stores only on an explicitly enabled disposable CI host."""

import os
from collections.abc import Mapping
from pathlib import Path

EXCLUDED_NAMES = (
    "dusty.exe",
    "dusty-fetch.exe",
    "whisper-cli.exe",
    "ffmpeg.exe",
    "ffprobe.exe",
)
EXCLUSION_KEY = r"Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications"
AREAS = ("ReportQueue", "ReportArchive", "Temp")


def require_disposable_ci(environment: Mapping[str, str]) -> None:
    if not (
        environment.get("GITHUB_ACTIONS") == "true"
        and environment.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and environment.get("DUSTY_WER_ACCEPTANCE") == "1"
    ):
        raise RuntimeError("Deliberate crashes require the disposable hosted CI acceptance step")


def snapshot(roots: tuple[Path, ...]) -> tuple[dict[Path, tuple[int, int]], dict[str, str]]:
    """Fail on access errors rather than calling an unreadable store empty."""
    reports: dict[Path, tuple[int, int]] = {}
    states: dict[str, str] = {}

    def inspect(folder: Path) -> None:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_symlink():
                    raise OSError("Linked WER store cannot be proven")
                if entry.is_dir(follow_symlinks=False):
                    inspect(Path(entry.path))
                elif entry.name.casefold() == "report.wer":
                    info = entry.stat(follow_symlinks=False)
                    reports[Path(entry.path)] = (info.st_size, info.st_mtime_ns)

    for index, root in enumerate(roots):
        for area in AREAS:
            label = f"{'user' if index == 0 else 'machine'}/{area}"
            folder = root / area
            try:
                folder.stat()
            except FileNotFoundError:
                states[label] = "absent"
                continue
            inspect(folder)  # Permission or enumeration errors are never ignored.
            states[label] = "readable"
    return reports, states
