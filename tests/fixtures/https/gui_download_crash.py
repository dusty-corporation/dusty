"""Real guarded GUI used only to test hard parent death during local TLS download."""


def main():
    import atexit
    import json
    import os
    import sys
    from pathlib import Path

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QDialog

    from dusty.app.model_manager import DownloadDialog
    from dusty.app.window import MainWindow
    from dusty.runtime_paths import RuntimePaths

    port, certificate, resources, models, user, output = sys.argv[1:]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "gui-pid").write_text(str(os.getpid()), encoding="ascii")
    os.environ["DUSTY_TEST_FETCH_CHECKPOINT"] = str(output / "fetch-ready.json")
    atexit.register(lambda: (output / "gui-cleanup-ran").touch())
    app = QApplication([])
    paths = RuntimePaths(Path(resources) / "bin", Path(models), Path(resources), Path(user))
    window = MainWindow(paths, interactive=False)
    command = [sys.executable, str(Path(__file__).with_name("fetch_child.py")), port, certificate]
    import dusty.app.model_manager as manager_module

    manager_module.resolve_fetch_command = lambda: command
    DownloadDialog.exec = lambda _: QDialog.DialogCode.Accepted
    opened = False
    started = False

    def drive():
        nonlocal opened, started
        if window.ready and not opened:
            opened = True
            window.vad.setChecked(False)
            QTimer.singleShot(0, lambda: window.open_model_manager(focus_id="tiny"))
        dialog = window.model_manager
        if dialog is None:
            return
        if not started and dialog.workers and not dialog.busy:
            started = True
            dialog.download_button.click()
        elif started and dialog.worker and dialog.worker.pids:
            checkpoint = output / "fetch-ready.json"
            if checkpoint.exists():
                # The actual child PID must also have arrived via the GUI protocol.
                child = json.loads(checkpoint.read_text(encoding="utf-8"))["pid"]
                if child in dialog.worker.pids:
                    (output / "gui-ready").touch()

    timer = QTimer()
    timer.timeout.connect(drive)
    timer.start(10)
    window.show()
    window.initialize()
    return app.exec()


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    raise SystemExit(main())
