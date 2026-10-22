"""Exercise simple-mode controls, safe dialogs, queue editing and recovery."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLabel, QPushButton

from dusty.app import messages as M
from dusty.app.dialogs import (
    CollisionDialog,
    ErrorDialog,
    FolderDialog,
    ResumeDialog,
    SummaryDialog,
    SyncDialog,
)
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
    assert remaining.name + " is already in the list" in window.status.text()


def test_backend_defaults_language_translation_and_hint_rules(window, qtbot, tmp_path) -> None:
    window.apply_prepared(
        Prepared(tuple(window.registry.manifest.models), True, {"schema_version": 1})
    )
    assert window.model_choice.currentData() == "large-v3-turbo-q8_0"
    assert "Recommended" in window.model_choice.currentText()
    window.model.set_jobs([Job(tmp_path / "clip.wav")])
    window._refresh()
    assert window.start_button.isEnabled()
    window.options_dialog.show()
    assert window.options_scroll.isVisible()
    assert not window.task_choice.model().item(1).isEnabled()
    assert not window.use_medium.isVisible()
    assert not window.incompatible.isVisible()
    window._set_combo(window.task_choice, "translate")
    assert window.incompatible.isVisible()
    assert window.use_medium.isVisible()
    assert not window.start_button.isEnabled()
    window._use_medium()
    assert window.model_choice.currentData() == "medium"
    assert window.task_choice.currentData() == "translate"
    assert window.start_button.isEnabled()
    window._set_combo(window.model_choice, "small.en")
    assert window.language_choice.currentData() == "en"
    assert not window.language_choice.isEnabled()
    assert not window.start_button.isEnabled()
    window._use_medium()
    assert window.language_choice.currentData() == "auto"
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
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/three.wav").touch()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: str(tmp_path))

    def include_subfolders(dialog):
        dialog.recursive.setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FolderDialog, "exec", include_subfolders)
    qtbot.mouseClick(window.add_folder_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.model.rowCount() == 3 and not window.scanner.isRunning())


def test_dialog_defaults_and_every_error(window, qtbot) -> None:
    collision = CollisionDialog("example.wav", window)
    qtbot.addWidget(collision)
    assert collision.selected_policy() == "keep_both"
    assert collision.apply_all.isChecked()
    summary = SummaryDialog(
        [Job(Path("example.wav"), status=JobStatus.FAILED, failure=FailureCode.NO_AUDIO)], window
    )
    qtbot.addWidget(summary)
    assert summary.retry.isEnabled()
    sync = SyncDialog(window)
    qtbot.addWidget(sync)
    for code in FailureCode:
        dialog = ErrorDialog(code, filename="example.wav", parent=window)
        assert any("example.wav" in label.text() for label in dialog.findChildren(QLabel))
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == M.ERROR_TITLE
        assert M.FAILURE_MESSAGES[code].action


def test_resume_and_settings_preserve_preferences(window, qtbot, tmp_path, monkeypatch) -> None:
    options = BatchOptions(
        "medium",
        tmp_path / "out",
        task="translate",
        prompt="CANARYMEDTERM",
        formats=("txt", "json"),
    )
    job = Job(tmp_path / "clip.wav", status=JobStatus.TRANSCRIBING, elapsed_sec=120)
    state = window.paths.user_dir / "state/queue.json"
    save_batch(state, options, [job])
    recovered = load_batch(state)
    monkeypatch.setattr(ResumeDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    resumed = []
    monkeypatch.setattr(window, "start_batch", lambda: resumed.append(True))
    window._startup_dialogs(Prepared(window.installed, False, window.settings, recovered))
    qtbot.waitUntil(lambda: bool(resumed))
    assert window.model.jobs[0].status == JobStatus.QUEUED
    assert window.model.jobs[0].elapsed_sec == 0
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


def test_resume_never_silently_substitutes_an_uninstalled_model(window, qtbot, tmp_path) -> None:
    window.apply_prepared(Prepared(("tiny",), False, {"schema_version": 1}))
    window.restore_batch(BatchOptions("medium", tmp_path / "out"), [Job(tmp_path / "clip.wav")])
    assert not window.start_button.isEnabled()
    assert window.resume_model_button.isVisible()
    assert "Medium" in window.warning.text()
    qtbot.mouseClick(window.resume_model_button, Qt.MouseButton.LeftButton)
    assert window.start_button.isEnabled()
    assert window.model_choice.currentData() == "tiny"


def test_options_are_modal_without_reflow_and_extra_formats_persist(window, qtbot) -> None:
    window.model.set_jobs([Job(Path("one.wav"))])
    window._refresh()
    qtbot.wait(20)
    geometry = window.table.geometry()
    assert set(
        box.text() for box in window.format_row.findChildren(type(window.formats["txt"]))
    ) == {M.FORMATS["txt"], M.FORMATS["docx"]}
    assert not window.overall.isVisible()
    seen = []

    def review():
        seen.append(window.options_dialog.isModal() and window.options_dialog.isVisible())
        assert window.table.geometry() == geometry
        window.formats["json"].setChecked(True)
        window.options_dialog.accept()

    QTimer.singleShot(500, window.options_dialog.accept)
    QTimer.singleShot(50, review)
    qtbot.mouseClick(window.options_button, Qt.MouseButton.LeftButton)
    assert seen == [True]
    assert window.table.geometry() == geometry
    saved = json.loads((window.paths.user_dir / "settings.json").read_text(encoding="utf-8"))
    assert "json" in saved["formats"]
    assert not any(
        button.text() in {M.MOVE_UP, M.MOVE_DOWN} for button in window.findChildren(QPushButton)
    )
    window.model.set_jobs([Job(Path("one.wav")), Job(Path("two.wav"))])
    window.table.selectRow(0)
    window.move_actions[1].trigger()
    assert window.model.jobs[1].source.name == "one.wav"
    assert window.move_actions[0].shortcut().toString() == "Alt+Up"
    window.activateWindow()
    window.table.setFocus()
    qtbot.waitUntil(window.table.hasFocus)
    qtbot.keyClick(window.table, Qt.Key.Key_Up, Qt.KeyboardModifier.AltModifier)
    assert window.model.jobs[0].source.name == "one.wav"


def test_phase_text_matches_active_row_including_zero_progress(window) -> None:
    from dataclasses import replace

    job = Job(Path("one.wav"))
    window.model.set_jobs([job])
    window.running = True
    window._refresh()
    assert window.overall.isVisible()
    for phase in (
        JobStatus.PREFLIGHT,
        JobStatus.DECODING,
        JobStatus.TRANSCRIBING,
        JobStatus.EXPORTING,
    ):
        window._job_changed(replace(job, status=phase, progress=0))
        assert M.phase_text(phase.value, 0) in window.status.text()
        assert window.model.data(window.model.index(0, 2)) == M.phase_text(phase.value, 0)
    window.running = False
    window._refresh()
    assert not window.overall.isVisible()


def test_named_dialogs_radio_choices_and_nonzero_summary(window, qtbot) -> None:
    collision = CollisionDialog("example.wav", window)
    qtbot.addWidget(collision)
    assert any("example.wav" in label.text() for label in collision.findChildren(QLabel))
    assert list(collision.choices) == ["keep_both", "overwrite", "skip"]
    collision.choices["overwrite"].click()
    assert collision.selected_policy() == "overwrite"
    assert not collision.choices["keep_both"].isChecked()
    summary = SummaryDialog(
        [Job(Path("bad.wav"), status=JobStatus.FAILED, failure=FailureCode.NO_AUDIO)], window
    )
    qtbot.addWidget(summary)
    text = "\n".join(label.text() for label in summary.findChildren(QLabel))
    assert "0 done" not in text and "0 skipped" not in text
    assert "bad.wav" in text and M.FAILURE_MESSAGES[FailureCode.NO_AUDIO].message in text
    assert not summary.open_folder.isVisible()
    assert summary.dismiss.isDefault()
    assert summary.dismiss.objectName() == "primaryButton"
    dialog = ErrorDialog(FailureCode.NO_AUDIO, filename="bad.wav", parent=window)
    qtbot.addWidget(dialog)
    assert any("bad.wav" in label.text() for label in dialog.findChildren(QLabel))


def test_empty_output_language_rules_and_clear_finished(window, qtbot, tmp_path) -> None:
    window.output_dir = None
    window._refresh()
    assert window.output_row.isVisible()
    assert window.output_label.text() == M.NO_OUTPUT
    assert window.warning.text() == M.CHOOSE_OUTPUT_FIRST
    assert not window.start_button.isEnabled()
    assert any(action.text() == M.CHOOSE_OUTPUT_MENU for action in window.edit_actions)
    window.options_dialog.show()
    window._set_combo(window.language_choice, "fa")
    window._set_combo(window.model_choice, "small.en")
    assert window.language_choice.currentData() == "en"
    assert window.incompatible.isVisible()
    assert "unavailable" in window.task_choice.itemText(1)
    assert not window.task_choice.model().item(1).isEnabled()
    window._set_combo(window.model_choice, "medium")
    assert window.language_choice.currentData() == "fa"
    assert window.model_warning.isVisible()
    assert window.model_warning.text() == M.SLOW
    assert window.model_speed.text().startswith(M.SPEED_SLOW)
    window.options_dialog.hide()
    window.output_dir = tmp_path / "out"
    window.model.set_jobs([Job(tmp_path / "one.wav", status=JobStatus.DONE)])
    window._refresh()
    assert window.warning.text() == M.EVERYTHING_DONE
    window.clear_finished()
    assert window.model.rowCount() == 0 and window.output_row.isVisible()


def test_duplicate_copy_highlight_and_tab_exits_recording_list(window, qtbot, tmp_path) -> None:
    from dusty.queue.scanning import ScanResult

    job = Job(tmp_path / "one.wav")
    window.model.set_jobs([job])
    window._scanned(ScanResult((), 0, 1, (job.source,)))
    assert window.status.text() == "one.wav is already in the list"
    assert job.source in window.model.highlighted
    assert M.scan_summary(1, 0, 0) == M.ADDED_ONE
    assert M.scan_summary(2, 0, 3) == "2 recordings added; 3 recordings were already in the list"
    window.activateWindow()
    window.table.setFocus()
    qtbot.waitUntil(window.table.hasFocus)
    qtbot.keyClick(window.table, Qt.Key.Key_Tab)
    assert not window.table.hasFocus()
    window._clear_highlight()
    assert not window.model.highlighted


def test_collision_wait_phase_and_existing_transcript_name(
    window, monkeypatch, qtbot, tmp_path
) -> None:
    class Worker:
        def choose_collision(self, policy, apply_all):
            assert policy == "keep_both"

    window.batch = Worker()
    window.running = True
    job = Job(tmp_path / "one.amr", outputs=[tmp_path / "one.txt"])
    window.model.set_jobs([job])

    def choose(dialog):
        window._tick()
        assert window.status.text() == M.WAITING_CHOICE
        assert window.model.data(window.model.index(0, 2)) == M.WAITING_CHOICE
        assert any("one.txt" in label.text() for label in dialog.findChildren(QLabel))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(CollisionDialog, "exec", choose)
    window._collision(job)
    assert not window._waiting_choice
    window.running = False
    window.batch = None


def test_zero_success_summary_and_folder_title_are_unambiguous(window, qtbot) -> None:
    summary = SummaryDialog(
        [Job(Path("bad.mp3"), status=JobStatus.FAILED, failure=FailureCode.DECODE_ERROR)], window
    )
    qtbot.addWidget(summary)
    summary.show()
    assert not summary.open_folder.isVisible()
    assert summary.dismiss.isDefault()
    assert summary.dismiss.objectName() == "primaryButton"
    folder = FolderDialog(window)
    qtbot.addWidget(folder)
    assert not any(label.text() == M.FOLDER_TITLE for label in folder.findChildren(QLabel))
