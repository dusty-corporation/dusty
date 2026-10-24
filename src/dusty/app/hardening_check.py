"""CI-only packaged GUI canary using the real batch worker and native engine."""

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from dusty.core import Job, JobStatus
from dusty.privacy.logging import configure_logger
from dusty.privacy.network_guard import is_installed
from dusty.runtime_paths import resolve_paths

from .window import MainWindow
from .workers import Prepared


def run(output: Path) -> int:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not is_installed():
        return 2
    paths = resolve_paths()
    logger = configure_logger(paths.user_dir)
    output.mkdir(parents=True, exist_ok=False)
    source = output / "CANARY_PATIENT_JANE_DOE تست ضبط.wav"
    shutil.copyfile(paths.resources_dir / "selftest.wav", source)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    app = QApplication([])
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
        job = window.model.jobs[0]
        ok = bool(
            job.status == JobStatus.DONE
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
