"""CI-only packaged GUI canary using the real batch worker and native engine."""

import ctypes
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from dusty.core import Job, JobStatus
from dusty.privacy import native_diagnostics as diagnostics
from dusty.privacy.logging import configure_logger
from dusty.privacy.network_guard import is_installed
from dusty.runtime_paths import resolve_paths

from .window import MainWindow
from .workers import Prepared


def run(output: Path) -> int:
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or not is_installed()
        or not diagnostics.is_installed()
    ):
        return 2
    paths = resolve_paths()
    logger = configure_logger(paths.user_dir)
    output.mkdir(parents=True, exist_ok=False)
    source = output / "CANARY_PATIENT_JANE_DOE تست ضبط.wav"
    shutil.copyfile(paths.resources_dir / "selftest.wav", source)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    app = QApplication([])
    # Explicit CI fixture, never a claim that the real Qt defect reproduced.
    diagnostics.set_context("ci-fixture")
    kernel = ctypes.WinDLL("kernel32")
    kernel.RaiseException.argtypes = [
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    secret = ctypes.create_unicode_buffer("CANARY_PATIENT_JANE_DOE CANARYMEDTERM")
    info = (ctypes.c_size_t * 1)(ctypes.addressof(secret))
    try:
        kernel.RaiseException(0x8001010D, 0, 1, info)
    except OSError:
        pass  # Normal ctypes handling still happens after passive observation.
    else:
        return 1
    diagnostics.set_context("gui-check")
    window = MainWindow(paths, interactive=False)
    window.apply_prepared(
        Prepared(
            ("tiny",),
            False,
            {
                "schema_version": 1,
                "model_id": "tiny",
                "output_dir": str(output / "transcripts"),
                "backend": "cpu",
                "threads": 2,
                "vad": False,
                "prompt": "CANARYMEDTERM",
            },
            vad_installed=False,
        )
    )
    window.model.set_jobs([Job(source)])
    window._refresh()
    window.show()
    started = time.monotonic()
    outcome = 1
    timer = QTimer()

    def poll() -> None:
        nonlocal outcome
        if time.monotonic() - started > 120:
            window.cancel_all()
        if not window.batch or window.running or window.batch.isRunning():
            return
        timer.stop()
        for handler in logger.handlers:
            handler.flush()
        logs = "".join(
            p.read_text(encoding="utf-8") for p in (paths.user_dir / "logs").glob("dusty.log*")
        )
        capture = paths.user_dir / "logs/native-diagnostic.jsonl"
        captured = capture.read_text(encoding="ascii")
        logs += captured

        captured_events = [json.loads(line) for line in captured.splitlines()]
        capture_ok = any(
            event["phase"] == "ci-fixture"
            and event["instruction"]["module"] != "unknown"
            and event["frames"]
            for event in captured_events
        )
        job = window.model.jobs[0]
        ok = bool(
            capture_ok
            and job.status == JobStatus.DONE
            and len(job.outputs) == 2
            and all(p.is_file() for p in job.outputs)
            and "CANARY" not in logs
            and str(source) not in logs
            and "تست ضبط" not in logs
            and hashlib.sha256(source.read_bytes()).hexdigest() == original
            and not list((paths.user_dir / "work").iterdir())
        )
        (output / "summary.json").write_text(
            json.dumps(
                {
                    "packaged_canary": ok,
                    "outputs_complete": job.status == JobStatus.DONE,
                    "source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == original,
                    "guard_installed": is_installed(),
                    "native_diagnostic_capture": bool(capture_ok),
                }
            ),
            encoding="utf-8",
        )
        outcome = 0 if ok else 1
        window.ready = False
        window.close()
        app.quit()

    timer.timeout.connect(poll)
    timer.start(25)
    QTimer.singleShot(0, window.start_batch)
    app.exec()
    return outcome
