"""Start approved native programs on macOS under the dusty-lifeline helper.

This mirrors win_process (ADR 0037). Windows puts each child in a kill-on-close
Job Object; here each child runs under dusty-lifeline, which holds the read end
of a control pipe and kills the child's whole process group when the pipe
reaches end of file. Only this process holds the write end, so cancel, timeout
and the death of the app (including SIGKILL) all end the child's group.

The helper is started with libc posix_spawn through ctypes, just as Windows uses
CreateProcessW through ctypes, so the audit guard that blocks subprocess and
os.posix_spawn stays installed and unchanged. Nothing here logs arguments,
paths or program output.

Every launch gets an explicit environment built here and passed to posix_spawn;
the helper hands it to the target unchanged. Nothing from the app's own
environment is inherited. Processing programs get only LC_ALL=C and the
isolated downloader gets the set chosen by resolve_fetch_environment.
"""

import ctypes
import errno
import fcntl
import os
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from dusty.core.types import Cancellation
from dusty.platform.process import ProcessResult, _read_lines, approved_executable

# macOS only. On Windows the fcntl import above already fails; this check also
# tells type checkers on Windows that the rest of the module is macOS only.
if sys.platform == "win32":
    raise ImportError("dusty.platform.mac_process is macOS only")

POSIX_SPAWN_SETPGROUP = 0x0002
POSIX_SPAWN_SETSIGDEF = 0x0004
POSIX_SPAWN_SETSIGMASK = 0x0008
POSIX_SPAWN_CLOEXEC_DEFAULT = 0x4000  # Apple: only file-action descriptors survive.
CONTROL_FD = 3  # The helper reads its control pipe here; see lifeline.c.
_FIRST_SPARE_FD = 10  # Child-side descriptors are moved here so dup2 never collides.
_POLL_SEC = 0.1
_REAP_SEC = 5.0
# Every catchable signal starts with its default action in the helper, so that
# Python's own settings (for example SIGPIPE ignored) never reach native code.
_DEFAULT_SIGNALS = sum(
    1 << (number - 1) for number in range(1, 32) if number not in (signal.SIGKILL, signal.SIGSTOP)
)

_SpawnObject = ctypes.c_void_p  # posix_spawnattr_t and posix_spawn_file_actions_t
_SignalSet = ctypes.c_uint32  # sigset_t
_Pointer = ctypes.POINTER(_SpawnObject)

_libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
for _name, _argtypes in {
    "posix_spawn_file_actions_init": [_Pointer],
    "posix_spawn_file_actions_destroy": [_Pointer],
    "posix_spawn_file_actions_adddup2": [_Pointer, ctypes.c_int, ctypes.c_int],
    "posix_spawn_file_actions_addchdir_np": [_Pointer, ctypes.c_char_p],
    "posix_spawnattr_init": [_Pointer],
    "posix_spawnattr_destroy": [_Pointer],
    "posix_spawnattr_setflags": [_Pointer, ctypes.c_short],
    "posix_spawnattr_setpgroup": [_Pointer, ctypes.c_int32],
    "posix_spawnattr_setsigdefault": [_Pointer, ctypes.POINTER(_SignalSet)],
    "posix_spawnattr_setsigmask": [_Pointer, ctypes.POINTER(_SignalSet)],
    "posix_spawn": [
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_char_p,
        _Pointer,
        _Pointer,
        ctypes.POINTER(ctypes.c_char_p),
        ctypes.POINTER(ctypes.c_char_p),
    ],
}.items():
    getattr(_libc, _name).argtypes = _argtypes
    getattr(_libc, _name).restype = ctypes.c_int


def _check(result: int, operation: str) -> None:
    """posix_spawn functions return an error number instead of setting errno."""
    if result:
        raise OSError(result, f"macOS process operation failed: {operation}")


def _require_program(path: Path) -> None:
    if not path.is_file():
        raise OSError(errno.ENOENT, "macOS process operation failed: program missing")
    if not os.access(path, os.X_OK):
        raise OSError(errno.EACCES, "macOS process operation failed: program not executable")


def _wait(pid: int, seconds: float) -> int | None:
    """Return the raw wait status once the helper exits, or None after seconds."""
    deadline = time.monotonic() + seconds
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            return status
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.005)


def _reap(pid: int) -> int:
    """Wait a bounded time for the helper; it only ever needs milliseconds."""
    status = _wait(pid, _REAP_SEC)
    if status is None:
        os.kill(pid, signal.SIGKILL)
        status = os.waitpid(pid, 0)[1]
    return status


def _exit_code(status: int) -> int:
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code


def _array(items: list[bytes]) -> "ctypes.Array[ctypes.c_char_p]":
    return (ctypes.c_char_p * (len(items) + 1))(*items, None)


PROCESSING_ENVIRONMENT = {"LC_ALL": "C"}


def child_environment(executable: Path) -> dict[str, str]:
    """Choose the complete environment for one approved, canonical executable."""
    from dusty.runtime_paths import resolve_fetch_command, resolve_fetch_environment, resolve_paths
    from dusty.work_area import canonical

    if executable.is_relative_to(canonical(resolve_paths().bin_dir)):
        return dict(PROCESSING_ENVIRONMENT)
    if executable == canonical(Path(resolve_fetch_command()[0])):
        return resolve_fetch_environment()
    return dict(PROCESSING_ENVIRONMENT)


def _environment_block(environment: dict[str, str]) -> list[bytes]:
    block = []
    for name, value in sorted(environment.items()):
        if not name or "=" in name:
            raise ValueError("Environment names must be non-empty and contain no equals sign")
        block.append(os.fsencode(name) + b"=" + os.fsencode(value))
    return block


def run_job_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    on_stderr: Callable[[str], None] | None = None,
    on_stdout: Callable[[str], None] | None = None,
    cancel: Cancellation | None = None,
    timeout_sec: float | None = None,
    on_poll: Callable[[], None] | None = None,
    environment: Mapping[str, str] | None = None,
) -> ProcessResult:
    """Run a child only under a lifeline helper that owns its process group."""
    if not args or not Path(args[0]).is_absolute():
        raise ValueError("Executable must have an absolute path")
    executable = approved_executable(Path(args[0]))
    if cwd is not None and cwd.resolve() != executable.parent:
        raise ValueError("Child working directory must be its executable folder")
    from dusty.engine.binaries import lifeline_path
    from dusty.runtime_paths import resolve_paths

    lifeline = approved_executable(lifeline_path(resolve_paths().bin_dir))
    _require_program(lifeline)
    _require_program(executable)
    argv = [
        os.fsencode(lifeline),
        str(CONTROL_FD).encode(),
        os.fsencode(executable),
        *(os.fsencode(argument) for argument in args[1:]),
    ]
    chosen = dict(environment) if environment is not None else child_environment(executable)
    block = _environment_block(chosen)
    if any(b"\0" in item for item in (*argv, *block)):
        raise ValueError("Arguments must not contain NUL characters")

    opened: list[int] = []  # Every descriptor this call still has to close.

    def track(fd: int) -> int:
        opened.append(fd)
        return fd

    def spare(fd: int) -> int:
        """Move a child-side descriptor above the numbers the child will use."""
        try:
            return track(fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, _FIRST_SPARE_FD))
        finally:
            os.close(fd)

    def release(fd: int) -> None:
        opened.remove(fd)
        os.close(fd)

    actions = _SpawnObject()
    attributes = _SpawnObject()
    actions_ready = attributes_ready = False
    readers: list[threading.Thread] = []
    pid = 0
    control_write = -1
    started = time.monotonic()
    cancelled = False
    try:
        child_stdin = spare(os.open(os.devnull, os.O_RDONLY | os.O_CLOEXEC))
        stderr_read, stderr_write = os.pipe()
        track(stderr_read)
        stderr_write = spare(stderr_write)
        stdout_read = -1
        if on_stdout:
            stdout_read, stdout_write = os.pipe()
            track(stdout_read)
            child_stdout = spare(stdout_write)
        else:
            child_stdout = spare(os.open(os.devnull, os.O_WRONLY | os.O_CLOEXEC))
        control_read, control_write = os.pipe()
        control_read = spare(control_read)

        _check(_libc.posix_spawn_file_actions_init(ctypes.byref(actions)), "file actions")
        actions_ready = True
        for source, target in (
            (child_stdin, 0),
            (child_stdout, 1),
            (stderr_write, 2),
            (control_read, CONTROL_FD),
        ):
            _check(
                _libc.posix_spawn_file_actions_adddup2(ctypes.byref(actions), source, target),
                "file actions",
            )
        _check(
            _libc.posix_spawn_file_actions_addchdir_np(
                ctypes.byref(actions), os.fsencode(executable.parent)
            ),
            "file actions",
        )
        _check(_libc.posix_spawnattr_init(ctypes.byref(attributes)), "attributes")
        attributes_ready = True
        flags = (
            POSIX_SPAWN_SETPGROUP
            | POSIX_SPAWN_SETSIGDEF
            | POSIX_SPAWN_SETSIGMASK
            | POSIX_SPAWN_CLOEXEC_DEFAULT
        )
        default_signals = _SignalSet(_DEFAULT_SIGNALS)
        no_signals = _SignalSet(0)
        _check(_libc.posix_spawnattr_setflags(ctypes.byref(attributes), flags), "attributes")
        _check(_libc.posix_spawnattr_setpgroup(ctypes.byref(attributes), 0), "attributes")
        _check(
            _libc.posix_spawnattr_setsigdefault(
                ctypes.byref(attributes), ctypes.byref(default_signals)
            ),
            "attributes",
        )
        _check(
            _libc.posix_spawnattr_setsigmask(ctypes.byref(attributes), ctypes.byref(no_signals)),
            "attributes",
        )
        child = ctypes.c_int32()
        _check(
            _libc.posix_spawn(
                ctypes.byref(child),
                argv[0],
                ctypes.byref(actions),
                ctypes.byref(attributes),
                _array(argv),
                _array(block),  # The helper passes it to the target unchanged.
            ),
            "posix_spawn",
        )
        pid = child.value
        for fd in (child_stdin, child_stdout, stderr_write, control_read):
            release(fd)
        stderr_reader = threading.Thread(
            target=_read_lines, args=(stderr_read, on_stderr), daemon=True
        )
        stderr_reader.start()
        readers.append(stderr_reader)
        opened.remove(stderr_read)
        if on_stdout:
            stdout_reader = threading.Thread(
                target=_read_lines, args=(stdout_read, on_stdout), daemon=True
            )
            stdout_reader.start()
            readers.append(stdout_reader)
            opened.remove(stdout_read)
        while True:
            status = _wait(pid, _POLL_SEC)
            if status is not None:
                break
            if on_poll:
                on_poll()
            if (
                cancel
                and cancel.is_set()
                or timeout_sec
                and time.monotonic() - started > timeout_sec
            ):
                cancelled = True
                os.close(control_write)  # End of file tells the helper to kill the group.
                control_write = -1
                status = _reap(pid)
                break
        pid = 0
        for reader in readers:
            reader.join(timeout=5)
        if on_poll:
            on_poll()
        return ProcessResult(_exit_code(status), time.monotonic() - started, cancelled)
    finally:
        if control_write >= 0:
            os.close(control_write)
        if pid > 0:
            # An error after the spawn: the closed pipe has already told the
            # helper to kill the group, so only the helper is left to reap.
            try:
                _reap(pid)
            except OSError:
                pass
        for fd in opened:
            os.close(fd)
        if actions_ready:
            _libc.posix_spawn_file_actions_destroy(ctypes.byref(actions))
        if attributes_ready:
            _libc.posix_spawnattr_destroy(ctypes.byref(attributes))
