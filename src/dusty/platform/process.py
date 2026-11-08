"""Platform-neutral contract for starting Dusty's fixed native programs.

The Windows runner (win_process) and the macOS runner (mac_process) share the
result type, the executable approval rule and the in-memory line parser kept
here. run_job_process picks the runner for the current platform; there is no
generic launch API.
"""

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dusty.core.types import Cancellation

UNSUPPORTED_PLATFORM = "Native process runner unavailable on this platform"


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    elapsed_sec: float
    cancelled: bool


class JobRunner(Protocol):
    def __call__(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        on_stderr: Callable[[str], None] | None = None,
        on_stdout: Callable[[str], None] | None = None,
        cancel: Cancellation | None = None,
        timeout_sec: float | None = None,
        on_poll: Callable[[], None] | None = None,
    ) -> ProcessResult: ...


def approved_executable(path: Path) -> Path:
    """One launch boundary for processing binaries and the isolated downloader."""
    from dusty.runtime_paths import resolve_fetch_command, resolve_paths
    from dusty.work_area import canonical, linked

    executable = canonical(path)
    allowed = {
        canonical(Path(sys.executable)),
        canonical(Path(resolve_fetch_command()[0])),
    }
    if linked(path) or not (
        executable in allowed or executable.is_relative_to(canonical(resolve_paths().bin_dir))
    ):
        raise ValueError("Executable is not approved")
    return executable


def _read_lines(fd: int, callback: Callable[[str], None] | None) -> None:
    """Parse lines in memory and discard raw native output immediately."""
    buffer = b""
    with os.fdopen(fd, "rb", closefd=True) as stream:
        while chunk := os.read(stream.fileno(), 4096):
            buffer += chunk
            while b"\n" in buffer or b"\r" in buffer:
                newline = buffer.find(b"\n")
                carriage = buffer.find(b"\r")
                indices = [index for index in (newline, carriage) if index >= 0]
                split_at = min(indices)
                line, buffer = buffer[:split_at], buffer[split_at + 1 :]
                if callback and line:
                    callback(line.decode("utf-8", errors="replace"))
            if len(buffer) > 65536:
                buffer = buffer[-65536:]
        if callback and buffer:
            callback(buffer.decode("utf-8", errors="replace"))


def platform_runner(platform: str | None = None) -> JobRunner:
    """Import only the runner for the requested platform, defaulting to this one."""
    selected = sys.platform if platform is None else platform
    if selected == "win32":
        from dusty.platform.win_process import run_job_process as run_windows

        return run_windows
    if selected == "darwin":
        from dusty.platform.mac_process import run_job_process as run_mac

        return run_mac
    raise OSError(UNSUPPORTED_PLATFORM)


def run_job_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    on_stderr: Callable[[str], None] | None = None,
    on_stdout: Callable[[str], None] | None = None,
    cancel: Cancellation | None = None,
    timeout_sec: float | None = None,
    on_poll: Callable[[], None] | None = None,
) -> ProcessResult:
    """Run one approved program with the platform's kill-on-close boundary."""
    return platform_runner()(
        args,
        cwd=cwd,
        on_stderr=on_stderr,
        on_stdout=on_stdout,
        cancel=cancel,
        timeout_sec=timeout_sec,
        on_poll=on_poll,
    )
