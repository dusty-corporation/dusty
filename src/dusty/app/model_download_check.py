"""CI-only real-entry exercise of the actual Model Manager and child boundary."""

import json
import os
import time
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from dusty.privacy.network_guard import is_installed
from dusty.runtime_paths import resolve_paths

from . import messages as M
from .model_manager import VOICE_ID, DownloadDialog
from .theme import apply_theme
from .window import MainWindow
from .workers import Prepared


def run_download_check(model_id: str, output: Path) -> int:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not is_installed():
        return 2
    paths = resolve_paths()
    paths = replace(paths, models_dir=paths.user_dir / "models")
    app = QApplication([])
    apply_theme(app)
    window = MainWindow(paths, interactive=False)
    window.apply_prepared(Prepared((), False, {"output_dir": str(output)}, vad_installed=False))
    window.show()
    began = time.monotonic()
    started = False
    consent = False
    timed_out = False
    outcome = 1

    def poll() -> None:
        nonlocal started, consent, timed_out, outcome
        dialog = window.model_manager
        if dialog is None:
            return
        modal = QApplication.activeModalWidget()
        if isinstance(modal, DownloadDialog):
            consent = True
            modal.accept()  # Explicit simulated user consent, same real dialog path.
            return
        if time.monotonic() - began > 180:
            timed_out = True
            dialog.done(0)
        if (
            not started
            and not timed_out
            and not dialog.busy
            and dialog.message.text() == M.MODELS_READY
        ):
            started = True
            QTimer.singleShot(0, dialog.download_button.click)
        elif (started or timed_out) and not dialog.busy:
            pids = sorted({pid for worker in dialog.workers for pid in worker.pids})
            ok = bool(
                not timed_out
                and consent
                and pids
                and os.getpid() not in pids
                and dialog.statuses[model_id] == "installed"
                and dialog.statuses[VOICE_ID] == "installed"
                and model_id in window.installed
                and window.vad_installed
            )
            output.mkdir(parents=True, exist_ok=True)
            (output / "download-result.json").write_text(
                json.dumps(
                    {
                        "gui_pid": os.getpid(),
                        "fetch_pids": pids,
                        "verified": ok,
                        "consent_confirmed": consent,
                        "guard_installed": is_installed(),
                    }
                ),
                encoding="utf-8",
                newline="\n",
            )
            outcome = 0 if ok else 1
            timer.stop()
            dialog.accept()
            window.ready = False
            window.close()
            app.quit()

    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(poll)
    timer.start()
    QTimer.singleShot(0, lambda: window.open_model_manager(focus_id=model_id))
    app.exec()
    return outcome
