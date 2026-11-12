"""Mac GUI conventions: no hidden greeting, Metal labels, native menus, Finder folders."""

import json
import logging
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QAction, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from dusty.app import messages as M
from dusty.app.workers import Prepared
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="macOS GUI conventions")


@pytest.fixture
def window(qtbot, tmp_path: Path):
    from dusty.app.window import MainWindow

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


def test_windows_wording_is_unchanged_and_metal_wording_is_separate():
    assert M.DEVICES == {"auto": "Automatic", "vulkan": "Graphics card", "cpu": "Processor only"}
    assert M.devices("vulkan") is M.DEVICES and M.device_help("vulkan") is M.DEVICE_HELP
    assert M.THEMES["system"] == "Follow Windows" and M.themes("win32") is M.THEMES
    assert M.EXIT == "Exit"
    assert set(M.devices("metal")) == {"auto", "metal", "cpu"}
    assert M.devices("metal")["metal"] == "Graphics processor (Metal)"
    assert "Metal" in M.device_help("metal")
    assert M.themes("darwin")["system"] == "Follow macOS"


def _release(widget) -> QMouseEvent:
    point = QPointF(widget.rect().center())
    return QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        point,
        widget.mapToGlobal(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


@mac_only
def test_title_clicks_never_open_a_hidden_dialog_or_keep_state(
    window, qtbot, monkeypatch, caplog, tmp_path
):
    from dusty.app import dialogs
    from dusty.app import window as module

    assert not hasattr(dialogs, "GreetingDialog")
    assert not hasattr(window, "_title_clicks") and not hasattr(window, "_title_click_started")
    clock = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    opened = []
    for method in ("exec", "open", "show"):
        monkeypatch.setattr(QDialog, method, lambda self, m=method: opened.append(m) or 0)
    file = window.paths.user_dir / "settings.json"
    before_file = file.read_bytes() if file.exists() else None
    before_settings = dict(window.settings)
    before_state = set(vars(window))

    def visible_dialogs():
        return [
            w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible()
        ]

    assert visible_dialogs() == []
    caplog.set_level(logging.DEBUG)

    def click() -> None:
        qtbot.mouseClick(window.title, Qt.MouseButton.LeftButton)
        # Also deliver the exact event the Windows greeting listened for.
        assert window.eventFilter(window.title, _release(window.title)) is False

    for _ in range(7):  # Seven fast clicks.
        clock[0] += 0.1
        click()
    for _ in range(7):  # Seven slow clicks, past the old four-second window.
        clock[0] += 4.1
        click()
    for _ in range(21):  # Repeated clicks: three times the old trigger count.
        clock[0] += 0.05
        click()
    qtbot.wait(50)
    assert opened == []
    assert visible_dialogs() == []
    assert set(vars(window)) == before_state
    assert window.settings == before_settings
    assert (file.read_bytes() if file.exists() else None) == before_file
    assert not caplog.records


@mac_only
def test_device_choices_and_summary_name_metal(window):
    combo = window.device_choice
    assert [combo.itemData(i) for i in range(combo.count())] == ["auto", "metal", "cpu"]
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Automatic",
        "Graphics processor (Metal)",
        "Processor only",
    ]
    assert window.theme_choice.itemText(0) == "Follow macOS"
    window.vulkan_ok = True  # Platform GPU probe passed.
    window._set_combo(combo, "auto")
    window._rules()
    assert window.choices_summary.text().endswith("Graphics processor (Metal)")
    assert window.batch_options().backend == "auto"
    window._set_combo(combo, "metal")
    assert window.batch_options().backend == "metal"
    window._set_combo(combo, "cpu")
    window._rules()
    assert window.choices_summary.text().endswith("Processor only")
    window._set_combo(combo, "auto")
    window._apply_settings({"backend": "vulkan"})  # A saved GPU choice named "vulkan".
    assert combo.currentData() == "metal"
    window._apply_settings({"backend": "cpu"})
    assert combo.currentData() == "cpu"
    assert window._save_settings()
    saved = json.loads((window.paths.user_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["backend"] == "cpu"
    window._set_combo(combo, "metal")
    assert window._save_settings()
    saved = json.loads((window.paths.user_dir / "settings.json").read_text(encoding="utf-8"))
    assert saved["backend"] == "metal"


@mac_only
def test_native_menu_roles_and_standard_shortcuts(window, monkeypatch):
    from dusty.app.dialogs import NoticesDialog, TextDialog

    assert window.about_action.menuRole() == QAction.MenuRole.AboutRole
    assert window.exit_action.menuRole() == QAction.MenuRole.QuitRole
    assert window.exit_action.text() == M.QUIT
    standard_quit = QKeySequence(QKeySequence.StandardKey.Quit)
    assert standard_quit.isEmpty() or window.exit_action.shortcut() == standard_quit
    assert window.exit_action.shortcut().toString() == "Ctrl+Q"  # Command+Q on Mac.
    add_files, add_folder = window.edit_actions[:2]
    assert add_files.text() == M.ADD_FILES and add_folder.text() == M.ADD_FOLDER
    assert add_files.shortcut().toString() == "Ctrl+O"  # Command+O on Mac.
    assert add_folder.shortcut().toString() == "Ctrl+Shift+O"
    menus = {action.text(): action for action in window.menuBar().actions()}
    assert list(menus) == [M.FILE_MENU, M.TOOLS_MENU, M.HELP_MENU]
    roles = {
        item.text(): item.menuRole()
        for menu in menus.values()
        for item in menu.menu().actions()
        if not item.isSeparator()
    }
    special = {k for k, role in roles.items() if role != QAction.MenuRole.NoRole}
    assert special == {M.ABOUT, M.QUIT}  # No text guessing moves other items.
    assert {M.ADD_FILES, M.ADD_FOLDER, M.HELP_TITLE, M.PRIVACY_TITLE} <= set(roles)
    assert window.help_action.text() == M.HELP_TITLE
    assert window.notices_action.text() == M.THIRD_PARTY_NOTICES
    seen = []

    def inspect(dialog):
        texts = [label.text() for label in dialog.findChildren(QLabel)]
        seen.append((type(dialog), dialog.windowTitle(), texts))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(TextDialog, "exec", inspect)
    monkeypatch.setattr(NoticesDialog, "exec", inspect)
    window.help_action.trigger()
    assert seen[0][0] is TextDialog and seen[0][1] == M.HELP_TITLE
    assert all(topic in seen[0][2] for topic in M.HELP_TOPICS)
    window.notices_action.trigger()
    assert seen[1][0] is NoticesDialog
    help_menu = next(a for a in window.menuBar().actions() if a.text() == M.HELP_MENU)
    # Extension commands come before About; public Dusty has none.
    assert [a.text() for a in help_menu.menu().actions()] == [
        M.HELP_TITLE,
        M.PRIVACY_TITLE,
        *(command.label for command in window.extensions.commands),
        M.ABOUT,
        M.THIRD_PARTY_NOTICES,
    ]


@mac_only
def test_result_folders_open_in_finder_only_for_directories(window, monkeypatch, tmp_path):
    from dusty.app import window as module
    from dusty.core import Job, JobStatus

    urls = []
    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: urls.append(url) or True)
    folder = tmp_path / "Transcripts"
    folder.mkdir()
    document = folder / "lecture.txt"
    document.write_text("public", encoding="utf-8")
    window._open_folder(folder)
    assert [url.toLocalFile() for url in urls] == [str(folder)]
    assert all(url.isLocalFile() for url in urls)
    bundle = tmp_path / "Tool.App"
    bundle.mkdir()
    for refused in (document, tmp_path / "missing", Path("//server/share"), bundle):
        window._open_folder(refused)
    assert len(urls) == 1
    window.model.set_jobs([Job(tmp_path / "lecture.wav", status=JobStatus.DONE)])
    window.model.jobs[0].outputs = [document]
    window._refresh()
    window._table_clicked(window.model.index(0, 5))
    window.open_output()
    assert [url.toLocalFile() for url in urls] == [str(folder)] * 3


@mac_only
@pytest.mark.parametrize("found", [True, False])
def test_mac_gpu_probe_flags_use_the_shared_engine_probe(tmp_path, monkeypatch, found):
    import builtins

    from dusty.__main__ import main
    from dusty.engine import backend

    calls = []
    real_import = builtins.__import__

    def refuse_vulkan(name, *args, **kwargs):
        assert name != "dusty.platform.vulkan_probe"
        return real_import(name, *args, **kwargs)

    def probe(paths, registry, *, model_id):
        calls.append(model_id)
        return found

    monkeypatch.setattr(backend, "probe_gpu", probe)
    monkeypatch.setattr(builtins, "__import__", refuse_vulkan)
    parent, child = tmp_path / "parent.json", tmp_path / "child.json"
    assert main(["--probe-vulkan", "--out", str(parent)]) == (0 if found else 1)
    assert main(["--probe-vulkan-child", "--model", "small", "--out", str(child)]) == 0
    assert calls == ["tiny", "small"]
    for output in (parent, child):
        assert json.loads(output.read_text(encoding="utf-8")) == {"real_gpu_found": found}
    assert main(["--probe-vulkan"]) == 2


@mac_only
def test_entry_point_flags_and_mac_application_identity(qtbot, tmp_path):
    from dusty.__main__ import _prepare_mac_application, main

    with pytest.raises(SystemExit) as exit_info:
        main(["--backend", "vulkan"])
    assert exit_info.value.code == 2
    with pytest.raises(SystemExit) as exit_info:
        main(["--backend", "metal", "--version"])
    assert exit_info.value.code == 0
    app = QApplication.instance()
    original = (app.applicationName(), app.organizationName(), app.applicationDisplayName())
    try:
        _prepare_mac_application(app)
        assert app.applicationName() == M.APP_NAME
        assert app.organizationName() == M.APP_NAME
        assert not app.windowIcon().isNull()
    finally:
        app.setApplicationName(original[0])
        app.setOrganizationName(original[1])
        app.setApplicationDisplayName(original[2])


@mac_only
def test_notices_come_from_the_app_bundle_resources(window, tmp_path, monkeypatch):
    from dataclasses import replace

    from dusty.app.dialogs import NoticesDialog

    contents = tmp_path / "Dusty.app/Contents"
    resources = contents / "Resources"
    resources.mkdir(parents=True)
    (resources / "THIRD_PARTY_NOTICES.md").write_text("Bundled notices\n", encoding="utf-8")
    window.paths = replace(window.paths, resources_dir=resources)
    seen = []
    monkeypatch.setattr(
        NoticesDialog, "exec", lambda dialog: seen.append(dialog.text.toPlainText()) or 1
    )
    window.open_notices()
    assert seen == ["Bundled notices\n"]
    source = tmp_path / "source"
    (source / "resources").mkdir(parents=True)
    (source / "THIRD_PARTY_NOTICES.md").write_text("Source notices\n", encoding="utf-8")
    window.paths = replace(window.paths, resources_dir=source / "resources")
    window.open_notices()
    assert seen[-1] == "Source notices\n"


@mac_only
def test_mac_theme_uses_the_system_font(qapp):
    from PySide6.QtGui import QFontDatabase

    from dusty.app.theme import apply_theme

    apply_theme(qapp, "light")
    system = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    assert qapp.font().family() == system.family()
    assert qapp.font().family() != "Segoe UI"


@mac_only
def test_data_folder_is_created_private_and_tightened_before_the_window(tmp_path):
    import os
    import stat

    from dusty.__main__ import _private_user_dir
    from dusty.platform.mac_instance import GuiInstance

    fresh = tmp_path / "fresh/Dusty"
    _private_user_dir(fresh)
    assert stat.S_IMODE(os.lstat(fresh).st_mode) == 0o700
    earlier = tmp_path / "earlier/Dusty"
    earlier.mkdir(parents=True, mode=0o755)
    os.chmod(earlier, 0o755)
    (earlier / "settings.json").write_text("{}", encoding="utf-8")
    with pytest.raises(OSError):
        GuiInstance(earlier)  # The lease refuses a folder others can read.
    _private_user_dir(earlier)
    assert stat.S_IMODE(os.lstat(earlier).st_mode) == 0o700
    assert (earlier / "settings.json").read_text(encoding="utf-8") == "{}"
    instance = GuiInstance(earlier)
    try:
        assert instance.owner
    finally:
        instance.close()
    target = tmp_path / "target"
    target.mkdir(mode=0o755)
    os.chmod(target, 0o755)
    link = tmp_path / "link/Dusty"
    link.parent.mkdir()
    link.symlink_to(target, target_is_directory=True)
    _private_user_dir(link)
    assert stat.S_IMODE(os.lstat(target).st_mode) == 0o755  # Links are never followed.


WINDOWS_WORDING = {
    "MODEL_DETAILS turbo": (
        M.MODEL_DETAILS["large-v3-turbo-q8_0"],
        "Recommended with a graphics card",
    ),
    "MODEL_DETAILS tiny": (M.MODEL_DETAILS["tiny"], "Lower accuracy"),
    "MODEL_NOTE turbo": (
        M.MODEL_NOTE["large-v3-turbo-q8_0"],
        "Fast on newer computers. Slow on older ones.",
    ),
    "MODEL_NOTE tiny": (M.MODEL_NOTE["tiny"], "Lowest accuracy. Good for quick drafts."),
    "GPU_FALLBACK": (M.GPU_FALLBACK, "Completed on processor (graphics card failed)"),
    "GPU_NOTICE": (
        M.GPU_NOTICE,
        "The graphics card could not finish a file. Dusty completed it with the processor instead.",
    ),
    "NOTICES_UNAVAILABLE": (
        M.NOTICES_UNAVAILABLE,
        "The bundled notices could not be opened. Reinstall Dusty to restore them.",
    ),
}


def test_windows_strings_stay_byte_identical_and_accessors_return_them():
    from dusty.core import FailureCode

    for name, (actual, expected) in WINDOWS_WORDING.items():
        assert actual == expected, name
    gpu = M.FAILURE_MESSAGES[FailureCode.GPU_ERROR]
    assert (gpu.message, gpu.action) == (
        "The graphics card could not process this file.",
        "Retry with Processing device set to CPU.",
    )
    crash = M.FAILURE_MESSAGES[FailureCode.ENGINE_CRASH]
    assert crash.action == (
        "Click Retry. If it keeps happening, switch Processing device to CPU in Advanced settings."
    )
    assert M.failure_messages("win32") is M.FAILURE_MESSAGES
    assert M.model_details("win32") is M.MODEL_DETAILS
    assert M.model_note("win32") is M.MODEL_NOTE
    assert M.gpu_fallback("win32") is M.GPU_FALLBACK
    assert M.gpu_notice("win32") is M.GPU_NOTICE
    assert M.notices_unavailable("win32") is M.NOTICES_UNAVAILABLE


def _mac_visible_wording() -> list[str]:
    texts = [
        M.gpu_fallback("darwin"),
        M.gpu_notice("darwin"),
        M.notices_unavailable("darwin"),
        M.device_help("metal"),
        M.DATA_FOLDER_UNSAFE,
        M.INSTANCE_UNAVAILABLE,
        *M.devices("metal").values(),
        *M.themes("darwin").values(),
        *M.model_details("darwin").values(),
        *M.model_note("darwin").values(),
        *M.HELP_TOPICS,
    ]
    for failure in M.failure_messages("darwin").values():
        texts += [failure.message, failure.action]
    return texts


def test_mac_wording_never_names_windows_hardware_or_installer():
    from dusty.core import FailureCode

    forbidden = ("graphics card", "vulkan", "installer", "setup", " cpu", "explorer")
    for text in _mac_visible_wording():
        lowered = text.casefold()
        assert not any(word in lowered for word in forbidden), text
        assert "Windows" not in text and "Start menu" not in text, text  # "windows" is fine.
        assert "—" not in text and "–" not in text
    mac = M.failure_messages("darwin")
    assert set(mac) == set(FailureCode)
    # Only the graphics wording differs; every other explanation is shared.
    changed = {code for code in FailureCode if mac[code] != M.FAILURE_MESSAGES[code]}
    assert changed == {FailureCode.GPU_ERROR, FailureCode.ENGINE_CRASH}
    assert "Metal" in mac[FailureCode.GPU_ERROR].message
    assert M.devices("metal")["cpu"] in mac[FailureCode.GPU_ERROR].action
    assert set(M.model_details("darwin")) == set(M.MODEL_DETAILS)
    assert set(M.model_note("darwin")) == set(M.MODEL_NOTE)
    assert "Skip long silences" in M.model_details("darwin")["tiny"]
    assert "silence" in M.model_note("darwin")["tiny"]


def test_recommendation_rule_reads_as_platform_gpu_and_keeps_windows_choices():
    from dusty.models import recommend_model

    for working, expected in ((True, "large-v3-turbo-q8_0"), (False, "small")):
        assert recommend_model(gpu_ok=working, task="transcribe") == expected
        assert recommend_model(vulkan_ok=working, task="transcribe") == expected
        assert recommend_model(gpu_ok=working, task="translate") == "medium"
        assert recommend_model(vulkan_ok=working, task="translate") == "medium"
    with pytest.raises(TypeError):
        recommend_model(task="transcribe")
    with pytest.raises(TypeError):
        recommend_model(gpu_ok=True, vulkan_ok=True, task="transcribe")


@mac_only
@pytest.mark.parametrize(
    ("metal", "device", "task", "expected"),
    [
        (True, "auto", "transcribe", "large-v3-turbo-q8_0"),
        (True, "metal", "transcribe", "large-v3-turbo-q8_0"),
        (True, "cpu", "transcribe", "small"),
        (False, "auto", "transcribe", "small"),
        (True, "auto", "translate", "medium"),
        (False, "auto", "translate", "medium"),
    ],
)
def test_mac_recommendation_follows_metal_and_device_choice(window, metal, device, task, expected):
    window.vulkan_ok = metal  # Platform GPU probe result (Metal on Mac).
    window._set_combo(window.device_choice, device)
    window._set_combo(window.task_choice, task)
    window._rules()
    assert window._recommendation == expected
    marked = [
        window.model_choice.itemData(i)
        for i in range(window.model_choice.count())
        if window.model_choice.itemText(i).endswith(", recommended")
    ]
    assert marked == [expected]


@mac_only
def test_mac_option_details_and_queue_status_use_mac_wording(window):
    from dusty.core import FailureCode, Job, JobStatus

    window._set_combo(window.model_choice, "large-v3-turbo-q8_0")
    window._rules()
    assert window.model_details.text() == M.MODEL_DETAILS_MAC["large-v3-turbo-q8_0"]
    window._set_combo(window.model_choice, "tiny")
    window._rules()
    assert window.model_details.text() == M.MODEL_DETAILS_MAC["tiny"]
    done = Job(Path("lecture.wav"), status=JobStatus.DONE)
    done.gpu_fallback = True
    failed = Job(Path("other.wav"), status=JobStatus.FAILED, failure=FailureCode.GPU_ERROR)
    window.model.set_jobs([done, failed])
    assert window.model.data(window.model.index(0, 2)) == M.GPU_FALLBACK_MAC
    tip = window.model.data(window.model.index(1, 0), Qt.ItemDataRole.ToolTipRole)
    gpu = M.FAILURE_MESSAGES_MAC[FailureCode.GPU_ERROR]
    assert tip == gpu.message + " " + gpu.action


@mac_only
def test_mac_error_summary_and_notices_dialogs_use_mac_wording(window, qtbot, tmp_path):
    from dusty.app.dialogs import ErrorDialog, NoticesDialog, SummaryDialog
    from dusty.core import FailureCode, Job, JobStatus

    error = ErrorDialog(FailureCode.GPU_ERROR, filename="one.wav", parent=window)
    qtbot.addWidget(error)
    mac = M.FAILURE_MESSAGES_MAC[FailureCode.GPU_ERROR].message
    assert [label.text() for label in error.findChildren(QLabel)] == [
        M.NAMED_FAILURE.format(name="one.wav", reason=mac)
    ]
    failed = Job(Path("two.wav"), status=JobStatus.FAILED, failure=FailureCode.GPU_ERROR)
    summary = SummaryDialog([failed], window)
    qtbot.addWidget(summary)
    assert M.NAMED_FAILURE.format(name="two.wav", reason=mac) in [
        label.text() for label in summary.findChildren(QLabel)
    ]
    notices = NoticesDialog(tmp_path / "missing.md", window)
    qtbot.addWidget(notices)
    assert notices.text.toPlainText() == M.NOTICES_UNAVAILABLE_MAC


@mac_only
def test_main_controls_have_accessible_names(window):
    from PySide6.QtGui import QAccessible
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QPlainTextEdit,
        QPushButton,
        QSpinBox,
        QToolButton,
        QWidget,
    )

    from dusty.core import Job

    window.model.set_jobs([Job(Path("lecture.wav"))])
    window._refresh()
    assert window.table.accessibleName() == M.QUEUE_NAME
    assert window.overall.accessibleName() == M.OVERALL_PROGRESS
    unnamed = []
    for host in (window, window.options_dialog):
        for widget in host.findChildren(QWidget):
            controls = QPushButton | QCheckBox | QToolButton | QComboBox | QSpinBox | QPlainTextEdit
            if widget.objectName().startswith("qt_"):
                continue  # Qt's own internal parts, such as scroll area viewports.
            if not isinstance(widget, controls) and widget not in (window.table, window.overall):
                continue
            interface = QAccessible.queryAccessibleInterface(widget)
            if not interface.text(QAccessible.Text.Name).strip():
                unnamed.append(type(widget).__name__ + ":" + widget.objectName())
    assert unnamed == []


@mac_only
def test_main_window_tab_order_reaches_queue_and_buttons(window, qtbot):
    from dusty.core import Job

    window.model.set_jobs([Job(Path("lecture.wav"))])
    window._refresh()
    window.add_files_button.setFocus()
    qtbot.waitUntil(window.add_files_button.hasFocus)
    order = [window.add_files_button]
    for _ in range(12):
        window.focusNextChild()
        current = QApplication.focusWidget()
        if current is window.add_files_button:
            break
        order.append(current)
    assert order == [
        window.add_files_button,
        window.add_folder_button,
        *window.queue_buttons,
        window.table,
        window.output_button,
        window.formats["txt"],
        window.formats["docx"],
        window.options_button,
        window.start_button,
    ]


@mac_only
def test_command_shortcuts_trigger_their_actions(window, qtbot, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    from dusty.app.dialogs import TextDialog

    opened = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames", lambda *a, **k: opened.append("files") or ([], "")
    )
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **k: opened.append("folder") or ""
    )
    monkeypatch.setattr(TextDialog, "exec", lambda dialog: opened.append(dialog.windowTitle()))
    window.activateWindow()
    window.output_button.setFocus()
    qtbot.waitUntil(window.output_button.hasFocus)
    control = Qt.KeyboardModifier.ControlModifier  # Command on Mac.
    qtbot.keyClick(window, Qt.Key.Key_O, control)
    qtbot.keyClick(window, Qt.Key.Key_O, control | Qt.KeyboardModifier.ShiftModifier)
    assert opened == ["files", "folder"]
    window.help_action.trigger()  # Command+? needs a layout-specific key; the action is bound.
    assert opened[-1] == M.HELP_TITLE
    assert window.help_action.shortcut() == QKeySequence(QKeySequence.StandardKey.HelpContents)
    closed = []
    monkeypatch.setattr(window, "close", lambda: closed.append(True) or True)
    window.exit_action.triggered.disconnect()
    window.exit_action.triggered.connect(window.close)
    qtbot.keyClick(window, Qt.Key.Key_Q, control)
    assert closed == [True]


@mac_only
def test_model_manager_table_and_rows_are_named_for_voiceover(qtbot, tmp_path):
    from dusty.app.model_manager import ModelManager
    from dusty.models import ModelRegistry, load_manifest

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, tmp_path / "models", dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    dialog = ModelManager(
        registry, paths, recommended="large-v3-turbo-q8_0", command=["/bin/false"]
    )
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitUntil(lambda: bool(dialog.workers) and not dialog.busy, timeout=10000)
    assert dialog.table.accessibleName() == M.MODEL_MANAGER
    for row in range(len(dialog.ids)):
        spoken = dialog.table.item(row, 0).data(Qt.ItemDataRole.AccessibleTextRole)
        labels = [label.text() for label in dialog.table.cellWidget(row, 0).findChildren(QLabel)]
        assert spoken == ". ".join(labels)
    tiny = dialog.table.item(dialog.ids.index("tiny"), 0)
    assert M.MODEL_NOTE_MAC["tiny"] in tiny.data(Qt.ItemDataRole.AccessibleTextRole)


@mac_only
def test_first_download_runs_the_metal_probe_once_and_updates_the_choice(
    qtbot, tmp_path, monkeypatch
):
    from dusty.app.window import MainWindow
    from dusty.engine import backend
    from dusty.queue.storage import load_settings, save_settings

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    view = MainWindow(paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), False, {"schema_version": 1}, vad_installed=False))
    view.output_dir = tmp_path / "out"
    view.show()
    view.interactive = True  # Like a Processing device change, only a real window probes.
    # Nothing could be probed without a model; Apple silicon presumes Metal for
    # advice only (D-MAC-022), and the backend still waits for the real probe.
    assert view._recommendation == "large-v3-turbo-q8_0" and not view.vulkan_ok
    probes = []

    def probe(paths, registry, *, model_id, refresh=False):
        probes.append((model_id, refresh, view.ready, view.start_button.isEnabled()))
        settings = load_settings(paths.user_dir / "settings.json")
        settings["backend_probe"] = {"engine": "e", "driver": "d", "ok": True}
        save_settings(paths.user_dir / "settings.json", settings)
        return True

    monkeypatch.setattr(backend, "probe_vulkan", probe)
    statuses = dict.fromkeys(view.registry.manifest.models, "not_installed")
    statuses.update({"tiny": "installed", "silero-vad": "installed"})
    view._models_changed(statuses)
    qtbot.waitUntil(lambda: view.ready, timeout=10000)
    assert probes == [("tiny", False, False, False)]  # Start waited for the probe.
    assert view.vulkan_ok and view._recommendation == "large-v3-turbo-q8_0"
    assert view.model_choice.currentData() == "tiny"  # The downloaded choice is kept.
    assert view.choices_summary.text().split(", ")[-1] == "Graphics processor (Metal)"
    assert view.settings["backend_probe"]["ok"] is True
    assert view._save_settings()
    saved = load_settings(paths.user_dir / "settings.json")
    assert saved["backend_probe"]["ok"] is True  # A later save keeps the probe result.
    statuses["small"] = "installed"
    view._models_changed(statuses)  # The GPU already works: no second probe.
    statuses.update(tiny="not_installed", small="not_installed")
    view._models_changed(statuses)  # Deleting never probes.
    qtbot.wait(50)
    assert len(probes) == 1 and view.ready


@mac_only
def test_failed_first_probe_keeps_processor_and_small(qtbot, tmp_path, monkeypatch):
    from dusty.app.window import MainWindow
    from dusty.engine import backend

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    view = MainWindow(paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(Prepared((), False, {"schema_version": 1}, vad_installed=True))
    view.show()
    view.interactive = True
    monkeypatch.setattr(backend, "probe_vulkan", lambda *a, **k: False)
    statuses = dict.fromkeys(view.registry.manifest.models, "not_installed")
    statuses.update({"small": "installed", "silero-vad": "installed"})
    view._models_changed(statuses)
    qtbot.waitUntil(lambda: view.ready, timeout=10000)
    assert not view.vulkan_ok and view._recommendation == "small"
    assert view.choices_summary.text().split(", ")[-1] == "Processor only"
