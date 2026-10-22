"""Drive the real Qt window through an offline batch for the WFP CI audit."""

from dusty.privacy.network_guard import install_guard

install_guard()


def main() -> int:
    import sys
    from pathlib import Path

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from dusty.app.theme import apply_theme
    from dusty.app.window import MainWindow
    from dusty.core import Job, JobStatus

    app = QApplication([])
    apply_theme(app)
    window = MainWindow(interactive=False)
    window.output_dir = Path(sys.argv[1])
    root = Path(__file__).resolve().parents[2]
    window.model.set_jobs([Job(root / "tests/fixtures/audio/formats/jfk.wav")])
    window.show()
    result = 1
    started = False
    poll = QTimer()
    poll.setInterval(20)

    def finished() -> None:
        nonlocal result
        job = window.model.jobs[0]
        if job.status == JobStatus.DONE and len(job.outputs) == 2:
            result = 0
        window.close()
        app.quit()

    def ready() -> None:
        nonlocal started
        if not started and window.ready:
            started = True
            poll.stop()
            window._set_combo(window.model_choice, "tiny")
            window._set_combo(window.device_choice, "cpu")
            window._refresh()
            window.start_batch()
            if window.batch:
                window.batch.finished.connect(finished)
            else:
                app.quit()

    poll.timeout.connect(ready)
    poll.start()
    window.initialize()
    app.exec()
    if result == 0:
        print("gui batch passed")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
