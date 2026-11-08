"""Mac Remove Dusty data (D-MAC-025): the rules, the menu, the dialog and the exit step."""

import json
import logging
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QLabel

from dusty.app import messages as M
from dusty.mac_removal import FINDER_FILE, INSTANCE_FOLDER, finished, remove_data, stop_logging
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="Mac removal flow")
mac_owner_checks = pytest.mark.skipif(
    sys.platform != "darwin", reason="Mac removal checks file owners with os.getuid"
)


def paths_for(root: Path) -> RuntimePaths:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    return RuntimePaths(dev.bin_dir, root / "models", dev.resources_dir, root)


def data_folder(tmp_path: Path, **settings) -> Path:
    """A data folder as a Mac Dusty leaves it after real use."""
    root = tmp_path / "Library/Application Support/Dusty"
    for folder in ("logs", "state", "models", "work", INSTANCE_FOLDER):
        (root / folder).mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    os.chmod(root / INSTANCE_FOLDER, 0o700)
    values = {"schema_version": 1, "output_dir": str(tmp_path / "transcripts"), **settings}
    (root / "settings.json").write_text(json.dumps(values), encoding="utf-8")
    (root / "state/queue.json").write_text(
        json.dumps({"schema_version": 1, "jobs": []}), encoding="utf-8"
    )
    (root / "logs/dusty.log").write_text("started\n", encoding="utf-8")
    (root / "logs/dusty.log.1").write_text("older\n", encoding="utf-8")
    (root / "models/ggml-tiny.bin").write_bytes(b"model")
    (root / "models/ggml-small.bin.part").write_bytes(b"partial")
    (root / "models/ggml-silero-vad.bin").write_bytes(b"vad")
    for name in ("owner", "activation"):
        path = root / INSTANCE_FOLDER / name
        path.write_bytes(b"0" if name == "activation" else b"")
        path.chmod(0o600)
    (root / FINDER_FILE).write_bytes(b"finder")
    (root / "logs" / FINDER_FILE).write_bytes(b"finder")
    return root


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """Recordings and transcripts outside the data folder are never touched."""
    folder = tmp_path / "transcripts"
    folder.mkdir()
    (folder / "talk.txt").write_text("transcript", encoding="utf-8")
    (folder / "talk.m4a").write_bytes(b"recording")
    return folder


def untouched(folder: Path) -> None:
    assert (folder / "talk.txt").read_text(encoding="utf-8") == "transcript"
    assert (folder / "talk.m4a").read_bytes() == b"recording"


@mac_owner_checks
def test_removes_everything_including_models(tmp_path, outside):
    root = data_folder(tmp_path)
    assert remove_data(paths_for(root), remove_models=True)
    assert not root.exists()
    assert root.parent.is_dir()  # Application Support itself stays.
    untouched(outside)


@mac_owner_checks
def test_keeping_models_leaves_only_the_models_folder(tmp_path, outside):
    root = data_folder(tmp_path)
    assert remove_data(paths_for(root), remove_models=False)
    assert [p.name for p in root.iterdir()] == ["models"]
    assert sorted(p.name for p in (root / "models").iterdir()) == [
        "ggml-silero-vad.bin",
        "ggml-small.bin.part",
        "ggml-tiny.bin",
    ]
    assert finished(root, remove_models=False)
    untouched(outside)


def test_missing_data_folder_is_already_removed(tmp_path):
    assert remove_data(paths_for(tmp_path / "none/Dusty"), remove_models=True)


@mac_owner_checks
def test_unknown_files_are_kept_and_reported(tmp_path):
    root = data_folder(tmp_path)
    (root / "notes.txt").write_text("mine", encoding="utf-8")
    (root / "models/my-model.bin").write_bytes(b"own")
    assert not remove_data(paths_for(root), remove_models=True)
    assert (root / "notes.txt").read_text(encoding="utf-8") == "mine"
    assert (root / "models/my-model.bin").read_bytes() == b"own"
    # Everything Dusty recognizes is gone.
    assert not (root / "settings.json").exists() and not (root / "logs").exists()
    assert not (root / "models/ggml-tiny.bin").exists()
    assert not (root / INSTANCE_FOLDER).exists()


@mac_owner_checks
def test_an_output_folder_inside_the_data_folder_stops_all_removal(tmp_path):
    inside = tmp_path / "Library/Application Support/Dusty/transcripts"
    root = data_folder(tmp_path, output_dir=str(inside))
    inside.mkdir()
    (inside / "talk.txt").write_text("transcript", encoding="utf-8")
    assert not remove_data(paths_for(root), remove_models=True)
    assert (inside / "talk.txt").read_text(encoding="utf-8") == "transcript"
    assert (root / "settings.json").is_file() and (root / "models/ggml-tiny.bin").is_file()


@mac_owner_checks
def test_unknown_settings_schema_removes_nothing(tmp_path):
    root = data_folder(tmp_path, schema_version=99)
    assert not remove_data(paths_for(root), remove_models=True)
    assert (root / "settings.json").is_file() and (root / "logs/dusty.log").is_file()


def test_a_linked_data_folder_is_refused(tmp_path):
    real = data_folder(tmp_path / "real")
    link = tmp_path / "Dusty"
    link.symlink_to(real)
    assert not remove_data(paths_for(link), remove_models=True)
    assert (real / "settings.json").is_file() and (real / "models/ggml-tiny.bin").is_file()


@mac_owner_checks
def test_linked_instance_and_finder_files_are_kept(tmp_path):
    root = data_folder(tmp_path)
    target = tmp_path / "elsewhere.txt"
    target.write_text("keep", encoding="utf-8")
    (root / INSTANCE_FOLDER / "owner").unlink()
    (root / INSTANCE_FOLDER / "owner").symlink_to(target)
    (root / "logs" / FINDER_FILE).unlink()
    (root / "logs" / FINDER_FILE).symlink_to(target)
    assert not remove_data(paths_for(root), remove_models=True)
    assert target.read_text(encoding="utf-8") == "keep"
    assert (root / INSTANCE_FOLDER / "owner").is_symlink()
    assert (root / "logs" / FINDER_FILE).is_symlink()


@mac_owner_checks
def test_logging_stops_before_the_log_is_removed(tmp_path):
    from dusty.privacy.logging import configure_logger

    root = data_folder(tmp_path)
    logger = logging.getLogger("dusty")
    saved = list(logger.handlers)
    for handler in saved:
        logger.removeHandler(handler)
    try:
        configure_logger(root)
        logger.info("before removal")
        assert remove_data(paths_for(root), remove_models=True)
        logger.info("after removal")
        assert not root.exists()
        assert all(isinstance(h, logging.NullHandler) for h in logger.handlers)
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        for handler in saved:
            logger.addHandler(handler)


def test_stop_logging_is_safe_twice():
    logger = logging.getLogger("dusty")
    saved = list(logger.handlers)
    try:
        stop_logging()
        stop_logging()
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        for handler in saved:
            logger.addHandler(handler)


@mac_only
def test_removal_while_holding_the_instance_lease(tmp_path):
    from dusty.platform.mac_instance import GuiInstance

    root = data_folder(tmp_path)
    instance = GuiInstance(root)
    try:
        assert instance.owner
        second = GuiInstance(root)  # A launch before removal only asks to come forward.
        assert not second.owner
        second.close()
        assert remove_data(paths_for(root), remove_models=True)
        assert not root.exists()
    finally:
        instance.close()


@pytest.fixture
def window(qtbot, tmp_path: Path):
    from dusty.app.window import MainWindow
    from dusty.app.workers import Prepared

    view = MainWindow(paths_for(data_folder(tmp_path)), interactive=False)
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


@mac_only
def test_menu_item_is_last_in_tools_and_follows_busy_state(window):
    from PySide6.QtGui import QAction

    menu_action = next(a for a in window.menuBar().actions() if a.text() == M.TOOLS_MENU)
    tools = menu_action.menu()
    items = [a for a in tools.actions() if not a.isSeparator()]
    assert items[-1] is window.remove_data_action
    assert window.remove_data_action.text() == M.REMOVE_DATA
    assert window.remove_data_action.menuRole() == QAction.MenuRole.NoRole
    assert window.remove_data_action.isEnabled()
    window.running = True
    window._refresh()
    assert not window.remove_data_action.isEnabled()
    window.running = False
    window._refresh()
    assert window.remove_data_action.isEnabled()


@mac_only
def test_dialog_defaults_to_cancel_and_offers_model_removal(qtbot):
    from dusty.app.dialogs import RemoveDataDialog

    dialog = RemoveDataDialog("1.2 MB")
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == M.REMOVE_DATA_TITLE
    assert dialog.remove_models.isChecked()
    assert dialog.remove_models.text() == M.REMOVE_DATA_MODELS.format(size="1.2 MB")
    assert dialog.cancel.isDefault() and not dialog.confirm.isDefault()
    assert dialog.confirm.text() == M.REMOVE_DATA_CONFIRM
    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert M.REMOVE_DATA_HELP in texts and M.REMOVE_DATA_MODELS_HELP in texts


@mac_only
def test_cancel_keeps_dusty_open_and_requests_nothing(window, monkeypatch):
    from dusty.app.dialogs import RemoveDataDialog

    monkeypatch.setattr(RemoveDataDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    window.remove_data_action.trigger()
    assert window.removal_request is None and window.isVisible()
    assert (window.paths.user_dir / "settings.json").is_file()


@mac_only
@pytest.mark.parametrize("remove_models", [True, False])
def test_confirm_closes_the_window_and_records_the_choice(window, monkeypatch, remove_models):
    from dusty.app.dialogs import RemoveDataDialog

    sizes = []

    def confirm(self):
        sizes.append(self.remove_models.text())
        self.remove_models.setChecked(remove_models)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(RemoveDataDialog, "exec", confirm)
    window.remove_data_action.trigger()
    assert window.removal_request is remove_models and not window.isVisible()
    # Only the models inside the data folder are counted (5 + 7 + 3 bytes).
    assert sizes == [M.REMOVE_DATA_MODELS.format(size=M.format_size(15))]
    # The window removes nothing itself; the data waits for the exit step.
    assert (window.paths.user_dir / "models/ggml-tiny.bin").is_file()


@mac_only
def test_refused_close_clears_the_request(window, monkeypatch):
    from dusty.app.dialogs import CloseDialog, RemoveDataDialog

    monkeypatch.setattr(RemoveDataDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(CloseDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    window.running = True  # The menu item is disabled then; call the slot directly.
    window.remove_data()
    assert window.removal_request is None and window.isVisible()
    window.running = False


@mac_only
@pytest.mark.parametrize("keep_unknown", [False, True])
def test_exit_step_removes_and_reports(tmp_path, monkeypatch, qapp, keep_unknown):
    from dusty.__main__ import _finish_mac_removal
    from dusty.app.dialogs import TextDialog

    root = data_folder(tmp_path)
    monkeypatch.setenv("LOCALAPPDATA", str(root.parent))
    if keep_unknown:
        (root / "notes.txt").write_text("mine", encoding="utf-8")
    shown = []

    def record(self):
        shown.append((self.windowTitle(), [label.text() for label in self.findChildren(QLabel)]))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(TextDialog, "exec", record)
    assert _finish_mac_removal(remove_models=False) is not keep_unknown
    if keep_unknown:
        assert shown == [(M.REMOVE_DATA_KEPT_TITLE, [M.REMOVE_DATA_KEPT, M.REMOVE_DATA_DONE])]
        assert (root / "notes.txt").is_file()
    else:
        assert shown == [
            (M.REMOVE_DATA_DONE_TITLE, [M.REMOVE_DATA_DONE, M.REMOVE_DATA_MODELS_KEPT])
        ]
        assert [p.name for p in root.iterdir()] == ["models"]


def test_removal_wording_is_plain_and_mac_only():
    texts = [
        M.REMOVE_DATA,
        M.REMOVE_DATA_TITLE,
        M.REMOVE_DATA_HELP,
        M.REMOVE_DATA_MODELS,
        M.REMOVE_DATA_MODELS_HELP,
        M.REMOVE_DATA_CONFIRM,
        M.REMOVE_DATA_DONE_TITLE,
        M.REMOVE_DATA_DONE,
        M.REMOVE_DATA_MODELS_KEPT,
        M.REMOVE_DATA_KEPT_TITLE,
        M.REMOVE_DATA_KEPT,
    ]
    for text in texts:
        lowered = text.casefold()
        assert not any(w in lowered for w in ("installer", "setup", "explorer", "windows")), text
        assert chr(0x2014) not in text and chr(0x2013) not in text
        assert "/Users/" not in text


@mac_owner_checks
def test_packaged_app_paths_allow_removal_and_keep_the_app(tmp_path):
    """Frozen Mac paths name the app bundle as install_dir; the bundle is never touched."""
    from dataclasses import replace

    root = data_folder(tmp_path)
    app = tmp_path / "Applications/Dusty.app"
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/MacOS/Dusty").write_bytes(b"app")
    assert remove_data(replace(paths_for(root), install_dir=app), remove_models=True)
    assert not root.exists()
    assert (app / "Contents/MacOS/Dusty").read_bytes() == b"app"


@mac_owner_checks
def test_output_folder_inside_the_app_bundle_stops_removal(tmp_path):
    from dataclasses import replace

    app = tmp_path / "Applications/Dusty.app"
    (app / "Contents").mkdir(parents=True)
    root = data_folder(tmp_path, output_dir=str(app / "Contents/out"))
    assert not remove_data(replace(paths_for(root), install_dir=app), remove_models=True)
    assert (root / "settings.json").is_file()
