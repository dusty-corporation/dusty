"""Exercise actual TLS downloader children through the Qt Model Manager."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QLabel
from test_downloader import CERTS, DATA
from test_downloader import tls as tls

from dusty.app import messages as M
from dusty.app.dialogs import TextDialog
from dusty.app.model_manager import VOICE_ID, DownloadDialog, ModelManager, ModelWorker, format_size
from dusty.app.window import MainWindow
from dusty.app.workers import Prepared
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import RuntimePaths, resolve_fetch_command, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def models(tmp_path, qtbot, monkeypatch, request):
    server = request.getfixturevalue("tls")
    resources = tmp_path / "resources"
    resources.mkdir()
    data = json.loads((ROOT / "resources/models.json").read_text())
    for entry in data["models"] + data["vad"]:
        if entry["id"] in {"tiny", "small", VOICE_ID}:
            entry.update(
                url=server.url,
                size_bytes=len(DATA),
                sha256=hashlib.sha256(DATA).hexdigest(),
                file_name="ggml-" + entry["id"] + "-test.bin",
            )
    (resources / "models.json").write_text(json.dumps(data), encoding="utf-8")
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, tmp_path / "models", resources, tmp_path / "user")
    paths.models_dir.mkdir()
    registry = ModelRegistry(load_manifest(resources / "models.json"), paths.models_dir)
    command = [
        str(Path(sys.executable).resolve()),
        str(CERTS / "fetch_child.py"),
        str(server.port),
        str(CERTS / "localhost.pem"),
    ]
    monkeypatch.setattr(DownloadDialog, "exec", lambda _: QDialog.DialogCode.Accepted)

    def create(*, voice=False, selected=lambda: None, registry=registry):
        dialog = ModelManager(
            registry,
            paths,
            selected=selected,
            voice_in_use=lambda: voice,
            focus_id="tiny",
            command=command,
        )
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitUntil(lambda: bool(dialog.workers) and not dialog.busy)
        assert dialog.workers[-1].failure is None
        return dialog

    return SimpleNamespace(
        paths=paths,
        command=command,
        registry=registry,
        create=create,
        tls=server,
        file=paths.models_dir
        / data["models"][[e["id"] for e in data["models"]].index("tiny")]["file_name"],
    )


def wait_done(dialog, qtbot):
    qtbot.waitUntil(lambda: not dialog.busy, timeout=15000)


def test_catalog_statuses_space_and_confirmation_download_progress(models, qtbot, monkeypatch):
    monkeypatch.setattr(
        "dusty.app.model_manager.shutil.disk_usage", lambda _: SimpleNamespace(free=2_500_000_000)
    )
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), False, {}, vad_installed=False))
    dialog = models.create(voice=True, registry=view.registry)
    dialog.models_changed.connect(view._models_changed)
    assert set(dialog.ids) == set(models.registry.manifest.models) | {VOICE_ID}
    assert all(state == "not_installed" for state in dialog.statuses.values())
    assert dialog.free_space.text() == M.FREE_SPACE.format(gb=2.5)
    confirm = DownloadDialog(("tiny", VOICE_ID), models.registry, dialog)
    qtbot.addWidget(confirm)
    assert M.DOWNLOAD_CONFIRM.format(
        names="Tiny and Voice detection", size=format_size(2 * len(DATA))
    ) in [label.text() for label in confirm.findChildren(QLabel)]
    assert M.VOICE_MODEL in confirm.findChildren(QLabel)[0].text()
    dialog.download()
    worker = dialog.worker
    events = []
    worker.progress.connect(events.append)
    wait_done(dialog, qtbot)
    assert dialog.statuses["tiny"] == dialog.statuses[VOICE_ID] == "installed"
    assert models.registry.model_path("tiny").read_bytes() == DATA
    assert models.registry.vad_path().read_bytes() == DATA
    assert events and events[-1]["bytes"] == len(DATA)
    assert len(worker.pids) == 2 and all(pid > 0 for pid in worker.pids)
    assert dialog.message.text() == M.DOWNLOAD_FINISHED
    assert not list(models.paths.models_dir.glob("*.part"))
    assert view.model_choice.currentData() == "tiny" and "tiny" in view.installed
    dialog.table.selectRow(dialog.ids.index("small"))
    dialog.download()
    wait_done(dialog, qtbot)
    assert view.model_choice.currentData() == "tiny"
    dialog.table.selectRow(dialog.ids.index(VOICE_ID))
    assert dialog.delete_button.isEnabled()


def test_cancel_removes_part_and_new_dialog_starts_fresh(models, qtbot):
    models.tls.mode = "slow"
    dialog = models.create()
    dialog.download()
    part = models.file.with_suffix(".bin.part")
    qtbot.waitUntil(lambda: part.exists() and part.stat().st_size > 0, timeout=10000)
    dialog.cancel()
    wait_done(dialog, qtbot)
    assert not part.exists() and not models.file.exists()
    assert dialog.message.text() == M.DOWNLOAD_PAUSED
    dialog.close()
    models.tls.mode = "normal"
    fresh_registry = ModelRegistry(models.registry.manifest, models.paths.models_dir)
    resumed = models.create(registry=fresh_registry)
    resumed.download()
    wait_done(resumed, qtbot)
    assert resumed.statuses["tiny"] == "installed"
    assert not any(models.tls.requests)
    assert not part.exists()


def test_hash_mismatch_is_damaged_and_never_installed(models, qtbot):
    manifest_path = models.paths.resources_dir / "models.json"
    data = json.loads(manifest_path.read_text())
    next(item for item in data["models"] if item["id"] == "tiny")["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    registry = ModelRegistry(load_manifest(manifest_path), models.paths.models_dir)
    dialog = models.create(registry=registry)
    dialog.download()
    wait_done(dialog, qtbot)
    assert dialog.statuses["tiny"] == "damaged"
    assert dialog.download_button.text() == M.DOWNLOAD_AGAIN
    assert dialog.message.text() == M.FETCH_ERRORS["MISMATCH"]
    assert not models.file.exists() and not list(models.paths.models_dir.glob("*.part"))


def test_verify_all_rehashes_and_delete_requires_confirmation_and_safe_choice(
    models, qtbot, monkeypatch
):
    models.file.write_bytes(DATA)
    small = models.paths.models_dir / models.registry.manifest.models["small"].file_name
    small.write_bytes(DATA)
    choice = ["tiny"]
    dialog = models.create(selected=lambda: choice[0])
    assert dialog.delete_button.isEnabled()
    choice[0] = "small"
    dialog._refresh()
    assert dialog.delete_button.isEnabled()
    monkeypatch.setattr(TextDialog, "exec", lambda _: QDialog.DialogCode.Rejected)
    dialog.delete()
    assert models.file.exists()
    monkeypatch.setattr(TextDialog, "exec", lambda _: QDialog.DialogCode.Accepted)
    dialog.delete()
    wait_done(dialog, qtbot)
    assert not models.file.exists() and small.exists()
    choice[0] = None
    dialog.table.selectRow(dialog.ids.index("small"))
    assert dialog.delete_button.isEnabled()
    original = small.stat()
    small.write_bytes(b"x" * len(DATA))
    os.utime(small, ns=(original.st_atime_ns, original.st_mtime_ns))
    dialog.verify_all()
    wait_done(dialog, qtbot)
    assert dialog.statuses["small"] == "damaged"


def test_no_download_without_consent_and_worker_allows_selected_last_delete(
    models, qtbot, monkeypatch
):
    models.file.write_bytes(DATA)
    dialog = models.create()
    worker = ModelWorker(
        models.registry, models.paths, action="delete", ids=("tiny",), selected="tiny"
    )
    worker.run()
    assert not models.file.exists() and worker.failure is None
    dialog.table.selectRow(dialog.ids.index("small"))
    monkeypatch.setattr(DownloadDialog, "exec", lambda _: QDialog.DialogCode.Rejected)
    dialog.download()
    assert not dialog.busy and not models.tls.requests


def test_main_prompts_live_update_and_preserves_explicit_choice(models, qtbot, monkeypatch):
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.show()
    view.apply_prepared(
        Prepared((), False, {"output_dir": str(models.paths.user_dir)}, vad_installed=False)
    )
    assert view.start_hint.text() == M.NO_MODELS
    assert view.download_recommended_button.isVisible() and not view.start_button.isEnabled()
    assert view.warning.text() == M.MISSING_RECOMMENDATION.format(name="Small")
    opened = []
    monkeypatch.setattr(view, "open_model_manager", lambda **kw: opened.append(kw["focus_id"]))
    view.download_recommended_button.click()
    assert opened == ["small"]
    models.file.write_bytes(DATA)
    small = models.paths.models_dir / models.registry.manifest.models["small"].file_name
    small.write_bytes(DATA)
    dialog = models.create(registry=view.registry)
    dialog.models_changed.connect(view._models_changed)
    dialog.verify_all()
    wait_done(dialog, qtbot)
    assert view.model_choice.currentData() == "small"  # Implicit recommendation.
    view._set_combo(view.model_choice, "tiny")
    view._model_chosen()
    dialog.verify_all()
    wait_done(dialog, qtbot)
    assert view.model_choice.currentData() == "tiny"
    assert view.start_hint.text() == M.VAD_MISSING
    view.download_recommended_button.click()
    assert opened[-1] == VOICE_ID
    view.vad.setChecked(False)
    assert view.start_hint.text() == M.ADD_RECORDINGS_FIRST


def test_fetch_command_separates_source_and_split_packaged_runtime(tmp_path):
    source = tmp_path / "venv/Scripts/python.exe"
    assert resolve_fetch_command(frozen=False, executable=source) == [
        str(source.resolve()),
        "-m",
        "dusty_fetch",
    ]
    app = tmp_path / "install/dusty/dusty.exe"
    assert resolve_fetch_command(frozen=True, executable=app) == [
        str((tmp_path / "install/dusty-fetch/dusty-fetch.exe").resolve())
    ]


def test_closing_manager_cancels_child_and_removes_part(models, qtbot):
    models.tls.mode = "slow"
    dialog = models.create()
    dialog.download()
    part = models.file.with_suffix(".bin.part")
    qtbot.waitUntil(lambda: part.exists() and part.stat().st_size > 0, timeout=10000)
    dialog.done(QDialog.DialogCode.Rejected)
    qtbot.waitUntil(lambda: not dialog.busy and not dialog.isVisible(), timeout=15000)
    assert not part.exists() and not models.file.exists()
    assert dialog.workers[-1].cancelled.is_set()


@pytest.mark.parametrize("entry", ["tools", "options"])
def test_model_manager_is_reachable_from_tools_and_options(models, qtbot, monkeypatch, entry):
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), False, {"output_dir": str(models.paths.user_dir)}))
    view.show()
    seen = []

    def dismiss():
        dialog = view.model_manager
        if dialog is not None and not dialog.busy:
            seen.append(dialog.selected_id())
            dialog.accept()

    timer = QTimer()
    timer.timeout.connect(dismiss)
    timer.start(20)
    if entry == "tools":
        view.manage_models_action.trigger()
    else:
        view.options_dialog.show()
        view.manage_models_button.click()
        view.options_dialog.hide()
    timer.stop()
    assert seen and view.model_manager is not None


def test_main_window_close_cancels_model_child_without_orphan(models, qtbot, monkeypatch):
    models.tls.mode = "slow"
    monkeypatch.setattr("dusty.app.model_manager.resolve_fetch_command", lambda: models.command)
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), False, {"output_dir": str(models.paths.user_dir)}))
    view.show()
    started = []
    part = models.file.with_suffix(".bin.part")

    def drive():
        dialog = view.model_manager
        if dialog is None or view.closing:
            return
        try:
            partial_bytes = part.stat().st_size
        except FileNotFoundError:
            partial_bytes = 0  # The cancelled child may remove it between timer ticks.
        if not started and not dialog.busy and bool(dialog.workers):
            started.append(True)
            QTimer.singleShot(0, dialog.download_button.click)
        elif partial_bytes > 0:
            view.close()

    timer = QTimer()
    timer.timeout.connect(drive)
    timer.start(20)
    QTimer.singleShot(0, lambda: view.open_model_manager(focus_id="tiny"))
    qtbot.waitUntil(lambda: bool(started) and not view.isVisible(), timeout=15000)
    timer.stop()
    assert not part.exists() and not models.file.exists()
    assert not any(worker.isRunning() for worker in view._tasks)


def test_real_entry_download_check_refuses_non_ci_use(models):
    environment = {**os.environ, "GITHUB_ACTIONS": "false"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dusty",
            "--check-model-download",
            "--out",
            str(models.paths.user_dir),
        ],
        env=environment,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert not (models.paths.user_dir / "download-result.json").exists()


def test_guarded_real_gui_download_exercise_with_local_tls(models):
    environment = {**os.environ, "GITHUB_ACTIONS": "true", "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run(
        [
            sys.executable,
            str(CERTS / "gui_download_check.py"),
            str(models.tls.port),
            str(CERTS / "localhost.pem"),
            str(models.paths.resources_dir),
            str(models.paths.user_dir),
            str(models.paths.user_dir / "audit"),
        ],
        env=environment,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    evidence = json.loads((models.paths.user_dir / "audit/download-result.json").read_text())
    assert evidence["verified"] and evidence["consent_confirmed"] and evidence["guard_installed"]
    assert len(evidence["fetch_pids"]) == 2
    assert evidence["gui_pid"] not in evidence["fetch_pids"]
    assert len(models.tls.requests) == 2


def test_selected_last_and_voice_deletion_clear_choice_without_replacement(
    models, qtbot, monkeypatch
):
    from dusty.core import Job
    from dusty.queue.storage import load_settings

    models.file.write_bytes(DATA)
    small = models.paths.models_dir / models.registry.manifest.models["small"].file_name
    small.write_bytes(DATA)
    voice = models.paths.models_dir / models.registry.manifest.vad_file_name
    voice.write_bytes(DATA)
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            ("tiny", "small"),
            False,
            {"model_id": "tiny", "output_dir": str(models.paths.user_dir)},
            vad_installed=True,
        )
    )
    view.model.set_jobs([Job(Path("sample.wav"))])
    view._refresh()
    view.show()
    dialog = models.create(
        registry=view.registry, voice=True, selected=lambda: view.model_choice.currentData()
    )
    dialog.models_changed.connect(view._models_changed)
    confirmations = []

    def accept(dialog):
        confirmations.extend(label.text() for label in dialog.findChildren(QLabel))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(TextDialog, "exec", accept)
    dialog.delete()
    wait_done(dialog, qtbot)
    assert M.DELETE_SELECTED.format(name="Tiny") in confirmations
    assert view.model_choice.currentIndex() == -1 and view.installed == ("small",)
    assert view.model_choice.placeholderText() == M.MODEL_PLACEHOLDER
    assert M.NO_MODEL_SELECTED in view.choices_summary.text()
    assert view.start_hint.text() == M.CHOOSE_MODEL
    assert not hasattr(view, "choose_model_button")
    assert view.options_button.isVisible() and not view.start_button.isEnabled()
    assert view.status.text() != M.READY
    assert not view.download_recommended_button.isVisible()
    assert load_settings(view.paths.user_dir / "settings.json")["model_id"] is None
    reopened = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(reopened)
    reopened.apply_prepared(
        Prepared(
            ("small",),
            False,
            load_settings(view.paths.user_dir / "settings.json"),
            vad_installed=True,
        )
    )
    assert reopened.model_choice.currentIndex() == -1
    # Newly downloaded Tiny is selected only because the previous choice is empty.
    dialog.table.selectRow(dialog.ids.index("tiny"))
    dialog.download()
    wait_done(dialog, qtbot)
    assert view.model_choice.currentData() == "tiny"
    dialog.table.selectRow(dialog.ids.index(VOICE_ID))
    dialog.delete()
    wait_done(dialog, qtbot)
    assert M.DELETE_VOICE.format(name=M.VOICE_MODEL) in confirmations
    assert view.start_hint.text() == M.VAD_MISSING
    assert not view.start_button.isEnabled()
    for key in ("small", "tiny"):
        dialog.table.selectRow(dialog.ids.index(key))
        dialog.delete()
        wait_done(dialog, qtbot)
    assert not view.installed and view.start_hint.text() == M.NO_MODELS
    assert view.download_recommended_button.isVisible()


def test_manager_name_quality_note_and_best_for_are_distinct(models, qtbot):
    dialog = models.create()
    assert dialog.table.columnCount() == 4
    for row, key in enumerate(dialog.ids):
        labels = dialog.table.cellWidget(row, 0).findChildren(QLabel)
        assert len(labels) == 3
        name = M.VOICE_MODEL if key == VOICE_ID else M.MODEL_TECHNICAL[key]
        assert labels[0].text() == (M.RECOMMENDED.format(name=name) if key == "small" else name)
        assert labels[0].font().bold()
        assert labels[1].text() == M.MODEL_QUALITY[key]
        assert labels[2].text() == M.MODEL_NOTE[key]
        assert labels[2].font().pointSizeF() < labels[1].font().pointSizeF()
        assert dialog.table.item(row, 1).text() == M.MODEL_BEST_FOR[key]
    assert dialog.review_notice.text() == M.MODEL_REVIEW
    assert dialog.cancel_button.isVisible() and not dialog.cancel_button.isEnabled()


def test_missing_voice_button_targets_voice_when_another_model_is_installed(
    models, qtbot, monkeypatch
):
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            ("tiny",),
            False,
            {"model_id": "tiny", "output_dir": str(models.paths.user_dir)},
            vad_installed=False,
        )
    )
    view.show()
    opened = []
    monkeypatch.setattr(view, "open_model_manager", lambda **kw: opened.append(kw["focus_id"]))
    assert view._recommendation == "small" and "small" not in view.installed
    assert view.download_recommended_button.text() == M.DOWNLOAD_VOICE
    view.download_recommended_button.click()
    assert opened == [VOICE_ID]
    assert not view.warning.text().startswith(M.MODEL_NAMES["small"])


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_catalog_selected_row_labels_use_legible_highlight_ink(models, qtbot, qapp, theme):
    from PySide6.QtGui import QPalette

    from dusty.app.theme import apply_theme, contrast_ratio

    apply_theme(qapp, theme)
    dialog = models.create()
    for row in range(dialog.table.rowCount()):
        dialog.table.selectRow(row)
        labels = dialog.table.cellWidget(row, 0).findChildren(QLabel)
        for label in labels:
            assert label.foregroundRole() == QPalette.ColorRole.HighlightedText
            ink = label.palette().color(label.foregroundRole()).name()
            background = dialog.table.palette().highlight().color().name()
            assert contrast_ratio(ink, background) >= 4.5
        for other in range(dialog.table.rowCount()):
            if other != row:
                assert all(
                    label.foregroundRole() == QPalette.ColorRole.WindowText
                    for label in dialog.table.cellWidget(other, 0).findChildren(QLabel)
                )
    apply_theme(qapp, "light")


def test_backend_recommendation_change_preserves_a_deliberate_model_choice(models, qtbot):
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            ("small", "large-v3-turbo-q8_0"),
            False,
            {"model_id": "small", "output_dir": str(models.paths.user_dir)},
            vad_installed=True,
        )
    )
    view._model_chosen()
    view._device_changed()
    view._device_prepared(Prepared(view.installed, True, {}, vad_installed=True))
    assert view._recommendation == "large-v3-turbo-q8_0"
    assert view.model_choice.currentData() == "small"


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (874_200_000, "874.2\u00a0MB"),
        (999_900_000, "999.9\u00a0MB"),
        (999_999_999, "1.0\u00a0GB"),
        (1_000_000_000, "1.0\u00a0GB"),
        (1_533_000_000, "1.5\u00a0GB"),
    ],
)
def test_model_size_units_keep_number_and_unit_together(size, expected):
    assert format_size(size) == expected


def test_consent_joins_names_with_and_and_uses_catalog_size_units(models, qtbot):
    for ids in (("large-v3-turbo-q8_0", VOICE_ID), ("medium",)):
        dialog = DownloadDialog(ids, models.registry)
        qtbot.addWidget(dialog)
        text = dialog.findChildren(QLabel)[0].text()
        assert "," not in text
        assert "\u00a0" in text
        assert " MB" not in text and " GB" not in text
        if len(ids) == 2:
            assert "Large v3 Turbo and Voice detection" in text
        else:
            assert "1.5\u00a0GB" in text
    manager = models.create()
    medium = manager.ids.index("medium")
    assert manager.table.item(medium, 2).text() == "1.5\u00a0GB"


def test_checked_feedback_only_after_explicit_verify_with_installed_files(models, qtbot):
    empty = models.create()
    assert empty.message.text() == M.EMPTY_CELL
    empty.verify_button.click()
    wait_done(empty, qtbot)
    assert empty.message.text() == M.EMPTY_CELL
    models.file.write_bytes(DATA)
    dialog = models.create()
    assert dialog.statuses["tiny"] == "installed"
    assert dialog.message.text() == M.EMPTY_CELL
    dialog.verify_button.click()
    wait_done(dialog, qtbot)
    assert dialog.message.text() == M.MODELS_READY
    # A newly opened dialog must not inherit the previous Verify all feedback.
    fresh = models.create()
    assert fresh.message.text() == M.EMPTY_CELL
    models.file.unlink()
    dialog.verify_button.click()
    wait_done(dialog, qtbot)
    assert dialog.message.text() == M.EMPTY_CELL


def test_progress_names_active_download_and_does_not_repeat_percent(models, qtbot):
    dialog = models.create()
    dialog._progress(
        {
            "id": "large-v3-turbo-q8_0",
            "event": "downloading",
            "bytes": 291_400_000,
            "total": 874_200_000,
        }
    )
    assert dialog.message.text() == "Downloading Large v3 Turbo"
    assert dialog.progress.value() == 33
    assert dialog.progress_text.text() == "291.4\u00a0MB of 874.2\u00a0MB"
    assert "%" not in dialog.progress_text.text()


@pytest.mark.parametrize(
    ("key", "selected", "voice", "expected"),
    [
        ("tiny", None, False, "Delete Tiny? You can download it again later."),
        (
            "small",
            "small",
            False,
            "Delete Small? It is the model chosen in Options. You can download it again later.",
        ),
        (
            VOICE_ID,
            None,
            True,
            "Delete Voice detection? Skip silent parts is on, so Start will be unavailable "
            "until you download it again or turn off Skip silent parts in Options.",
        ),
    ],
)
def test_delete_confirmation_names_file_and_explains_recovery(
    models, qtbot, monkeypatch, key, selected, voice, expected
):
    file_name = (
        models.registry.manifest.vad_file_name
        if key == VOICE_ID
        else models.registry.manifest.models[key].file_name
    )
    (models.paths.models_dir / file_name).write_bytes(DATA)
    dialog = models.create(selected=lambda: selected, voice=voice)
    dialog.table.selectRow(dialog.ids.index(key))
    texts = []

    def reject(confirm):
        texts.extend(label.text() for label in confirm.findChildren(QLabel))
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(TextDialog, "exec", reject)
    dialog.delete_button.click()
    assert texts == [expected]
    if key != VOICE_ID:
        assert "You can download it again later." in expected
    else:
        assert "Start will be unavailable until" in expected
    assert (models.paths.models_dir / file_name).exists()


@pytest.mark.parametrize(("vulkan", "name"), [(False, "Small"), (True, "Large v3 Turbo")])
def test_empty_model_recommendation_uses_only_short_model_name(models, qtbot, vulkan, name):
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), vulkan, {}, vad_installed=False))
    assert view.warning.text() == f"The recommended model, {name}, is not installed yet."


def test_verify_all_enabled_for_voice_only_but_not_an_empty_catalog(models, qtbot, monkeypatch):
    dialog = models.create()
    assert not dialog.verify_button.isEnabled()
    before = len(dialog.workers)
    dialog.verify_button.click()
    assert len(dialog.workers) == before
    voice = models.paths.models_dir / models.registry.manifest.vad_file_name
    voice.write_bytes(DATA)
    installed = models.create(voice=True)
    assert installed.statuses[VOICE_ID] == "installed"
    assert not any(
        state == "installed" for key, state in installed.statuses.items() if key != VOICE_ID
    )
    assert installed.verify_button.isEnabled()
    installed.verify_button.click()
    wait_done(installed, qtbot)
    assert installed.message.text() == M.MODELS_READY
    monkeypatch.setattr(TextDialog, "exec", lambda _: QDialog.DialogCode.Accepted)
    installed.table.selectRow(installed.ids.index(VOICE_ID))
    installed.delete_button.click()
    wait_done(installed, qtbot)
    assert not installed.verify_button.isEnabled()


def test_best_for_wraps_within_two_lines_and_turbo_note_matches_pm(models, qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTextLayout, QTextOption

    dialog = models.create()
    expected = {
        "large-v3-turbo-q8_0": "Everything, if your computer is fast enough",
        "small": "Older or slower computers",
        "medium": "Translating to English",
        "small.en": "English only, on older or slower computers",
    }
    assert dialog.table.wordWrap()
    assert dialog.table.textElideMode() == Qt.TextElideMode.ElideNone
    for key, text in expected.items():
        assert dialog.table.item(dialog.ids.index(key), 1).text() == text
        layout = QTextLayout(text, dialog.table.font())
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WordWrap)
        layout.setTextOption(option)
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(dialog.table.columnWidth(1) - 16)
        layout.endLayout()
        assert layout.lineCount() <= 2
    labels = dialog.table.cellWidget(dialog.ids.index("large-v3-turbo-q8_0"), 0).findChildren(
        QLabel
    )
    assert labels[2].text() == "Fast on newer computers. Slow on older ones."


def test_gui_startup_removes_stale_partial_and_keeps_recent_prefix(models, qtbot):
    import time

    stale = models.paths.models_dir / "abandoned-model.bin.part"
    stale.write_bytes(b"old prefix")
    old = time.time() - 8 * 24 * 60 * 60
    os.utime(stale, (old, old))
    recent = models.file.with_suffix(".bin.part")
    recent.write_bytes(DATA[:65536])
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.initialize()
    qtbot.waitUntil(lambda: view.ready and not view.preparer.isRunning(), timeout=10000)
    assert not stale.exists() and recent.read_bytes() == DATA[:65536]
    dialog = models.create(registry=view.registry)
    dialog.download_button.click()
    wait_done(dialog, qtbot)
    assert models.tls.requests == ["bytes=65536-"]
    assert not recent.exists() and models.file.read_bytes() == DATA


@pytest.mark.skipif(sys.platform != "win32", reason="Windows TerminateProcess and Job Objects")
def test_forced_gui_death_kills_fetch_job_and_recent_partial_resumes(models, qtbot):
    import ctypes
    from ctypes import wintypes

    models.tls.mode = "hold"
    evidence = models.paths.user_dir / "crash-evidence"
    evidence.mkdir(parents=True)
    process = subprocess.Popen(
        [
            sys.executable,
            str(CERTS / "gui_download_crash.py"),
            str(models.tls.port),
            str(CERTS / "localhost.pem"),
            str(models.paths.resources_dir),
            str(models.paths.models_dir),
            str(models.paths.user_dir),
            str(evidence),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    gui_handle = child_handle = None
    part = models.file.with_suffix(".bin.part")
    try:
        qtbot.waitUntil(lambda: (evidence / "gui-ready").exists(), timeout=15000)
        assert models.tls.waiting.wait(5) and not models.tls.release.is_set()
        gui_pid = int((evidence / "gui-pid").read_text(encoding="ascii"))
        child_pid = json.loads((evidence / "fetch-ready.json").read_text())["pid"]
        assert gui_pid != child_pid
        gui_handle = kernel.OpenProcess(0x00100001, False, gui_pid)
        child_handle = kernel.OpenProcess(0x00100001, False, child_pid)
        assert gui_handle and child_handle
        assert kernel.WaitForSingleObject(gui_handle, 0) == 258
        assert kernel.WaitForSingleObject(child_handle, 0) == 258
        assert kernel.TerminateProcess(gui_handle, 77)
        assert kernel.WaitForSingleObject(gui_handle, 5000) == 0
        # Response is still gated, so closed stdout cannot explain child death.
        assert not models.tls.release.is_set()
        assert kernel.WaitForSingleObject(child_handle, 5000) == 0
        process.wait(timeout=10)
        assert not (evidence / "gui-cleanup-ran").exists()
        assert not (evidence / "fetch-cleanup-ran").exists()
        offset = part.stat().st_size
        assert offset == 2 * 65536 and not models.file.exists()
        models.tls.release.set()
        assert models.tls.finished.wait(5)
        assert part.stat().st_size == offset
    finally:
        # Only clean up these test-owned processes if a regression made them survive.
        if gui_handle is None and (evidence / "gui-pid").exists():
            gui_handle = kernel.OpenProcess(
                0x00100001, False, int((evidence / "gui-pid").read_text(encoding="ascii"))
            )
        if child_handle is None and (evidence / "fetch-ready.json").exists():
            child_handle = kernel.OpenProcess(
                0x00100001, False, json.loads((evidence / "fetch-ready.json").read_text())["pid"]
            )
        for handle in (gui_handle, child_handle):
            if handle:
                if kernel.WaitForSingleObject(handle, 0) == 258:
                    kernel.TerminateProcess(handle, 99)
                    kernel.WaitForSingleObject(handle, 5000)
                kernel.CloseHandle(handle)
        models.tls.release.set()
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
    # Restart through real GUI preparation, then resume the retained exact prefix.
    models.tls.mode = "normal"
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.initialize()
    qtbot.waitUntil(lambda: view.ready and not view.preparer.isRunning(), timeout=10000)
    assert part.stat().st_size == offset
    dialog = models.create(registry=view.registry)
    dialog.download_button.click()
    wait_done(dialog, qtbot)
    assert models.tls.requests == [None, f"bytes={offset}-"]
    assert models.file.read_bytes() == DATA and not part.exists()


def test_failed_installer_test_keeps_models_and_shows_empty_options_choice(models, qtbot):
    from dusty.installer_support import clear_failed_selection
    from dusty.queue.storage import load_settings, save_settings

    models.file.write_bytes(DATA)
    file = models.paths.user_dir / "settings.json"
    save_settings(
        file,
        {
            "schema_version": 1,
            "model_id": "tiny",
            "output_dir": str(models.paths.user_dir / "outputs"),
            "vad": False,
        },
    )
    clear_failed_selection(models.paths)
    view = MainWindow(models.paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared(("tiny",), False, load_settings(file)))
    assert models.file.read_bytes() == DATA
    assert view.model_choice.currentData() is None
    assert view.start_hint.text() == M.CHOOSE_MODEL
    assert view.warning.text() == M.INSTALLER_TEST_WARNING
    view.model_choice.setCurrentIndex(view.model_choice.findData("tiny"))
    view._selftest_result(True)
    assert load_settings(file)["installer_test_failed"] is False
