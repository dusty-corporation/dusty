"""Windows Job Object child process and cancellation checks."""

import sys
import threading
from pathlib import Path

import pytest

from dusty.platform.win_process import run_job_process


def test_child_uses_executable_folder_even_with_untrusted_parent_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    lines = []
    result = run_job_process(
        [str(Path(sys.executable).resolve()), "-c", "import os; print(os.getcwd())"],
        on_stdout=lines.append,
        timeout_sec=5,
    )
    assert result.exit_code == 0
    assert Path(lines[0]) == Path(sys.executable).resolve().parent


def test_arbitrary_executable_is_rejected_before_launch(tmp_path):
    import shutil

    copy = tmp_path / "other-python.exe"
    shutil.copyfile(sys.executable, copy)
    with pytest.raises(ValueError, match="approved"):
        run_job_process([str(copy), "--version"])


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Objects")
def test_job_object_cancels_child() -> None:
    cancel = threading.Event()
    timer = threading.Timer(0.25, cancel.set)
    timer.start()
    try:
        result = run_job_process(
            [str(Path(sys.executable).resolve()), "-c", "import time; time.sleep(20)"],
            cancel=cancel,
            timeout_sec=5,
        )
    finally:
        timer.cancel()
    assert result.cancelled
    assert result.elapsed_sec < 3


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Objects")
def test_short_stderr_progress_is_delivered_before_child_exits() -> None:
    cancel = threading.Event()
    lines = []

    def poll() -> None:
        if lines:
            cancel.set()

    result = run_job_process(
        [
            str(Path(sys.executable).resolve()),
            "-c",
            "import sys,time; print('progress=25',file=sys.stderr,flush=True); time.sleep(5)",
        ],
        on_stderr=lines.append,
        on_poll=poll,
        cancel=cancel,
        timeout_sec=10,
    )
    assert lines == ["progress=25"]
    assert result.cancelled
    assert result.elapsed_sec < 3
