"""Render synthetic GUI review screens at real Qt device-pixel scaling."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(output: Path, theme: str) -> None:
    from dusty.privacy.network_guard import install_guard

    install_guard()
    from PySide6.QtGui import QFont, QRawFont
    from PySide6.QtWidgets import QApplication

    from dusty.app import messages as M
    from dusty.app.dialogs import (
        CloseDialog,
        CollisionDialog,
        ErrorDialog,
        FolderDialog,
        ResumeDialog,
        SummaryDialog,
        SyncDialog,
        TextDialog,
        WelcomeDialog,
    )
    from dusty.app.theme import apply_theme
    from dusty.app.window import MainWindow
    from dusty.app.workers import Prepared
    from dusty.core import FailureCode, Job, JobStatus
    from dusty.runtime_paths import RuntimePaths

    app = QApplication([])
    apply_theme(app, theme)
    if not QRawFont.fromFont(QFont("Segoe UI", 10)).supportsCharacter("A"):
        raise RuntimeError("Required screenshot font glyphs are unavailable")
    output.mkdir(parents=True, exist_ok=True)
    paths = RuntimePaths(
        ROOT / "build/bin", ROOT / "build/models", ROOT / "resources", output / "state"
    )
    window = MainWindow(paths, interactive=False)
    window.apply_prepared(
        Prepared(
            tuple(window.registry.manifest.models), True, {"schema_version": 1, "theme": theme}
        )
    )
    window.output_dir = None
    window.show()

    def capture(widget, name: str) -> None:
        widget.show()
        app.processEvents()
        if not widget.grab().save(str(output / (name + ".png"))):
            raise RuntimeError("Screenshot save failed")

    window._refresh()
    capture(window, "01-empty")
    window.output_dir = Path("C:/Transcripts")
    window._refresh()
    capture(window, "01b-output-chosen")
    jobs = [
        Job(Path("C:/Recordings/Lecture 01.wav"), duration_sec=1200),
        Job(Path("C:/Recordings/Lecture 02.mp3"), duration_sec=900),
    ]
    window.model.set_jobs(jobs)
    window._refresh()
    window.status.setText(M.scan_summary(2, 0, 0))
    capture(window, "02-queued")
    window.status.setText(M.DUPLICATE_ONE.format(name=jobs[0].source.name))
    capture(window, "02b-duplicate-message")
    window.output_dir = None
    window._refresh()
    capture(window, "02c-choose-output")
    window.output_dir = Path("C:/Transcripts")
    window.status.setText(M.READY)
    window._refresh()
    window.options_dialog.show()
    capture(window.options_dialog, "03-options")
    window._set_combo(window.task_choice, "translate")
    capture(window.options_dialog, "03b-translation-choice")
    window._set_combo(window.task_choice, "transcribe")
    window.options_scroll.verticalScrollBar().setValue(
        window.options_scroll.verticalScrollBar().maximum() // 2
    )
    capture(window.options_dialog, "04-vocabulary")
    window.advanced_toggle.setChecked(True)
    app.processEvents()
    window.options_scroll.verticalScrollBar().setValue(
        window.options_scroll.verticalScrollBar().maximum()
    )
    capture(window.options_dialog, "05-advanced")
    window.advanced_toggle.setChecked(False)
    window.options_scroll.verticalScrollBar().setValue(0)
    window._set_combo(window.model_choice, "small.en")
    capture(window.options_dialog, "05b-english-only")
    window._set_combo(window.model_choice, "medium")
    window.options_scroll.verticalScrollBar().setValue(0)
    window._set_combo(window.device_choice, "cpu")
    capture(window.options_dialog, "05c-slow-choice")
    window.options_dialog.hide()
    capture(window, "05d-main-slow-warning")
    window._set_combo(window.device_choice, "auto")
    window._set_combo(window.model_choice, "large-v3-turbo-q8_0")
    window.options_dialog.hide()
    window.model.jobs[0].status = JobStatus.TRANSCRIBING
    window.model.jobs[0].progress = 0.62
    window.model.jobs[0].elapsed_sec = 74
    window.running = True
    window._refresh()
    window._active_id = window.model.jobs[0].id
    window._batch_started = time.monotonic() - 74
    window._active_received = time.monotonic()
    window._active_elapsed = 74
    window._timed_ids = {job.id for job in window.model.jobs}
    window._tick()
    window.overall.setValue(310)
    capture(window, "06-running")
    window.model.jobs[0].progress = 0
    window._tick()
    capture(window, "06a-preparing")
    window.model.jobs[0].status = JobStatus.EXPORTING
    window.model.jobs[0].progress = 0.95
    window._tick()
    capture(window, "06b-saving")
    window.running = False
    window.model.jobs[0].status = JobStatus.DONE
    window.model.jobs[1].status = JobStatus.FAILED
    window.model.jobs[1].failure = FailureCode.NO_AUDIO
    window._refresh()
    window.status.setText(M.summary_counts({"done": 2}))
    window.model.jobs[1].status = JobStatus.DONE
    for job in window.model.jobs:
        job.progress = 1
    window._refresh()
    capture(window, "06c-all-finished")
    window.model.jobs[1].status = JobStatus.FAILED
    window._refresh()
    dialogs = [
        (CloseDialog(window), "13-close-save"),
        (TextDialog(M.PRIVACY_TITLE, (M.PRIVACY, M.ACCURACY), window), "14-privacy"),
        (
            TextDialog(
                M.ABOUT, (M.ABOUT_VERSION.format(version="0.0.1"), M.PRIVACY, M.ACCURACY), window
            ),
            "15-about",
        ),
        (CollisionDialog("Lecture 01.txt", window), "07-collision"),
        (SummaryDialog(window.model.jobs, window), "08-summary"),
        (SummaryDialog([window.model.jobs[1]], window), "08b-no-successes"),
        (FolderDialog(window), "12-add-folder"),
        (ResumeDialog(2, window), "09-resume"),
        (WelcomeDialog(window), "10-welcome"),
        (SyncDialog(window), "11-sync-warning"),
    ]
    dialogs.extend(
        (
            ErrorDialog(code, filename=window.model.jobs[1].source.name, parent=window),
            "error-" + code.value.lower(),
        )
        for code in FailureCode
    )
    for dialog, name in dialogs:
        dialog.adjustSize()
        capture(dialog, name)
        dialog.hide()
    window.ready = False
    window.close()
    app.processEvents()
    count = len(list(output.glob("*.png")))
    ratio = app.primaryScreen().devicePixelRatio()
    print(f"Rendered {count} screens; ratio={ratio:g}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/m3-screenshots")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Screenshot output must stay inside the repository")
    if args.child:
        render(output, args.theme)
        return
    for theme in ("light", "dark"):
        for scale in ("1", "1.5"):
            env = dict(
                os.environ,
                QT_QPA_PLATFORM="offscreen",
                QT_SCALE_FACTOR=scale,
                LOCALAPPDATA=str(output / "appdata"),
            )
            subprocess.run(
                [
                    sys.executable,
                    __file__,
                    "--child",
                    "--output",
                    str(output / f"{theme}-{scale}"),
                    "--theme",
                    theme,
                ],
                env=env,
                check=True,
                cwd=ROOT,
            )
    (output / "README.md").write_text(
        "# M3 UI review\n\nSynthetic recordings and progress only; no user content.\n"
        "All screens are rendered with pinned PySide6 6.9.2 via Qt's offscreen platform.\n"
        "Each light/dark folder uses QT_SCALE_FACTOR 1 or 1.5 (100% or 150%).\n"
        "The matrix includes every main screen and all failure-code dialogs.\n"
        "Client areas are captured; native window title bars are outside Qt widget grabs.\n"
        "Reproduce: uv run python tools/render_gui.py\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
