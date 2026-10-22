"""Kill a real coordinator parent, verify child death, then resume its batch."""

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pytest

from dusty.core import JobStatus
from dusty.models import ModelRegistry, load_manifest
from dusty.queue import Coordinator, cleanup_orphaned_work, load_batch
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]

PARENT = """
from dusty.privacy.network_guard import install_guard
install_guard()
import os
import sys
from pathlib import Path
from dusty.core import BatchOptions, Job, JobStatus
from dusty.models import ModelRegistry, load_manifest
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths, resolve_paths
root, temporary = map(Path, sys.argv[1:])
(temporary / 'parent-pid').write_text(str(os.getpid()), encoding='ascii')
dev = resolve_paths(repo_root=root, frozen=False)
paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, temporary / 'user')
registry = ModelRegistry(load_manifest(paths.resources_dir / 'models.json'), paths.models_dir)
jobs = [Job(root / 'tests/fixtures/audio/formats/jfk.wav'),
        Job(root / 'tests/fixtures/audio/vad/mostly-silence-10min.m4a')]
options = BatchOptions('tiny', temporary / 'out', formats=('txt',),
                       backend='cpu', threads=4, vad=False)
def changed(job):
    if job is jobs[1] and job.status == JobStatus.TRANSCRIBING:
        (temporary / 'ready').touch()
Coordinator(paths, registry).run_batch(jobs, options, on_change=changed, vulkan_ok=False)
"""


class ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _native_child_handle(parent_pid: int):
    """Open a synchronization handle while the native child is still alive."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ("Process32FirstW", "Process32NextW"):
        function = getattr(kernel, name)
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
        function.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    assert snapshot != ctypes.c_void_p(-1).value
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32ParentProcessID == parent_pid and entry.szExeFile == "whisper-cli.exe":
                handle = kernel.OpenProcess(0x00100000, False, entry.th32ProcessID)
                assert handle
                return kernel, handle
            found = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return None


def _kill_worker(tmp_path: Path) -> None:
    # A Windows venv Python redirector can have a different PID from its real
    # interpreter. Kill the actual coordinator, not just that launcher.
    pid_file = tmp_path / "parent-pid"
    if not pid_file.exists():
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(1, False, int(pid_file.read_text(encoding="ascii")))
    if handle:
        try:
            assert kernel.TerminateProcess(handle, 1)
        finally:
            kernel.CloseHandle(handle)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Objects")
def test_parent_crash_kills_native_child_and_batch_resumes(tmp_path: Path) -> None:
    parent = subprocess.Popen(
        [sys.executable, "-c", PARENT, str(ROOT), str(tmp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child = None
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            assert parent.poll() is None, "Coordinator exited before the crash test"
            if (tmp_path / "ready").exists():
                actual_pid = int((tmp_path / "parent-pid").read_text(encoding="ascii"))
                child = _native_child_handle(actual_pid)
                if child:
                    break
            time.sleep(0.02)
        assert child is not None, "Must kill the parent with a live native transcription child"
        kernel, handle = child
        assert kernel.WaitForSingleObject(handle, 0) == 258
        _kill_worker(tmp_path)
        parent.wait(timeout=10)
        assert kernel.WaitForSingleObject(handle, 5000) == 0, "Native child survived parent death"
    finally:
        if parent.poll() is None:
            _kill_worker(tmp_path)
            parent.kill()
            parent.wait(timeout=10)
        if child:
            child[0].CloseHandle(child[1])

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    recovered = load_batch(paths.user_dir / "state/queue.json")
    assert recovered is not None
    options, jobs = recovered
    assert [job.status for job in jobs] == [JobStatus.DONE, JobStatus.QUEUED]
    completed = jobs[0].outputs[0]
    before = (completed.read_bytes(), completed.stat().st_mtime_ns)
    assert (paths.user_dir / "work" / str(jobs[1].id)).is_dir()
    cleanup_orphaned_work(paths.user_dir / "work")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=False)
    assert all(job.status == JobStatus.DONE for job in jobs)
    assert (completed.read_bytes(), completed.stat().st_mtime_ns) == before
    assert all(output.is_file() for job in jobs for output in job.outputs)
    assert list((paths.user_dir / "work").iterdir()) == []
