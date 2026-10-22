"""Exercise simple-mode controls, safe dialogs, queue editing and recovery."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog

from dusty.app import messages as M
from dusty.app.dialogs import CollisionDialog, ErrorDialog, ResumeDialog, SummaryDialog, SyncDialog
from dusty.app.window import MainWindow
from dusty.app.workers import Prepared, PrepareWorker
from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine.ffmpeg import AudioProbe
from dusty.models import ModelMissing
from dusty.queue.storage import load_batch, save_batch
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def window(qtbot, tmp_path: Path):
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    view = MainWindow(paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            tuple(view.registry.manifest.models), False, {"schema_version": 1, "welcome_seen": True}
        )
    )
    view.output_dir = tmp_path / "out"
    view.show()
    view._refresh()
    return view


def test_simple_mode_defaults_and_central_copy(window) -> None:
    assert window.drop_area.isVisible()
    assert not window.table.isVisible()
    assert not window.options_scroll.isVisible()
    assert window.formats["txt"].isChecked() and window.formats["docx"].isChecked()
    assert not window.formats["json"].isChecked()
    assert not window.start_button.isEnabled()
    assert M.PRIVACY == (
        "Dusty processes your recordings entirely on this computer. After installation, "
        "it never needs an internet connection, and it never sends your audio or "
        "transcripts anywhere."
    )
    assert len(M.LANGUAGES) == 100
    assert window.model_choice.currentData() == "small"


def test_folder_scan_duplicate_reorder_remove(window, qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("dusty.engine.probe_audio", lambda *a, **kw: AudioProbe(60, True))
    folder = tmp_path / "input"
    (folder / "nested").mkdir(parents=True)
    (folder / "one.wav").write_bytes(b"fixture")
    (folder / "notes.txt").write_text("unsupported", encoding="utf-8")
    (folder / "nested/two.mp3").write_bytes(b"fixture")
    window.add_paths([folder], recursive=True)
    qtbot.waitUntil(lambda: window.model.rowCount() == 2 and window.start_button.isEnabled())
    assert not window.drop_area.isVisible()
    assert window.table.isVisible()
    assert "1 unsupported" in window.status.text()
    first = window.model.jobs[0].id
    window.table.selectRow(0)
    window.move_selected(1)
    assert window.model.jobs[1].id == first
    window.remove_selected()
    assert window.model.rowCount() == 1
    remaining = window.model.jobs[0].source
    window.add_paths([remaining])
    qtbot.waitUntil(lambda: not window.scanner.isRunning())
    assert window.model.rowCount() == 1
    assert "1 duplicates" in window.status.text()


def test_backend_defaults_language_translation_and_hint_rules(window, qtbot, tmp_path) -> None:
    window.apply_prepared(
        Prepared(tuple(window.registry.manifest.models), True, {"schema_version": 1})
    )
    assert window.model_choice.currentData() == "large-v3-turbo-q8_0"
    assert "Recommended" in window.model_choice.currentText()
    window.model.set_jobs([Job(tmp_path / "clip.wav")])
    window._refresh()
    assert window.start_button.isEnabled()
    qtbot.mouseClick(window.options_toggle, Qt.MouseButton.LeftButton)
    assert window.options_scroll.isVisible()
    assert not window.task_choice.model().item(1).isEnabled()
    assert window.use_medium.isVisible()
    window._set_combo(window.task_choice, "translate")
    assert not window.start_button.isEnabled()
    window._use_medium()
    assert window.model_choice.currentData() == "medium"
    assert window.task_choice.currentData() == "translate"
    assert window.start_button.isEnabled()
    window._set_combo(window.model_choice, "small.en")
    assert window.language_choice.currentData() == "en"
    assert not window.language_choice.isEnabled()
    assert not window.start_button.isEnabled()
    window.prompt.setPlainText("CANARYMEDTERM " * 80)
    assert window.prompt_warning.isVisible()
    window._set_combo(window.model_choice, "medium")
    window._set_combo(window.device_choice, "cpu")
    assert window.warning.text() == M.SLOW


def test_add_files_button_and_local_drop(window, qtbot, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("dusty.engine.probe_audio", lambda *a, **kw: AudioProbe(1, True))
    first = tmp_path / "one.wav"
    second = tmp_path / "two.wav"
    first.touch()
    second.touch()
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *a: ([str(first)], ""))
    qtbot.mouseClick(window.add_files_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.model.rowCount() == 1 and not window.scanner.isRunning())
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(second))])
    enter = QDragEnterEvent(
        QPoint(30, 30),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window, enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(30, 30),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window, drop)
    qtbot.waitUntil(lambda: window.model.rowCount() == 2 and not window.scanner.isRunning())


def test_dialog_defaults_and_every_error(window, qtbot) -> None:
    collision = CollisionDialog(window)
    qtbot.addWidget(collision)
    assert collision.choice.currentData() == "keep_both"
    assert collision.apply_all.isChecked()
    summary = SummaryDialog(
        [Job(Path("example.wav"), status=JobStatus.FAILED, failure=FailureCode.NO_AUDIO)], window
    )
    qtbot.addWidget(summary)
    assert summary.retry.isEnabled()
    sync = SyncDialog(window)
    qtbot.addWidget(sync)
    for code in FailureCode:
        dialog = ErrorDialog(code, parent=window)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == M.ERROR_TITLE
        assert M.FAILURE_MESSAGES[code].action


def test_resume_and_settings_preserve_preferences(window, tmp_path, monkeypatch) -> None:
    options = BatchOptions(
        "medium",
        tmp_path / "out",
        task="translate",
        prompt="CANARYMEDTERM",
        formats=("txt", "json"),
    )
    job = Job(tmp_path / "clip.wav", status=JobStatus.TRANSCRIBING)
    state = window.paths.user_dir / "state/queue.json"
    save_batch(state, options, [job])
    recovered = load_batch(state)
    monkeypatch.setattr(ResumeDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window._startup_dialogs(Prepared(window.installed, False, window.settings, recovered))
    assert window.model.jobs[0].status == JobStatus.QUEUED
    assert window.task_choice.currentData() == "translate"
    assert window.prompt.toPlainText() == "CANARYMEDTERM"
    assert window.formats["json"].isChecked() and not window.formats["docx"].isChecked()
    assert window._save_settings()
    saved = json.loads((window.paths.user_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["prompt"] == "CANARYMEDTERM"
    assert saved["task"] == "translate"


def test_prepare_worker_emits_only_verified_installed_models(window, qtbot, monkeypatch) -> None:
    def verify(model_id):
        if model_id != "tiny":
            raise ModelMissing("Missing")
        return Path("verified")

    monkeypatch.setattr(window.registry, "model_path", verify)
    monkeypatch.setattr("dusty.engine.backend.probe_vulkan", lambda *a, **kw: True)
    worker = PrepareWorker(window.paths, window.registry)
    with qtbot.waitSignal(worker.ready, timeout=2000) as result:
        worker.start()
    worker.wait(2000)
    prepared = result.args[0]
    assert prepared.installed == ("tiny",)
    assert prepared.vulkan_ok


def test_device_reprobe_preserves_user_choice_and_relabels_default(
    window, qtbot, monkeypatch
) -> None:
    window.apply_prepared(
        Prepared(tuple(window.registry.manifest.models), True, {"schema_version": 1})
    )
    window.interactive = True

    def prepare(worker):
        worker.ready.emit(
            Prepared(
                tuple(worker.registry.manifest.models),
                True,
                {"schema_version": 1, "backend": "auto"},
            )
        )

    monkeypatch.setattr(PrepareWorker, "run", prepare)
    window._set_combo(window.device_choice, "cpu")
    qtbot.waitUntil(lambda: window.ready and not window.preparer.isRunning())
    assert window.device_choice.currentData() == "cpu"
    assert window.model_choice.currentData() == "small"
    assert "Recommended" in window.model_choice.currentText()
    window.interactive = False
