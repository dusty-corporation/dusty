"""Windows Job Object child process and cancellation checks."""

import sys
import threading
from pathlib import Path

import pytest

from dusty.platform.win_process import run_job_process


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
