"""Start suspended children inside kill-on-close Windows Job Objects."""

import ctypes
import msvcrt
import os
import subprocess
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from dusty.core.types import Cancellation

CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258


class BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_uint64)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BasicLimitInformation),
        ("IoInfo", IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    elapsed_sec: float
    cancelled: bool


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.SetInformationJobObject.argtypes = [
    wintypes.HANDLE,
    wintypes.INT,
    ctypes.c_void_p,
    wintypes.DWORD,
]
_kernel32.SetInformationJobObject.restype = wintypes.BOOL
_kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.POINTER(StartupInfo),
    ctypes.POINTER(ProcessInformation),
]
_kernel32.CreateProcessW.restype = wintypes.BOOL
_kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
_kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
_kernel32.ResumeThread.restype = wintypes.DWORD
_kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_kernel32.GetExitCodeProcess.restype = wintypes.BOOL
_kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
_kernel32.TerminateJobObject.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


def _check(value: int, operation: str) -> None:
    if not value:
        code = ctypes.get_last_error()
        raise OSError(code, f"Windows process operation failed: {operation}")


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
    """Run a child only after attaching it to a kill-on-close Job Object."""
    if not args or not Path(args[0]).is_absolute():
        raise ValueError("Executable must have an absolute path")
    job = _kernel32.CreateJobObjectW(None, None)
    _check(job, "CreateJobObjectW")
    process = ProcessInformation()
    readers: list[threading.Thread] = []
    read_fd, write_fd = os.pipe()
    os.set_inheritable(read_fd, False)
    os.set_inheritable(write_fd, True)
    stdout_read_fd = -1
    stdout_write_fd = -1
    if on_stdout:
        stdout_read_fd, stdout_write_fd = os.pipe()
        os.set_inheritable(stdout_read_fd, False)
        os.set_inheritable(stdout_write_fd, True)
    input_file = open(os.devnull, "rb")
    output_file = open(os.devnull, "wb") if not on_stdout else None
    os.set_inheritable(input_file.fileno(), True)
    if output_file:
        os.set_inheritable(output_file.fileno(), True)
    started = time.monotonic()
    cancelled = False
    try:
        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        _check(
            _kernel32.SetInformationJobObject(
                job,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            ),
            "SetInformationJobObject",
        )
        startup = StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        startup.dwFlags = STARTF_USESTDHANDLES
        startup.hStdInput = msvcrt.get_osfhandle(input_file.fileno())
        stdout_fd = stdout_write_fd if output_file is None else output_file.fileno()
        startup.hStdOutput = msvcrt.get_osfhandle(stdout_fd)
        startup.hStdError = msvcrt.get_osfhandle(write_fd)
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        _check(
            _kernel32.CreateProcessW(
                args[0],
                command_line,
                None,
                None,
                True,
                CREATE_NO_WINDOW | CREATE_SUSPENDED,
                None,
                str(cwd) if cwd else None,
                ctypes.byref(startup),
                ctypes.byref(process),
            ),
            "CreateProcessW",
        )
        try:
            _check(
                _kernel32.AssignProcessToJobObject(job, process.hProcess),
                "AssignProcessToJobObject",
            )
            if _kernel32.ResumeThread(process.hThread) == 0xFFFFFFFF:
                _check(0, "ResumeThread")
        except BaseException:
            _kernel32.TerminateJobObject(job, 1)
            raise
        os.close(write_fd)
        write_fd = -1
        stderr_reader = threading.Thread(target=_read_lines, args=(read_fd, on_stderr), daemon=True)
        stderr_reader.start()
        readers.append(stderr_reader)
        read_fd = -1
        if on_stdout:
            os.close(stdout_write_fd)
            stdout_write_fd = -1
            stdout_reader = threading.Thread(
                target=_read_lines, args=(stdout_read_fd, on_stdout), daemon=True
            )
            stdout_reader.start()
            readers.append(stdout_reader)
            stdout_read_fd = -1
        while True:
            result = _kernel32.WaitForSingleObject(process.hProcess, 100)
            if result == WAIT_OBJECT_0:
                break
            if result != WAIT_TIMEOUT:
                _check(0, "WaitForSingleObject")
            if on_poll:
                on_poll()
            if (
                cancel
                and cancel.is_set()
                or timeout_sec
                and time.monotonic() - started > timeout_sec
            ):
                cancelled = True
                _check(_kernel32.TerminateJobObject(job, 1), "TerminateJobObject")
                _kernel32.WaitForSingleObject(process.hProcess, 5000)
                break
        for reader in readers:
            reader.join(timeout=5)
        if on_poll:
            on_poll()
        exit_code = wintypes.DWORD()
        _check(
            _kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(exit_code)),
            "GetExitCodeProcess",
        )
        return ProcessResult(exit_code.value, time.monotonic() - started, cancelled)
    finally:
        if write_fd >= 0:
            os.close(write_fd)
        if read_fd >= 0:
            os.close(read_fd)
        if stdout_write_fd >= 0:
            os.close(stdout_write_fd)
        if stdout_read_fd >= 0:
            os.close(stdout_read_fd)
        input_file.close()
        if output_file:
            output_file.close()
        if process.hThread:
            _kernel32.CloseHandle(process.hThread)
        if process.hProcess:
            _kernel32.CloseHandle(process.hProcess)
        _kernel32.CloseHandle(job)
