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
from dusty.app.model_manager import VOICE_ID, DownloadDialog, ModelManager, ModelWorker
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
        qtbot.waitUntil(lambda: dialog.message.text() == M.MODELS_READY and not dialog.busy)
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
    assert M.DOWNLOAD_CONFIRM.format(mb=2 * len(DATA) / 1_000_000) in [
        label.text() for label in confirm.findChildren(QLabel)
    ]
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
    assert view.model_choice.currentData() == "small"
    dialog.table.selectRow(dialog.ids.index(VOICE_ID))
    assert not dialog.delete_button.isEnabled()
    assert dialog.delete_button.toolTip() == M.DELETE_VOICE


def test_cancel_keeps_part_and_new_dialog_resumes(models, qtbot):
    models.tls.mode = "slow"
    dialog = models.create()
    dialog.download()
    part = models.file.with_suffix(".bin.part")
    qtbot.waitUntil(lambda: part.exists() and part.stat().st_size > 0, timeout=10000)
    dialog.cancel()
    wait_done(dialog, qtbot)
    offset = part.stat().st_size
    assert 0 < offset < len(DATA) and not models.file.exists()
    assert dialog.message.text() == M.DOWNLOAD_PAUSED
    dialog.close()
    models.tls.mode = "normal"
    fresh_registry = ModelRegistry(models.registry.manifest, models.paths.models_dir)
    resumed = models.create(registry=fresh_registry)
    resumed.download()
    wait_done(resumed, qtbot)
    assert resumed.statuses["tiny"] == "installed"
    assert f"bytes={offset}-" in models.tls.requests
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
    assert not dialog.delete_button.isEnabled()
    assert dialog.delete_button.toolTip() == M.DELETE_SELECTED
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
    assert not dialog.delete_button.isEnabled()
    assert dialog.delete_button.toolTip() == M.DELETE_LAST
    original = small.stat()
    small.write_bytes(b"x" * len(DATA))
    os.utime(small, ns=(original.st_atime_ns, original.st_mtime_ns))
    dialog.verify_all()
    wait_done(dialog, qtbot)
    assert dialog.statuses["small"] == "damaged"


def test_no_download_without_consent_and_worker_enforces_delete_policy(models, qtbot, monkeypatch):
    models.file.write_bytes(DATA)
    dialog = models.create()
    worker = ModelWorker(
        models.registry, models.paths, action="delete", ids=("tiny",), selected="tiny"
    )
    worker.run()
    assert models.file.exists() and worker.failure == "DELETE"
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
    assert M.MODEL_NAMES["small"] in view.warning.text()
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


def test_closing_manager_cancels_child_and_preserves_resumable_part(models, qtbot):
    models.tls.mode = "slow"
    dialog = models.create()
    dialog.download()
    part = models.file.with_suffix(".bin.part")
    qtbot.waitUntil(lambda: part.exists() and part.stat().st_size > 0, timeout=10000)
    dialog.done(QDialog.DialogCode.Rejected)
    qtbot.waitUntil(lambda: not dialog.busy and not dialog.isVisible(), timeout=15000)
    assert part.exists() and not models.file.exists()
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
        if dialog is None:
            return
        if not started and not dialog.busy and dialog.message.text() == M.MODELS_READY:
            started.append(True)
            QTimer.singleShot(0, dialog.download_button.click)
        elif part.exists() and part.stat().st_size > 0 and not view.closing:
            view.close()

    timer = QTimer()
    timer.timeout.connect(drive)
    timer.start(20)
    QTimer.singleShot(0, lambda: view.open_model_manager(focus_id="tiny"))
    qtbot.waitUntil(lambda: bool(started) and not view.isVisible(), timeout=15000)
    timer.stop()
    assert part.exists() and not models.file.exists()
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
