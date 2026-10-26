"""Exercise simple-mode controls, safe dialogs, queue editing and recovery."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLabel, QPushButton

from dusty.app import messages as M
from dusty.app.dialogs import (
    AboutDialog,
    CloseDialog,
    CollisionDialog,
    ErrorDialog,
    FolderDialog,
    NoticesDialog,
    ResumeDialog,
    SummaryDialog,
    SyncDialog,
    TextDialog,
    WelcomeDialog,
)
from dusty.app.window import MainWindow
from dusty.app.workers import Prepared, PrepareWorker
from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine.ffmpeg import AudioProbe
from dusty.models import ModelMissing
from dusty.queue.storage import load_batch, save_batch
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


def test_about_is_distinct_and_repository_is_selectable(qtbot):
    clicked = []
    dialog = AboutDialog("test-version", lambda: clicked.append(True))
    qtbot.addWidget(dialog)
    labels = dialog.findChildren(QLabel)
    texts = [label.text() for label in labels]
    assert M.ABOUT_VERSION.format(version="test-version") in texts
    assert M.ABOUT_DESCRIPTION in texts and M.ABOUT_LICENSE in texts
    assert M.PRIVACY not in texts and M.ACCURACY not in texts
    repository = next(label for label in labels if label.text() == M.REPOSITORY_ADDRESS)
    assert repository.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert repository.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByKeyboard
    assert not repository.openExternalLinks()
    qtbot.mouseClick(dialog.notices_button, Qt.MouseButton.LeftButton)
    assert clicked == [True]


def test_notices_open_the_bundled_local_text(window, tmp_path, qtbot, monkeypatch):
    from dataclasses import replace

    notices = tmp_path / "THIRD_PARTY_NOTICES.md"
    notices.write_text("Original local notices\nLicense text\n", encoding="utf-8")
    window.paths = replace(window.paths, resources_dir=tmp_path / "resources")
    seen = []

    def inspect(dialog):
        seen.append(dialog.text.toPlainText())
        assert dialog.text.isReadOnly()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(NoticesDialog, "exec", inspect)
    window.open_notices()
    assert seen == [notices.read_text(encoding="utf-8")]


@pytest.fixture
def window(qtbot, tmp_path: Path):
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    view = MainWindow(paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            tuple(view.registry.manifest.models),
            False,
            {"schema_version": 1, "welcome_seen": True},
            vad_installed=True,
        )
    )
    view.output_dir = tmp_path / "out"
    view.show()
    view._refresh()
    return view


def test_simple_mode_defaults_and_central_copy(window) -> None:
    assert not window.vad.isChecked()
    assert M.SILENCE_OFF not in window.choices_summary.text()
    assert window.drop_area.isVisible()
    assert not window.table.isVisible()
    assert not window.options_scroll.isVisible()
    assert window.formats["txt"].isChecked() and window.formats["docx"].isChecked()
    assert window.format_row.isVisible()
    assert not window.formats["json"].isChecked()
    assert not window.start_button.isEnabled()
    assert M.PRIVACY == (
        "Dusty processes your recordings entirely on this computer. After installation, "
        "it never needs an internet connection, and it never sends your audio or "
        "transcripts anywhere."
    )
    assert len(M.LANGUAGES) == 100
    assert window.model_choice.currentData() == "small"


def test_output_row_elides_long_path_and_recomputes_on_resize(window, qtbot):
    path = Path("C:/Transcripts") / ("Long folder name " * 7) / "saved transcripts"
    window.output_dir = path
    window.resize(800, 680)
    window._refresh()
    qtbot.waitUntil(lambda: "\u2026" in window.output_label.text())
    narrow = window.output_label.text()
    assert not window.output_label.wordWrap()
    assert window.output_label.toolTip() == str(path)
    assert window.output_label.accessibleDescription() == str(path)
    assert (
        window.output_label.fontMetrics().horizontalAdvance(narrow) <= window.output_label.width()
    )
    assert window.output_label.geometry().right() < window.output_row.width()
    window.resize(1700, 780)
    qtbot.waitUntil(lambda: window.output_label.text() != narrow)
    assert window.output_button.width() == window.options_button.width()
    assert (
        window.output_label.mapTo(window, QPoint()).x()
        == window.choices_summary.mapTo(window, QPoint()).x()
    )


def test_output_row_three_states_and_keyboard_order(window, qtbot):
    window.output_dir = None
    window._refresh()
    assert window.output_label.text() == M.NO_OUTPUT
    assert window.output_label.objectName() == "warning"
    window.output_dir = Path("C:/Transcripts")
    window._refresh()
    assert window.output_label.text() == M.SAVING_TO.format(path=str(window.output_dir))
    assert window.output_label.objectName() == ""
    window.same_folder.setChecked(True)
    assert window.output_label.text() == M.SAVING_NEXT_TO
    assert not window.output_button.isEnabled()
    window.same_folder.setChecked(False)
    window.model.set_jobs([Job(Path("C:/Recordings/jfk.wav"))])
    window._refresh()
    window.output_button.setFocus()
    for control in (
        window.formats["txt"],
        window.formats["docx"],
        window.options_button,
        window.start_button,
    ):
        qtbot.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
        assert QApplication.focusWidget() is control


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
        Prepared(
            tuple(window.registry.manifest.models), True, {"schema_version": 1}, vad_installed=True
        )
    )
    assert window.model_choice.currentData() == "large-v3-turbo-q8_0"
    assert ", recommended" in window.model_choice.currentText()
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
    assert window.slow_model_notice.text() == M.SLOW


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
    window._startup_dialogs(
        Prepared(window.installed, False, window.settings, recovered, vad_installed=True)
    )
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
        Prepared(
            tuple(window.registry.manifest.models), True, {"schema_version": 1}, vad_installed=True
        )
    )
    window.interactive = True

    def prepare(worker):
        worker.ready.emit(
            Prepared(
                tuple(worker.registry.manifest.models),
                True,
                {"schema_version": 1, "backend": "auto"},
                vad_installed=True,
            )
        )

    monkeypatch.setattr(PrepareWorker, "run", prepare)
    window._set_combo(window.device_choice, "cpu")
    qtbot.waitUntil(lambda: window.ready and not window.preparer.isRunning())
    assert window.device_choice.currentData() == "cpu"
    assert window.model_choice.currentData() == "small"
    assert ", recommended" in window.model_choice.currentText()
    window.interactive = False


def test_resume_never_silently_substitutes_an_uninstalled_model(window, qtbot, tmp_path) -> None:
    window.apply_prepared(Prepared(("tiny",), False, {"schema_version": 1}, vad_installed=True))
    window.restore_batch(BatchOptions("medium", tmp_path / "out"), [Job(tmp_path / "clip.wav")])
    assert not window.start_button.isEnabled()
    assert window.resume_model_button.isVisible()
    assert "Medium" in window.start_hint.text()
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
    qtbot.waitUntil(lambda: window.isActiveWindow() and window.table.hasFocus())
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
    assert window.start_hint.text() == M.CHOOSE_OUTPUT_FIRST
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
    window.options_dialog.hide()
    window.output_dir = tmp_path / "out"
    window.model.set_jobs([Job(tmp_path / "one.wav", status=JobStatus.DONE)])
    window._refresh()
    assert window.start_hint.text() == M.EVERYTHING_DONE
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


def test_message_area_and_disabled_start_guidance(window, tmp_path) -> None:
    from dusty.queue.scanning import ScanResult

    job = Job(tmp_path / "one.wav")
    window.model.set_jobs([job])
    window._scanned(ScanResult((), 0, 1, (job.source,)))
    QApplication.processEvents()
    assert window.status.parentWidget() is window.message_area
    assert window.warning.parentWidget() is window.message_area
    assert window.status.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert window.status.font().pixelSize() >= 16
    assert window.message_area.geometry().top() >= window.table.geometry().bottom()
    assert window.message_area.geometry().bottom() < window.output_row.geometry().top()
    assert window.status.text() == M.DUPLICATE_ONE.format(name="one.wav")
    window.output_dir = None
    window._refresh()
    QApplication.processEvents()
    assert window.start_button.isVisible() and not window.start_button.isEnabled()
    assert window.start_hint.text() == M.CHOOSE_OUTPUT_FIRST
    assert window.start_hint.geometry().bottom() < window.start_button.geometry().top()
    assert window.start_hint.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert window.start_button.width() == window.table.width()
    window.output_dir = tmp_path / "out"
    job.status = JobStatus.DONE
    window._refresh()
    assert window.start_hint.text() == M.EVERYTHING_DONE
    assert M.EVERYTHING_DONE not in window.warning.text()


def test_all_dialogs_have_one_title_and_errors_only_name_reason(window, qtbot) -> None:
    dialogs = [
        WelcomeDialog(window),
        FolderDialog(window),
        CollisionDialog("one.txt", window),
        ResumeDialog(1, window),
        SyncDialog(window),
        CloseDialog(window),
        SummaryDialog([Job(Path("one.wav"), status=JobStatus.DONE)], window),
        TextDialog(M.PRIVACY_TITLE, (M.PRIVACY, M.ACCURACY), window),
        TextDialog(M.ABOUT, (M.ABOUT_VERSION.format(version="test"),), window),
    ]
    for dialog in dialogs + [window.options_dialog]:
        qtbot.addWidget(dialog)
        assert not any(
            label.text() == dialog.windowTitle() for label in dialog.findChildren(QLabel)
        )
    for code in FailureCode:
        dialog = ErrorDialog(code, filename="corrupt.mp3", parent=window)
        qtbot.addWidget(dialog)
        assert [label.text() for label in dialog.findChildren(QLabel)] == [
            M.NAMED_FAILURE.format(name="corrupt.mp3", reason=M.FAILURE_MESSAGES[code].message)
        ]
    generic = ErrorDialog(text=M.SCAN_ERROR, parent=window)
    qtbot.addWidget(generic)
    assert [label.text() for label in generic.findChildren(QLabel)] == [M.SCAN_ERROR]


def test_model_labels_no_estimates_and_cpu_only_slow_warning(window) -> None:
    assert window.model_choice.accessibleName() == M.MODEL == "Transcription model"
    assert M.MODEL_NAMES["small"] == "Small: Balanced, all languages"
    assert M.MODEL_NAMES["small.en"] == "Small English: Balanced, English only"
    window.options_dialog.show()
    for vulkan in (False, True):
        window.vulkan_ok = vulkan
        window._set_combo(window.device_choice, "auto")
        for model_id in window.installed:
            window._set_combo(window.model_choice, model_id)
            window._rules()
            expected = not vulkan and window.registry.manifest.models[model_id].speed_cpu == "slow"
            assert window.model_warning.isVisible() == expected
            assert window.slow_model_notice.isVisible() == expected
            if expected:
                assert window.model_warning.text() == window.slow_model_notice.text() == M.SLOW
            assert not any(
                "On this computer:" in label.text() or "similar laptop" in label.text()
                for label in window.findChildren(QLabel)
            )
    window._set_combo(window.model_choice, "medium")
    window._set_combo(window.device_choice, "cpu")
    assert window.model_warning.isVisible() and window.slow_model_notice.isVisible()
    window._set_combo(window.model_choice, "small")
    assert "Small" in window.model_details.text()
    assert not window.model_warning.isVisible()


@pytest.mark.parametrize("folder_chosen", [False, True])
def test_welcome_uses_output_folder_not_legacy_flag(window, monkeypatch, folder_chosen) -> None:
    window.output_dir = window.paths.user_dir if folder_chosen else None
    window.settings["welcome_seen"] = not folder_chosen
    seen = []
    monkeypatch.setattr(
        WelcomeDialog, "exec", lambda _: seen.append("welcome") or QDialog.DialogCode.Rejected
    )
    prepared = Prepared(window.installed, False, window.settings, vad_installed=True)
    window._startup_dialogs(prepared)
    window._startup_dialogs(prepared)
    assert seen == ([] if folder_chosen else ["welcome"])


def test_welcome_finishes_before_resume_and_reentrant_startup_is_ignored(
    window, monkeypatch, qtbot
) -> None:
    window.output_dir = None
    options = BatchOptions("tiny", window.paths.user_dir / "out")
    prepared = Prepared(
        window.installed,
        False,
        window.settings,
        (options, [Job(Path("one.wav"), elapsed_sec=99)]),
        vad_installed=True,
    )
    seen = []

    def welcome(dialog):
        seen.append("welcome opened")
        window._startup_dialogs(prepared)
        QApplication.processEvents()
        assert seen == ["welcome opened"]
        seen.append("welcome dismissed")
        return QDialog.DialogCode.Rejected

    def resume(dialog):
        assert seen == ["welcome opened", "welcome dismissed"]
        seen.append("resume")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(WelcomeDialog, "exec", welcome)
    monkeypatch.setattr(ResumeDialog, "exec", resume)
    monkeypatch.setattr(window, "start_batch", lambda: seen.append("started"))
    window._startup_dialogs(prepared)
    qtbot.waitUntil(lambda: "started" in seen)
    assert seen == ["welcome opened", "welcome dismissed", "resume", "started"]
    assert window.model.jobs[0].elapsed_sec == 0


def test_start_stays_full_width_and_disabled_text_contrast(window, qtbot, tmp_path):
    from dusty.app.theme import DISABLED_COLORS, apply_theme, contrast_ratio

    window.model.set_jobs([Job(tmp_path / "one.wav")])
    for running, output in ((False, None), (False, tmp_path / "out"), (True, tmp_path / "out")):
        window.output_dir = output
        window.running = running
        window._refresh()
        QApplication.processEvents()
        assert window.start_button.isVisible()
        assert window.start_button.width() == window.table.width()
        if not window.start_button.isEnabled():
            assert window.start_hint.isVisible() and window.start_hint.text()
            assert window.start_hint.geometry().bottom() < window.start_button.geometry().top()
    window.running = False
    window.output_dir = None
    window._refresh()
    apply_theme(QApplication.instance(), "dark")
    qtbot.wait(20)
    image = window.start_button.grab().toImage()
    colors = {
        image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())
    }
    assert DISABLED_COLORS["dark"]["ink"] in colors
    assert (
        contrast_ratio(DISABLED_COLORS["dark"]["ink"], DISABLED_COLORS["dark"]["background"]) >= 4.5
    )
    for model_id in window.installed:
        name = M.RECOMMENDED.format(name=M.MODEL_NAMES[model_id])
        assert name.endswith(", recommended") and "(Recommended)" not in name
    apply_theme(QApplication.instance(), "light")


@pytest.mark.parametrize("area", ["work", "models", "state", "logs"])
def test_managed_source_and_output_refused(window, tmp_path, monkeypatch, area):
    from dusty.queue import Coordinator

    folder = window.paths.user_dir / area
    folder.mkdir(parents=True)
    errors = []
    monkeypatch.setattr(window, "show_error", lambda **kw: errors.append(kw["text"]))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: str(folder))
    original = window.output_dir
    window.choose_output()
    assert window.output_dir == original
    window.add_paths([folder / "recording.wav"])
    assert errors == [M.MANAGED_FOLDER, M.MANAGED_FOLDER]
    source = tmp_path / "recording.wav"
    source.write_bytes(b"public synthetic")
    with pytest.raises(ValueError, match="Managed folders"):
        Coordinator(window.paths, window.registry).run_batch(
            [Job(source)], BatchOptions("tiny", folder)
        )
    with pytest.raises(ValueError, match="Managed folders"):
        Coordinator(window.paths, window.registry).run_batch(
            [Job(folder / "recording.wav")], BatchOptions("tiny", original, same_folder=True)
        )


def test_prepared_missing_voice_flag_fails_closed():
    assert Prepared((), False, {}).vad_installed is False


def test_legacy_silence_default_migrates_off_then_explicit_choice_survives(window):
    window.apply_prepared(
        Prepared(window.installed, False, {"schema_version": 1, "vad": True}, vad_installed=True)
    )
    assert not window.vad.isChecked()
    assert M.SILENCE_ON not in window.choices_summary.text()
    assert "Skip long silences off" not in window.choices_summary.text()
    window.vad.setChecked(True)
    assert window._save_settings()
    from dusty.queue.storage import load_settings

    saved = load_settings(window.paths.user_dir / "settings.json")
    assert saved["vad_user_set"] is True and saved["vad"] is True
    window.apply_prepared(Prepared(window.installed, False, saved, vad_installed=True))
    assert window.vad.isChecked()


@pytest.mark.parametrize("saved", [None, False, True])
def test_silence_default_preserves_explicit_choice(window, saved):
    settings = {"schema_version": 1}
    if saved is not None:
        settings["vad"] = saved
        settings["vad_user_set"] = True
    window.apply_prepared(Prepared(window.installed, False, settings, vad_installed=True))
    assert window.vad.isChecked() is (saved is True)
    assert BatchOptions("tiny", window.output_dir).vad is False
    assert window.vad.text() == "Skip long silences"


def test_readding_done_resets_only_that_recording(window, tmp_path):
    from dusty.queue.scanning import scan_inputs

    sources = [tmp_path / f"clip{i}.wav" for i in range(5)]
    for source in sources:
        source.write_bytes(b"synthetic recording")
    jobs = [
        Job(source, status=status, elapsed_sec=42, progress=1)
        for source, status in zip(
            sources,
            [
                JobStatus.DONE,
                JobStatus.DONE,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.SKIPPED,
            ],
            strict=True,
        )
    ]
    old_output = tmp_path / "clip0.txt"
    old_output.write_text("Existing transcript")
    jobs[0].outputs = [old_output]
    window.model.set_jobs(jobs)
    window.vad.setChecked(False)
    window._scanned(scan_inputs([sources[0], *sources[2:]], existing=jobs))
    assert [job.status for job in jobs] == [
        JobStatus.QUEUED,
        JobStatus.DONE,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.SKIPPED,
    ]
    assert len(window.model.jobs) == 5
    assert jobs[0].elapsed_sec == jobs[0].progress == 0
    assert jobs[0].outputs == [] and old_output.read_text() == "Existing transcript"
    assert window.start_button.isEnabled()
    assert window.batch_options().vad is False
    assert window.status.text() == (
        M.READY_AGAIN.format(count=1) + " " + M.DUPLICATE_MANY.format(count=3)
    )


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_seven_title_clicks_greeting_is_memory_only(window, qtbot, monkeypatch, caplog, theme):
    from dusty.app import window as module
    from dusty.app.dialogs import GreetingDialog
    from dusty.app.theme import apply_theme

    apply_theme(QApplication.instance(), theme)
    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    file = window.paths.user_dir / "settings.json"
    before = file.read_bytes() if file.exists() else None
    settings = dict(window.settings)
    seen = []

    def inspect(dialog):
        assert [label.text() for label in dialog.findChildren(QLabel)] == ["Salam maman"]
        assert [button.text() for button in dialog.findChildren(QPushButton)] == [M.OK]
        assert window._title_clicks == 0
        seen.append(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(GreetingDialog, "exec", inspect)
    for _ in range(6):
        qtbot.mouseClick(window.title, Qt.MouseButton.LeftButton)
    assert not seen
    clock[0] += 4.1
    qtbot.mouseClick(window.title, Qt.MouseButton.LeftButton)
    assert not seen and window._title_clicks == 1
    for _ in range(6):
        clock[0] += 0.1
        qtbot.mouseClick(window.title, Qt.MouseButton.LeftButton)
    assert seen == [True]
    qtbot.mouseClick(window.title, Qt.MouseButton.LeftButton)
    assert seen == [True] and window._title_clicks == 1
    assert window.settings == settings
    assert (file.read_bytes() if file.exists() else None) == before
    assert not caplog.records


def test_readding_done_keeps_mixed_scan_information(window, tmp_path):
    from dusty.queue.scanning import scan_inputs

    done = tmp_path / "done.wav"
    new = tmp_path / "new.wav"
    bad = tmp_path / "unsupported.exe"
    for file in (done, new, bad):
        file.write_bytes(b"synthetic")
    window.model.set_jobs([Job(done, status=JobStatus.DONE)])
    window._scanned(scan_inputs([done, new, bad], existing=window.model.jobs))
    assert M.READY_AGAIN.format(count=1) in window.status.text()
    assert M.ADDED_ONE in window.status.text()
    assert M.UNSUPPORTED_ONE in window.status.text()
    assert len(window.model.jobs) == 2
    assert all(job.status == JobStatus.QUEUED for job in window.model.jobs)


@pytest.mark.parametrize("enabled", [True, False])
def test_resume_keeps_the_batches_explicit_silence_choice(window, tmp_path, enabled):
    from dusty.queue.storage import load_settings

    window.vad.setChecked(not enabled)
    window.restore_batch(
        BatchOptions("tiny", tmp_path / "out", vad=enabled), [Job(tmp_path / "lecture.wav")]
    )
    assert window.vad.isChecked() is enabled
    assert window.batch_options().vad is enabled
    assert window._save_settings()
    saved = load_settings(window.paths.user_dir / "settings.json")
    assert saved["vad"] is enabled and saved["vad_user_set"] is True
