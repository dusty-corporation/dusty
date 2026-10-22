"""Run real native processing while measuring Qt event-loop responsiveness."""

import shutil
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtWidgets import QDialog

from dusty.app.dialogs import CloseDialog, CollisionDialog, ResumeDialog, SyncDialog
from dusty.app.window import MainWindow
from dusty.app.workers import Prepared
from dusty.core import Job, JobStatus
from dusty.queue.storage import load_batch
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


def ready_window(qtbot, tmp_path):
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    window = MainWindow(paths, interactive=False)
    qtbot.addWidget(window)
    window.apply_prepared(Prepared(("tiny",), False, {"schema_version": 1, "welcome_seen": True}))
    window.output_dir = tmp_path / "out"
    window.show()
    return window


def test_real_batch_event_loop_gap_never_exceeds_200ms(qtbot, tmp_path, monkeypatch) -> None:
    window = ready_window(qtbot, tmp_path)
    window.model.set_jobs([Job(ROOT / "tests/fixtures/audio/formats/jfk.wav", duration_sec=11)])
    window._set_combo(window.device_choice, "cpu")
    window.threads_choice.setValue(2)
    window._refresh()
    update_threads = []
    original = window.model.update_job

    def update(job):
        update_threads.append(QThread.currentThread())
        original(job)

    monkeypatch.setattr(window.model, "update_job", update)
    qtbot.wait(100)
    ticks = [time.perf_counter()]
    timer = QTimer()
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    window.start_batch()
    assert window.running
    qtbot.waitUntil(lambda: not window.running, timeout=60000)
    ticks.append(time.perf_counter())
    timer.stop()
    assert window.model.jobs[0].status == JobStatus.DONE
    assert len(window.model.jobs[0].outputs) == 2
    assert len(ticks) > 10
    assert update_threads and all(thread == window.thread() for thread in update_threads)
    maximum_gap = max(b - a for a, b in zip(ticks, ticks[1:], strict=False))
    print(f"qt_maximum_event_gap_ms={maximum_gap * 1000:.3f}")
    assert maximum_gap <= 0.200, f"Qt event-loop maximum gap: {maximum_gap:.3f} seconds"


def test_ui_cancel_current_and_collision_apply_to_all(qtbot, tmp_path, monkeypatch) -> None:
    window = ready_window(qtbot, tmp_path)
    window.vad.setChecked(False)
    other = tmp_path / "other.wav"
    shutil.copyfile(ROOT / "tests/fixtures/audio/formats/jfk.wav", other)
    window.model.set_jobs(
        [
            Job(ROOT / "tests/fixtures/audio/vad/mostly-silence-10min.m4a"),
            Job(ROOT / "tests/fixtures/audio/formats/jfk.wav"),
            Job(other),
        ]
    )
    window.output_dir.mkdir()
    existing = window.output_dir / "jfk.txt"
    existing.write_bytes(b"keep this")
    (window.output_dir / "other.txt").write_bytes(b"also keep this")
    seen = []

    def collision(dialog):
        seen.append(True)
        assert dialog.apply_all.isChecked()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(CollisionDialog, "exec", collision)
    window._refresh()
    window.start_batch()
    qtbot.waitUntil(lambda: window.model.jobs[0].status == JobStatus.TRANSCRIBING, timeout=15000)
    qtbot.mouseClick(window.cancel_current_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.running, timeout=30000)
    assert window.model.jobs[0].status == JobStatus.CANCELLED
    assert window.model.jobs[1].status == JobStatus.DONE
    assert existing.read_bytes() == b"keep this"
    assert seen == [True]
    assert (window.output_dir / "jfk (1).docx").exists()
    assert (window.output_dir / "other (1).docx").exists()
    assert window.model.jobs[2].status == JobStatus.DONE


def test_close_mid_batch_saves_resume_and_sync_warning(qtbot, tmp_path, monkeypatch) -> None:
    window = ready_window(qtbot, tmp_path)
    source = tmp_path / "long.m4a"
    shutil.copyfile(ROOT / "tests/fixtures/audio/vad/mostly-silence-10min.m4a", source)
    window.model.set_jobs([Job(source)])
    window.vad.setChecked(False)
    warnings = []
    monkeypatch.setattr("dusty.app.window.is_synced", lambda path: True)
    monkeypatch.setattr(
        SyncDialog, "exec", lambda self: warnings.append(True) or QDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(CloseDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window._refresh()
    window.start_batch()
    qtbot.waitUntil(lambda: window.model.jobs[0].status == JobStatus.TRANSCRIBING, timeout=15000)
    window.close()
    qtbot.waitUntil(lambda: not window.running and not window.isVisible(), timeout=15000)
    assert warnings == [True]
    recovered = load_batch(window.paths.user_dir / "state/queue.json")
    assert recovered is not None
    assert recovered[1][0].status == JobStatus.QUEUED
    assert list((window.paths.user_dir / "work").iterdir()) == []
    second = ready_window(qtbot, tmp_path)
    monkeypatch.setattr(ResumeDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    second._startup_dialogs(Prepared(("tiny",), False, second.settings, recovered))
    assert second.model.rowCount() == 1
    assert second.model.jobs[0].id == recovered[1][0].id
    second.vad.setChecked(True)
    second._refresh()
    second.start_batch()
    qtbot.waitUntil(lambda: not second.running, timeout=60000)
    assert second.model.jobs[0].status == JobStatus.DONE
