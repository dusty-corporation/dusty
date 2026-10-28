"""Dusty's simple-mode desktop window, bound to the shared offline workers."""

import os
import time
from dataclasses import replace
from pathlib import Path
from typing import cast
from uuid import UUID

from PySide6.QtCore import QByteArray, QEvent, Qt, QThread, QTimer, QUrl, Slot
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QKeyEvent,
    QResizeEvent,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dusty import __version__
from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.core.types import Backend, CollisionPolicy, OutputFormat, Task
from dusty.models import ModelRegistry, can_translate, load_manifest, recommend_model
from dusty.platform.cpu_topology import default_threads
from dusty.privacy.logging import configure_logger
from dusty.privacy.sync import is_synced
from dusty.queue import clear_history
from dusty.queue.scanning import ScanResult
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths, resolve_paths

from . import messages as M
from .dialogs import (
    AboutDialog,
    ChoiceDelegate,
    CloseDialog,
    CollisionDialog,
    ErrorDialog,
    FolderDialog,
    GreetingDialog,
    NoticesDialog,
    ResumeDialog,
    SummaryDialog,
    SyncDialog,
    TextDialog,
    WelcomeDialog,
)
from .model_manager import VOICE_ID, ModelManager
from .presentation import TERMINAL, counts, eta_seconds, overall_progress
from .table import ProgressDelegate, QueueModel
from .theme import application_icon, apply_theme
from .workers import BatchWorker, Prepared, PrepareWorker, ScanWorker, SelfTestWorker


class ElidedLabel(QLabel):
    """Keep the complete destination accessible while fitting one visible line."""

    def __init__(self) -> None:
        super().__init__()
        self.full_text = ""
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(False)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set_full_text(self, text: str, description: str) -> None:
        self.full_text = text
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self._elide()

    def _elide(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self.full_text, Qt.TextElideMode.ElideMiddle, self.contentsRect().width()
            )
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._elide()


class MainWindow(QMainWindow):
    def __init__(self, paths: RuntimePaths | None = None, *, interactive: bool = True):
        super().__init__()
        self.paths = paths or resolve_paths()
        self.registry = ModelRegistry(
            load_manifest(self.paths.resources_dir / "models.json"), self.paths.models_dir
        )
        self.interactive = interactive
        self.settings: dict = {"schema_version": 1}
        self.installed: tuple[str, ...] = ()
        self.vulkan_ok = False
        self.vad_installed = False
        self._explicit_model = False
        self.model_manager: ModelManager | None = None
        self.ready = False
        self.running = False
        self.closing = False
        self._previous_language = "auto"
        self._english_forced = False
        self._waiting_choice = False
        self._startup_dialogs_active = False
        self._startup_dialogs_shown = False
        self._applying = False
        self._recommendation = "small"
        self._follow_recommendation = False
        self._missing_resume_model: str | None = None
        self.output_dir: Path | None = None
        self.batch: BatchWorker | None = None
        self.scanner: ScanWorker | None = None
        self.preparer: PrepareWorker | None = None
        self._tasks: list[QThread] = []
        self._acknowledged: set[Path] = set()
        self._batch_started = 0.0
        self._active_received = 0.0
        self._active_id: UUID | None = None
        self._active_elapsed = 0.0
        self._timed_ids: set[UUID] = set()
        self._title_clicks = 0
        self._title_click_started = 0.0
        self.setWindowTitle(M.APP_NAME)
        self.setWindowIcon(application_icon())
        self.resize(1060, 780)
        self.setMinimumSize(800, 640)
        self.setAcceptDrops(True)
        self.model = QueueModel()
        self._build()
        self._menus()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._refresh()

    def _label(self, text: str, *, warning: bool = False) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        if warning:
            label.setObjectName("warning")
        return label

    def _button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.setAccessibleName(text)
        button.clicked.connect(callback)
        return button

    def _combo(self, entries: dict[str, str], name: str) -> QComboBox:
        combo = QComboBox()
        combo.setAccessibleName(name)
        combo.setItemDelegate(ChoiceDelegate(combo))
        for key, label in entries.items():
            combo.addItem(label, key)
        return combo

    def _build(self) -> None:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)
        self.title = self._label(M.APP_NAME)
        self.title.setObjectName("title")
        self.title.installEventFilter(self)
        layout.addWidget(self.title)
        layout.addWidget(self._label(M.TAGLINE))
        self.drop_area = QFrame()
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setContentsMargins(20, 32, 20, 32)
        drop_layout.addStretch()
        drop_title = self._label(M.DROP)
        drop_title.setObjectName("dropTitle")
        drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_title)
        help_label = self._label(M.DROP_HELP)
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(help_label)
        self.drop_buttons = QHBoxLayout()
        self.drop_buttons.addStretch()
        self.drop_buttons.addStretch()
        drop_layout.addLayout(self.drop_buttons)
        drop_layout.addStretch()
        self.edit_bar = QWidget()
        edit_layout = QHBoxLayout(self.edit_bar)
        self.edit_layout = edit_layout
        edit_layout.setContentsMargins(0, 0, 0, 0)
        self.add_files_button = self._button(M.ADD_FILES, self.choose_files)
        self.add_folder_button = self._button(M.ADD_FOLDER, self.choose_input_folder)
        self.edit_buttons = [self.add_files_button, self.add_folder_button]
        for button in self.edit_buttons:
            edit_layout.addWidget(button)
        self.queue_buttons = []
        for text, callback in (
            (M.REMOVE, self.remove_selected),
            (M.CLEAR, self.clear_queue),
        ):
            button = self._button(text, callback)
            edit_layout.addWidget(button)
            self.queue_buttons.append(button)
        edit_layout.addStretch()
        layout.addWidget(self.drop_area)
        layout.addWidget(self.edit_bar)
        self.table = QTableView()
        self.table.setAccessibleName(M.APP_NAME)
        self.table.setModel(self.model)
        self.table.installEventFilter(self)
        self.table.setTabKeyNavigation(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column, width in ((1, 75), (2, 160), (3, 110), (4, 75), (5, 110)):
            self.table.setColumnWidth(column, width)
        self.table.setItemDelegateForColumn(3, ProgressDelegate(self.table))
        self.table.clicked.connect(self._table_clicked)
        self.table.doubleClicked.connect(self._table_details)
        self.move_actions = []
        for text, direction, shortcut in ((M.MOVE_UP, -1, "Alt+Up"), (M.MOVE_DOWN, 1, "Alt+Down")):
            action = QAction(text, self.table)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.triggered.connect(lambda checked=False, step=direction: self.move_selected(step))
            self.table.addAction(action)
            self.move_actions.append(action)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._list_context_menu)
        layout.addWidget(self.table, 1)
        self.message_area = QWidget()
        message_layout = QVBoxLayout(self.message_area)
        message_layout.setContentsMargins(0, 0, 0, 0)
        self.status = self._label(M.PREPARING_HELP)
        self.warning = self._label(M.EMPTY_CELL, warning=True)
        for notice_label in (self.status, self.warning):
            notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            notice_label.setStyleSheet("font-size: 16px")
            message_layout.addWidget(notice_label)
        self.download_recommended_button = self._button(M.DOWNLOAD_IT, self.download_recommended)
        prompt_actions = QHBoxLayout()
        prompt_actions.addStretch()
        prompt_actions.addWidget(self.download_recommended_button)
        prompt_actions.addStretch()
        message_layout.addLayout(prompt_actions)
        layout.addWidget(self.message_area)
        self.output_row = QWidget()
        output_layout = QHBoxLayout(self.output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(layout.spacing())
        self.output_button = self._button(M.CHOOSE_OUTPUT_BUTTON, self.choose_output)
        output_layout.addWidget(self.output_button)
        self.output_label = ElidedLabel()
        output_layout.addWidget(self.output_label, 1)
        layout.addWidget(self.output_row)
        self.format_row = QWidget()
        formats_layout = QHBoxLayout(self.format_row)
        formats_layout.setContentsMargins(0, 0, 0, 0)
        self.formats = {}
        for key, label in M.FORMATS.items():
            checkbox = QCheckBox(label)
            checkbox.setChecked(key in {"txt", "docx"})
            checkbox.toggled.connect(self._rules)
            self.formats[key] = checkbox
            if key in {"txt", "docx"}:
                formats_layout.addWidget(checkbox)
        formats_layout.addStretch()
        layout.addWidget(self.format_row)
        options_bar = QHBoxLayout()
        self.options_button = self._button(M.OPTIONS, self.open_options)
        options_bar.addWidget(self.options_button)
        button_width = max(
            self.output_button.sizeHint().width(), self.options_button.sizeHint().width()
        )
        self.output_button.setFixedWidth(button_width)
        self.options_button.setFixedWidth(button_width)
        self.choices_summary = self._label(M.PREPARING)
        options_bar.addWidget(self.choices_summary, 1)
        layout.addLayout(options_bar)
        self.slow_model_notice = self._label(M.EMPTY_CELL, warning=True)
        layout.addWidget(self.slow_model_notice)
        self.options_scroll = QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_dialog = TextDialog(M.OPTIONS_TITLE, (), self)
        self.options_dialog.setModal(True)
        self.options_dialog.resize(660, 650)
        self.options_dialog.body.insertWidget(0, self.options_scroll, 1)
        self.options_dialog.button(M.DISMISS, self.options_dialog.accept, default=True)
        options = QWidget()
        form = QFormLayout(options)
        self.model_choice = QComboBox()
        self.model_choice.setPlaceholderText(M.MODEL_PLACEHOLDER)
        self.model_choice.setAccessibleName(M.MODEL)
        form.addRow(M.MODEL, self.model_choice)
        self.model_details = self._label(M.EMPTY_CELL)
        self.model_warning = self._label(M.EMPTY_CELL, warning=True)
        form.addRow(self.model_details)
        form.addRow(self.model_warning)
        self.manage_models_button = self._button(M.MANAGE_MODELS, self.open_model_manager)
        form.addRow(self.manage_models_button)
        self.task_choice = self._combo(M.TASKS, M.TASK)
        form.addRow(M.TASK, self.task_choice)
        self.language_choice = QComboBox()
        self.language_choice.setAccessibleName(M.LANGUAGE)
        self.language_choice.addItem(M.AUTO_LANGUAGE, "auto")
        common = ("en", "fa", "es", "fr", "de", "ar", "zh")
        names = dict(M.LANGUAGES)
        for code in common:
            self.language_choice.addItem(names[code], code)
        for code, name in sorted(M.LANGUAGES, key=lambda item: item[1]):
            if code not in common:
                self.language_choice.addItem(name, code)
        form.addRow(M.LANGUAGE, self.language_choice)
        self.incompatible = self._label(M.TRANSLATE_DISABLED, warning=True)
        form.addRow(self.incompatible)
        self.use_medium = self._button(M.USE_MEDIUM, self._use_medium)
        form.addRow(self.use_medium)
        self.prompt = QPlainTextEdit()
        self.prompt.setAccessibleName(M.PROMPT)
        self.prompt.setPlaceholderText(M.PROMPT_EXAMPLE)
        self.prompt.setMaximumHeight(72)
        self.prompt.setTabChangesFocus(True)
        form.addRow(M.PROMPT, self.prompt)
        form.addRow(self._label(M.PROMPT_HELP))
        self.prompt_warning = self._label(M.PROMPT_WARNING, warning=True)
        form.addRow(self.prompt_warning)
        self.collision_choice = self._combo(M.COLLISIONS, M.COLLISION)
        form.addRow(M.COLLISION, self.collision_choice)
        more_formats = QWidget()
        more_layout = QHBoxLayout(more_formats)
        more_layout.setContentsMargins(0, 0, 0, 0)
        for key in ("srt", "vtt", "json"):
            more_layout.addWidget(self.formats[key])
        form.addRow(M.MORE_FORMATS, more_formats)
        self.same_folder = QCheckBox(M.SAME_FOLDER)
        self.keep_structure = QCheckBox(M.KEEP_STRUCTURE)
        form.addRow(self.same_folder)
        form.addRow(self.keep_structure)
        self.theme_choice = self._combo(M.THEMES, M.THEME)
        form.addRow(M.THEME, self.theme_choice)
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText(M.ADVANCED)
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        form.addRow(self.advanced_toggle)
        self.advanced = QWidget()
        advanced_form = QFormLayout(self.advanced)
        self.device_choice = self._combo(M.DEVICES, M.DEVICE)
        advanced_form.addRow(M.DEVICE, self.device_choice)
        advanced_form.addRow(self._label(M.DEVICE_HELP))
        self.threads_choice = QSpinBox()
        self.threads_choice.setRange(1, os.cpu_count() or 1)
        self.threads_choice.setValue(default_threads())
        self.threads_choice.setAccessibleName(M.THREADS)
        advanced_form.addRow(M.THREADS, self.threads_choice)
        advanced_form.addRow(self._label(M.THREADS_HELP))
        self.vad = QCheckBox(M.VAD)
        self.vad.setChecked(False)
        advanced_form.addRow(self.vad)
        advanced_form.addRow(self._label(M.VAD_HELP))
        form.addRow(self.advanced)
        self.advanced.hide()
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        self.options_scroll.setWidget(options)

        self.resume_model_button = self._button(M.EMPTY_CELL, self._confirm_resume_model)
        layout.addWidget(self.resume_model_button)
        bottom = QHBoxLayout()
        self.overall = QProgressBar()
        self.overall.setRange(0, 1000)
        self.overall.setTextVisible(False)
        bottom.addWidget(self.overall, 1)
        self.start_hint = self._label(M.EMPTY_CELL, warning=True)
        self.start_hint.setStyleSheet("font-size: 16px")
        self.start_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cancel_current_button = self._button(M.CANCEL_CURRENT, self.cancel_current)
        self.cancel_all_button = self._button(M.CANCEL_ALL, self.cancel_all)
        bottom.addWidget(self.cancel_current_button)
        bottom.addWidget(self.cancel_all_button)
        self.start_button = self._button(M.START, self.start_batch)
        self.start_button.setObjectName("startButton")
        self.start_button.setDefault(True)
        layout.addLayout(bottom)
        layout.addWidget(self.start_hint)
        layout.addWidget(self.start_button)
        self.setCentralWidget(body)
        for combo in (self.model_choice, self.task_choice, self.language_choice):
            combo.currentIndexChanged.connect(self._rules)
        self.model_choice.activated.connect(self._model_chosen)
        self.same_folder.toggled.connect(self._rules)
        self.device_choice.currentIndexChanged.connect(self._device_changed)
        self.prompt.textChanged.connect(self._rules)
        self.vad.toggled.connect(self._rules)
        self.theme_choice.currentIndexChanged.connect(self._theme_changed)
        for first, second in zip(
            (self.output_button, self.formats["txt"], self.formats["docx"], self.options_button),
            (self.formats["txt"], self.formats["docx"], self.options_button, self.start_button),
            strict=True,
        ):
            QWidget.setTabOrder(first, second)

    def _menus(self) -> None:
        file_menu = self.menuBar().addMenu(M.FILE_MENU)
        tools = self.menuBar().addMenu(M.TOOLS_MENU)
        help_menu = self.menuBar().addMenu(M.HELP_MENU)
        self.edit_actions = []
        for text, callback, menu in (
            (M.ADD_FILES, self.choose_files, file_menu),
            (M.ADD_FOLDER, self.choose_input_folder, file_menu),
            (M.CHOOSE_OUTPUT_MENU, self.choose_output, file_menu),
            (M.CLEAR_FINISHED, self.clear_finished, tools),
            (M.CLEAR_HISTORY, self.clear_queue, tools),
        ):
            action = QAction(text, self)
            action.triggered.connect(callback)
            menu.addAction(action)
            self.edit_actions.append(action)
        file_menu.addAction(M.EXIT, self.close)
        self.manage_models_action = tools.addAction(M.MANAGE_MODELS, self.open_model_manager)
        self.selftest_action = tools.addAction(M.SELF_TEST, self.run_selftest)
        help_menu.addAction(
            M.PRIVACY_TITLE,
            lambda: TextDialog(M.PRIVACY_TITLE, (M.PRIVACY, M.ACCURACY), self).exec(),
        )
        self.about_action = help_menu.addAction(M.ABOUT, self.show_about)

    def show_about(self) -> None:
        AboutDialog(__version__, self.open_notices, self).exec()

    def open_notices(self) -> None:
        NoticesDialog(self.paths.resources_dir.parent / "THIRD_PARTY_NOTICES.md", self).exec()

    def initialize(self) -> None:
        if self.preparer and self.preparer.isRunning():
            return
        configure_logger(self.paths.user_dir)
        self.ready = False
        self.status.setText(M.PREPARING_HELP)
        self.overall.setRange(0, 0)
        self.preparer = PrepareWorker(self.paths, self.registry)
        self._tasks.append(self.preparer)
        self.preparer.ready.connect(self.apply_prepared)
        self.preparer.failed.connect(self._prepare_failed)
        self.preparer.finished.connect(self._background_finished)
        self.preparer.start()

    @Slot(object)
    def apply_prepared(self, prepared: Prepared) -> None:
        self.installed, self.vulkan_ok, self.settings = (
            prepared.installed,
            prepared.vulkan_ok,
            prepared.settings,
        )
        self.ready = True
        self.vad_installed = prepared.vad_installed
        self._explicit_model = bool(self.settings.get("model_id"))
        self.model_choice.blockSignals(True)
        self.model_choice.clear()
        recommended = recommend_model(vulkan_ok=self.vulkan_ok, task="transcribe")
        for model_id in self.installed:
            name = M.MODEL_NAMES[model_id]
            self.model_choice.addItem(
                M.RECOMMENDED.format(name=name) if model_id == recommended else name, model_id
            )
        self.model_choice.blockSignals(False)
        default = (
            recommended
            if recommended in self.installed
            else next(
                (
                    m
                    for m in ("small", "tiny", "small.en", "medium", "large-v3-turbo-q8_0")
                    if m in self.installed
                ),
                "",
            )
        )
        self._set_combo(self.model_choice, self.settings.get("model_id", default))
        self._apply_settings(self.settings, restore_output=True)
        self.overall.setRange(0, 1000)
        self.status.setText(M.READY)
        self._refresh()
        if self.interactive and not self.closing:
            QTimer.singleShot(0, lambda: self._startup_dialogs(prepared))

    def _startup_dialogs(self, prepared: Prepared) -> None:
        if self._startup_dialogs_active or self._startup_dialogs_shown or self.closing:
            return
        self._startup_dialogs_active = True
        self._startup_dialogs_shown = True
        try:
            if self.settings.get("managed_folder_notice", False):
                self.settings["managed_folder_notice"] = False
                self.show_error(text=M.MANAGED_FOLDER)
                self._save_settings()
            # A saved folder is the welcome gate, including older settings files.
            # exec() keeps recovery behind welcome even with nested Qt events.
            if not self.output_dir:
                if WelcomeDialog(self).exec() == QDialog.DialogCode.Accepted:
                    self.choose_output()
                    if self.output_dir:
                        self.settings["welcome_seen"] = True
                        self._save_settings()
            if prepared.recovered:
                options, jobs = prepared.recovered
                remaining = sum(
                    job.status not in {JobStatus.DONE, JobStatus.SKIPPED} for job in jobs
                )
                if (
                    remaining
                    and ResumeDialog(remaining, self).exec() == QDialog.DialogCode.Accepted
                ):
                    self.restore_batch(options, jobs)
                    QTimer.singleShot(0, self.start_batch)
                else:
                    clear_history(self.paths.user_dir / "state/queue.json")
        finally:
            self._startup_dialogs_active = False

    def restore_batch(self, options: BatchOptions, jobs: list[Job]) -> None:
        from dataclasses import asdict

        for job in jobs:
            if job.status not in {JobStatus.DONE, JobStatus.SKIPPED}:
                job.elapsed_sec = 0.0
        self.model.set_jobs(jobs)
        self._missing_resume_model = (
            options.model_id if options.model_id not in self.installed else None
        )
        self._apply_settings({**asdict(options), "vad_user_set": True})
        self._refresh()

    def _set_combo(self, combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0 or combo is self.model_choice and value is None:
            combo.setCurrentIndex(index)

    def _apply_settings(self, settings: dict, *, restore_output: bool = False) -> None:
        self._applying = True
        for key, combo in (
            ("model_id", self.model_choice),
            ("language", self.language_choice),
            ("task", self.task_choice),
            ("backend", self.device_choice),
            ("collision", self.collision_choice),
            ("theme", self.theme_choice),
        ):
            if key in settings:
                self._set_combo(combo, settings[key])
        if restore_output and self.output_dir is None and settings.get("output_dir"):
            from dusty.work_area import managed_destination

            output = Path(settings["output_dir"])
            if not managed_destination(output, self.paths):
                self.output_dir = output
        for key, box in (
            ("same_folder", self.same_folder),
            ("keep_structure", self.keep_structure),
            ("vad", self.vad),
        ):
            if key in settings:
                box.setChecked(
                    settings[key] if key != "vad" or settings.get("vad_user_set") is True else False
                )
        if "formats" in settings:
            for key, checkbox in self.formats.items():
                checkbox.setChecked(key in settings["formats"])
        self.prompt.setPlainText(settings.get("prompt", ""))
        self.threads_choice.setValue(settings.get("threads", default_threads()))
        geometry = settings.get("geometry")
        if isinstance(geometry, str):
            self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii", errors="ignore")))
        self._theme_changed()
        self._applying = False
        self._rules()
        if self._english_forced:
            self._previous_language = settings.get("preferred_language", self._previous_language)

    def _save_settings(self) -> bool:
        from dusty.queue.storage import load_settings

        try:
            settings = load_settings(self.paths.user_dir / "settings.json")
            # Folder choice has a single writer: choose_output. Neither a stale
            # recovery snapshot nor model/installer notifications may replace it.
            settings.update({k: v for k, v in self.settings.items() if k != "output_dir"})
            settings.update(
                {
                    "schema_version": 1,
                    "model_id": self.model_choice.currentData(),
                    "language": self.language_choice.currentData(),
                    "preferred_language": self._previous_language
                    if self._english_forced
                    else self.language_choice.currentData(),
                    "task": self.task_choice.currentData(),
                    "backend": self.device_choice.currentData(),
                    "collision": self.collision_choice.currentData(),
                    "formats": [
                        key for key, checkbox in self.formats.items() if checkbox.isChecked()
                    ]
                    or ["txt", "docx"],
                    "threads": self.threads_choice.value(),
                    "vad": self.vad.isChecked(),
                    "vad_user_set": True,
                    "prompt": self.prompt.toPlainText(),
                    "same_folder": self.same_folder.isChecked(),
                    "keep_structure": self.keep_structure.isChecked(),
                    "theme": self.theme_choice.currentData(),
                    "geometry": bytes(self.saveGeometry().toBase64().data()).decode("ascii"),
                }
            )
            save_settings(self.paths.user_dir / "settings.json", settings)
            self.settings = settings
            return True
        except (OSError, ValueError):
            self.show_error(text=M.SAVE_ERROR)
            return False

    def open_options(self) -> None:
        self.options_dialog.exec()
        if self.ready:
            self._save_settings()

    def _model_chosen(self) -> None:
        self._explicit_model = True
        self._confirm_resume_model()

    def _track_model_worker(self, worker: QThread) -> None:
        self._tasks.append(worker)
        worker.finished.connect(lambda: QTimer.singleShot(0, self._background_finished))

    def download_recommended(self) -> None:
        target = self._recommendation if not self.installed else VOICE_ID
        self.open_model_manager(focus_id=target)

    def open_model_manager(self, *, focus_id: str | None = None) -> None:
        if not self.ready or self.running:
            return
        dialog = ModelManager(
            self.registry,
            self.paths,
            self,
            selected=lambda: self.model_choice.currentData(),
            voice_in_use=self.vad.isChecked,
            recommended=self._recommendation,
            focus_id=focus_id or self.model_choice.currentData(),
            track_worker=self._track_model_worker,
        )
        self.model_manager = dialog
        dialog.models_changed.connect(self._models_changed)
        dialog.exec()
        self._refresh()

    @Slot(object)
    def _models_changed(self, statuses: dict[str, str]) -> None:
        previous = self.model_choice.currentData()
        old_installed = self.installed
        self.installed = tuple(
            key for key, state in statuses.items() if state == "installed" and key != VOICE_ID
        )
        self.vad_installed = statuses.get(VOICE_ID) == "installed"
        self.model_choice.blockSignals(True)
        self.model_choice.clear()
        for key in self.installed:
            self.model_choice.addItem(M.MODEL_NAMES[key], key)
        newly_installed = [key for key in self.installed if key not in old_installed]
        desired = previous if previous in self.installed else None
        if previous is None and newly_installed:
            desired = (
                self._recommendation
                if self._recommendation in newly_installed
                else newly_installed[0]
            )
        self._set_combo(self.model_choice, desired)
        self.model_choice.blockSignals(False)
        self._refresh()
        self._save_settings()

    def eventFilter(self, watched, event) -> bool:
        if (
            watched is getattr(self, "title", None)
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            if event.button() == Qt.MouseButton.LeftButton:
                # Intentional maintainer-requested hidden greeting: memory-only, no side effects.
                now = time.monotonic()
                if not self._title_clicks or now - self._title_click_started > 4.0:
                    self._title_clicks = 0
                    self._title_click_started = now
                self._title_clicks += 1
                if self._title_clicks == 7:
                    self._title_clicks = 0
                    self._title_click_started = 0.0
                    GreetingDialog(self).exec()
        if (
            watched is getattr(self, "table", None)
            and isinstance(event, QKeyEvent)
            and event.modifiers() == Qt.KeyboardModifier.AltModifier
            and event.key() in {Qt.Key.Key_Up, Qt.Key.Key_Down}
            and event.type() in {QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress}
        ):
            if event.type() == QEvent.Type.KeyPress:
                self.move_selected(-1 if event.key() == Qt.Key.Key_Up else 1)
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _list_context_menu(self, point) -> None:
        index = self.table.indexAt(point)
        if index.isValid() and not self.table.selectionModel().isRowSelected(index.row()):
            self.table.selectRow(index.row())
        menu = QMenu(self.table)
        menu.addActions(self.move_actions)
        menu.exec(self.table.viewport().mapToGlobal(point))

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced.setVisible(expanded)
        self.advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _theme_changed(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, self.theme_choice.currentData() or "system")

    @Slot()
    def _system_theme_changed(self) -> None:
        if self.theme_choice.currentData() == "system":
            self._theme_changed()

    def _device_changed(self) -> None:
        if self._applying:
            return
        self._follow_recommendation = (
            not self._explicit_model and self.model_choice.currentData() == self._recommendation
        )
        self._rules()
        if self.ready and self.interactive and not self.running:
            self.ready = False
            self.status.setText(M.PREPARING_HELP)
            self.overall.setRange(0, 0)
            self.preparer = PrepareWorker(self.paths, self.registry, refresh_probe=True)
            self._tasks.append(self.preparer)
            self.preparer.ready.connect(self._device_prepared)
            self.preparer.failed.connect(self._prepare_failed)
            self.preparer.finished.connect(self._background_finished)
            self.preparer.start()
            self._refresh()

    @Slot(object)
    def _device_prepared(self, prepared: Prepared) -> None:
        self.vulkan_ok = prepared.vulkan_ok
        self.vad_installed = prepared.vad_installed
        if "backend_probe" in prepared.settings:
            self.settings["backend_probe"] = prepared.settings["backend_probe"]
        self.ready = True
        self.overall.setRange(0, 1000)
        self.status.setText(M.READY)
        self._rules()
        if self._follow_recommendation and self._recommendation in self.installed:
            self._set_combo(self.model_choice, self._recommendation)
        self._refresh()

    def _rules(self) -> None:
        if not hasattr(self, "start_button") or self._applying:
            return
        model_id = self.model_choice.currentData()
        model = self.registry.manifest.models.get(model_id)
        incompatible = model is not None and not can_translate(model)
        english_only = bool(model and model.english_only)
        self.language_choice.setEnabled(not english_only and not self.running)
        if english_only and not self._english_forced:
            self._previous_language = self.language_choice.currentData() or "auto"
            self._english_forced = True
            self._set_combo(self.language_choice, "en")
        if english_only and self.language_choice.currentData() != "en":
            self._set_combo(self.language_choice, "en")
        elif not english_only and self._english_forced:
            self._english_forced = False
            self._set_combo(self.language_choice, self._previous_language)
        task_model = self.task_choice.model()
        if isinstance(task_model, QStandardItemModel):
            translate_item = task_model.item(1)
            if translate_item:
                translate_item.setText(
                    M.TRANSLATE_UNAVAILABLE if incompatible else M.TASKS["translate"]
                )
                translate_item.setEnabled(not incompatible)
                translate_item.setToolTip(M.TRANSLATE_DISABLED if incompatible else M.EMPTY_CELL)
        invalid = incompatible and self.task_choice.currentData() == "translate"
        self.incompatible.setText(M.TRANSLATE_REASON if english_only else M.TRANSLATE_DISABLED)
        self.incompatible.setVisible(bool(invalid or english_only))
        self.use_medium.setVisible(bool(invalid and "medium" in self.installed))
        self.model_details.setText(M.MODEL_DETAILS.get(model_id, M.EMPTY_CELL))
        self.prompt_warning.setVisible(len(self.prompt.toPlainText()) / 4 > 200)
        cpu_only = not self.vulkan_ok or self.device_choice.currentData() == "cpu"
        slow = bool(model and cpu_only and model.speed_cpu == "slow")
        for notice in (self.model_warning, self.slow_model_notice):
            notice.setText(M.SLOW if slow else M.EMPTY_CELL)
            notice.setVisible(slow)
        warning = M.EMPTY_CELL
        recommended = recommend_model(
            vulkan_ok=not cpu_only, task=cast(Task, self.task_choice.currentData())
        )
        self._recommendation = recommended
        for index in range(self.model_choice.count()):
            candidate = self.model_choice.itemData(index)
            name = M.MODEL_NAMES[candidate]
            self.model_choice.setItemText(
                index, M.RECOMMENDED.format(name=name) if candidate == recommended else name
            )
        if self.ready and not self.installed:
            unavailable = M.MISSING_RECOMMENDATION.format(name=M.MODEL_TECHNICAL[recommended])
            warning = unavailable + ("\n" + warning if warning else "")
        self.resume_model_button.setVisible(bool(self._missing_resume_model))
        self.resume_model_button.setText(
            M.USE_INSTALLED.format(model=M.MODEL_NAMES.get(model_id, M.PREPARING))
        )
        self.resume_model_button.setEnabled(bool(model and not invalid and not self.running))
        needs_voice = self.vad.isChecked() and not self.vad_installed
        if model and needs_voice:
            warning = M.VAD_MISSING
        prompt = self.ready and (not self.installed or needs_voice)
        self.download_recommended_button.setText(
            M.DOWNLOAD_RECOMMENDED.format(name=M.MODEL_TECHNICAL[recommended])
            if not self.installed
            else M.DOWNLOAD_VOICE
        )
        self.download_recommended_button.setVisible(bool(prompt) and not self.running)
        self.download_recommended_button.setEnabled(not self.running)
        hint = M.EMPTY_CELL
        if not model and self.ready:
            hint = M.NO_MODELS if not self.installed else M.CHOOSE_MODEL
        elif needs_voice:
            hint = M.VAD_MISSING
        elif not self.output_dir and not self.same_folder.isChecked():
            hint = M.CHOOSE_OUTPUT_FIRST
        elif self.model.jobs and all(
            job.status in {JobStatus.DONE, JobStatus.SKIPPED} for job in self.model.jobs
        ):
            hint = M.EVERYTHING_DONE
        elif self._missing_resume_model:
            hint = M.MISSING_BATCH_MODEL.format(
                model=M.MODEL_NAMES.get(self._missing_resume_model, self._missing_resume_model)
            )
        elif not model and self.ready:
            hint = M.NO_MODELS if not self.installed else M.CHOOSE_MODEL
        elif invalid:
            hint = M.TRANSLATE_DISABLED
        elif not any(box.isChecked() for box in self.formats.values()):
            hint = M.NO_FORMATS
        if self.running:
            hint = M.START_RUNNING
        elif not self.ready:
            hint = M.PREPARING
        elif self.scanner and self.scanner.isRunning():
            hint = M.SCANNING
        elif any(isinstance(task, SelfTestWorker) and task.isRunning() for task in self._tasks):
            hint = M.SELF_TEST_RUNNING
        elif not self.model.jobs and not hint:
            hint = M.ADD_RECORDINGS_FIRST
        self.start_hint.setText(hint)
        self.start_hint.setVisible(bool(hint))
        if self.settings.get("installer_test_failed"):
            warning = M.INSTALLER_TEST_WARNING
        self.warning.setText(warning or M.EMPTY_CELL)
        self.warning.setVisible(bool(warning))
        self.choices_summary.setText(
            M.CHOICES_SUMMARY.format(
                model=M.MODEL_NAMES.get(model_id, M.NO_MODEL_SELECTED),
                language=self.language_choice.currentText(),
                device=M.DEVICES["cpu" if cpu_only else "vulkan"],
            )
            + (", " + M.SILENCE_ON if self.vad.isChecked() else "")
        )
        output_text = (
            M.SAVING_NEXT_TO
            if self.same_folder.isChecked()
            else M.SAVING_TO.format(path=str(self.output_dir))
            if self.output_dir
            else M.NO_OUTPUT
        )
        self.output_label.set_full_text(
            output_text,
            str(self.output_dir)
            if self.output_dir and not self.same_folder.isChecked()
            else output_text,
        )
        self.output_label.setObjectName(
            "warning" if not self.output_dir and not self.same_folder.isChecked() else ""
        )
        self.output_label.style().unpolish(self.output_label)
        self.output_label.style().polish(self.output_label)
        self.output_button.setEnabled(not self.running and not self.same_folder.isChecked())
        self.start_button.setEnabled(
            bool(
                self.ready
                and model
                and not invalid
                and not needs_voice
                and not self._missing_resume_model
                and not self.running
                and self.model.jobs
                and any(
                    job.status not in {JobStatus.DONE, JobStatus.SKIPPED} for job in self.model.jobs
                )
                and (self.output_dir or self.same_folder.isChecked())
                and any(box.isChecked() for box in self.formats.values())
                and not (self.scanner and self.scanner.isRunning())
                and not any(
                    isinstance(task, SelfTestWorker) and task.isRunning() for task in self._tasks
                )
            )
        )
        if not self.start_button.isEnabled() and self.status.text() == M.READY:
            self.status.clear()
        elif self.start_button.isEnabled() and not self.status.text():
            self.status.setText(M.READY)

    def _use_medium(self) -> None:
        self._explicit_model = True
        self._set_combo(self.model_choice, "medium")
        self._set_combo(self.task_choice, "translate")
        self._missing_resume_model = None
        self._rules()

    def _confirm_resume_model(self) -> None:
        self._missing_resume_model = None
        self._rules()

    def _refresh(self) -> None:
        has_jobs = bool(self.model.jobs)
        self.edit_bar.setVisible(has_jobs)
        for index, button in enumerate(self.edit_buttons):
            parent = self.edit_bar if has_jobs else self.drop_area
            if button.parentWidget() is not parent:
                target = self.edit_layout if has_jobs else self.drop_buttons
                target.insertWidget(index if has_jobs else index + 1, button)
        self.drop_area.setVisible(not has_jobs)
        self.table.setVisible(has_jobs)
        self.output_row.setVisible(True)
        self.format_row.setVisible(True)
        editing = not self.running and not (self.scanner and self.scanner.isRunning())
        for button in self.edit_buttons + self.queue_buttons:
            button.setEnabled(editing)
        for button in self.queue_buttons:
            button.setVisible(has_jobs)
        for action in self.edit_actions:
            action.setEnabled(editing)
        self.manage_models_button.setEnabled(self.ready and not self.running)
        self.manage_models_action.setEnabled(self.ready and not self.running)
        self.options_button.setEnabled(self.ready and not self.running)
        self.options_scroll.setEnabled(self.ready and not self.running)
        for action in self.move_actions:
            action.setEnabled(editing)
        self.format_row.setEnabled(not self.running)
        self.selftest_action.setEnabled(
            self.ready
            and editing
            and bool(self.installed)
            and not any(task.isRunning() for task in self._tasks)
        )
        self.cancel_current_button.setVisible(self.running)
        self.cancel_all_button.setVisible(self.running)
        self.start_button.setVisible(True)
        self.overall.setVisible(self.running)
        self._rules()

    def choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, M.ADD_FILES, "", M.FILE_FILTER)
        if files:
            self.add_paths([Path(path) for path in files])

    def choose_input_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, M.ADD_FOLDER)
        if folder:
            dialog = FolderDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.add_paths([Path(folder)], recursive=dialog.recursive.isChecked())

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, M.CHOOSE_FOLDER)
        if folder:
            from dusty.work_area import managed_destination

            if managed_destination(Path(folder), self.paths):
                self.show_error(text=M.MANAGED_FOLDER)
                return
            from dusty.queue.storage import load_settings

            try:
                file = self.paths.user_dir / "settings.json"
                settings = load_settings(file)
                settings["output_dir"] = folder
                save_settings(file, settings)
            except (OSError, ValueError):
                self.show_error(text=M.SAVE_ERROR)
                return
            self.settings["output_dir"] = folder
            self.output_dir = Path(folder)
            self._rules()

    def add_paths(self, paths: list[Path], *, recursive: bool = False) -> None:
        if self.running or (self.scanner and self.scanner.isRunning()):
            return
        from dusty.work_area import managed_destination

        if any(managed_destination(path, self.paths) for path in paths):
            self.show_error(text=M.MANAGED_FOLDER)
            return
        self.status.setText(M.SCANNING)
        self.scanner = ScanWorker(paths, recursive, list(self.model.jobs), self.paths)
        self._tasks.append(self.scanner)
        self.scanner.ready.connect(self._scanned)
        self.scanner.failed.connect(self._scan_failed)
        self.scanner.finished.connect(self._background_finished)
        self.scanner.start()
        self._refresh()

    @Slot(object)
    def _scanned(self, result: ScanResult) -> None:
        from dusty.work_area import managed_destination

        if any(managed_destination(job.source, self.paths) for job in result.jobs):
            self.show_error(text=M.MANAGED_FOLDER)
            return
        repeated = set(result.duplicate_paths)
        reset = 0
        for job in self.model.jobs:
            if job.status == JobStatus.DONE and job.source.resolve() in repeated:
                job.status = JobStatus.QUEUED
                job.failure = None
                job.progress = job.elapsed_sec = 0.0
                job.outputs = []
                job.backend_used = None
                job.gpu_fallback = False
                reset += 1
        self.model.set_jobs(self.model.jobs + list(result.jobs))
        if result.rejected:
            self.show_error(text=M.MANAGED_FOLDER)
        name = result.duplicate_paths[0].name if len(result.duplicate_paths) == 1 else ""
        self.status.setText(
            M.scan_summary(len(result.jobs), result.unsupported, result.duplicates, name)
        )
        if reset:
            remaining = M.scan_summary(
                len(result.jobs), result.unsupported, max(0, result.duplicates - reset)
            )
            self.status.setText(" ".join(filter(None, (M.ready_again(reset), remaining))))
        if result.duplicate_paths:
            self.model.highlighted = set(result.duplicate_paths)
            self.model.layoutChanged.emit()
            index = next(
                (
                    i
                    for i, job in enumerate(self.model.jobs)
                    if job.source in self.model.highlighted
                ),
                None,
            )
            if index is not None:
                self.table.scrollTo(self.model.index(index, 0))
            QTimer.singleShot(1800, self._clear_highlight)
        self._refresh()

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table.selectionModel().selectedRows()})

    def remove_selected(self) -> None:
        if self.running:
            return
        rows = set(self._selected_rows())
        self.model.set_jobs([job for row, job in enumerate(self.model.jobs) if row not in rows])
        self._refresh()

    def move_selected(self, direction: int) -> None:
        rows = self._selected_rows()
        if self.running or len(rows) != 1:
            return
        row = rows[0]
        target = row + direction
        if 0 <= target < len(self.model.jobs):
            jobs = list(self.model.jobs)
            jobs[row], jobs[target] = jobs[target], jobs[row]
            self.model.set_jobs(jobs)
            self.table.selectRow(target)

    def _clear_highlight(self) -> None:
        self.model.highlighted.clear()
        self.model.layoutChanged.emit()

    def clear_finished(self) -> None:
        if not self.running:
            self.model.set_jobs(
                [
                    job
                    for job in self.model.jobs
                    if job.status not in {JobStatus.DONE, JobStatus.SKIPPED}
                ]
            )
            self._refresh()

    def clear_queue(self) -> None:
        if not self.running:
            self.model.set_jobs([])
            clear_history(self.paths.user_dir / "state/queue.json")
            self._refresh()

    def dragEnterEvent(self, event) -> None:
        if (
            not self.running
            and event.mimeData().hasUrls()
            and all(url.isLocalFile() for url in event.mimeData().urls())
        ):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        recursive = False
        if any(path.is_dir() for path in paths):
            dialog = FolderDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            recursive = dialog.recursive.isChecked()
        self.add_paths(paths, recursive=recursive)
        event.acceptProposedAction()

    def batch_options(self) -> BatchOptions:
        return BatchOptions(
            self.model_choice.currentData(),
            self.output_dir,
            formats=cast(
                tuple[OutputFormat, ...],
                tuple(key for key, box in self.formats.items() if box.isChecked()),
            ),
            language=self.language_choice.currentData(),
            task=cast(Task, self.task_choice.currentData()),
            backend=cast(Backend, self.device_choice.currentData()),
            threads=self.threads_choice.value(),
            vad=self.vad.isChecked(),
            prompt=self.prompt.toPlainText(),
            collision=cast(CollisionPolicy, self.collision_choice.currentData()),
            same_folder=self.same_folder.isChecked(),
            keep_structure=self.keep_structure.isChecked(),
        )

    def start_batch(self, *, retry_failed: bool = False) -> None:
        if not self.ready or self.running or not self.start_button.isEnabled():
            return
        options = self.batch_options()
        from dusty.queue.outputs import output_targets
        from dusty.work_area import managed_destination

        if any(
            managed_destination(path, self.paths)
            for job in self.model.jobs
            for path in (job.source, *output_targets(job, replace(options, collision="overwrite")))
        ):
            self.show_error(text=M.MANAGED_FOLDER)
            return
        destinations = {
            job.source.parent if options.same_folder else options.output_dir
            for job in self.model.jobs
        }
        for folder in destinations:
            if folder is None:
                raise ValueError("Output directory required")
            resolved = folder.resolve()
            if resolved not in self._acknowledged and is_synced(resolved):
                if SyncDialog(self).exec() != QDialog.DialogCode.Accepted:
                    if not options.same_folder:
                        self.choose_output()
                    return
                self._acknowledged.add(resolved)
        if not self._save_settings():
            return
        jobs = [
            replace(job, outputs=list(job.outputs))
            for job in self.model.jobs
            if not retry_failed or job.status == JobStatus.FAILED
        ]
        self.batch = BatchWorker(self.paths, self.registry, jobs, options, self.vulkan_ok)
        self._tasks.append(self.batch)
        self.batch.changed.connect(self._job_changed)
        self.batch.collision.connect(self._collision)
        self.batch.failed.connect(self._prepare_failed)
        self.batch.state_failed.connect(lambda: self.show_error(text=M.STATE_SAVE_ERROR))
        self.batch.finished.connect(self._batch_finished)
        self.running = True
        self._batch_started = time.monotonic()
        self._timed_ids = {
            job.id for job in jobs if job.status not in {JobStatus.DONE, JobStatus.SKIPPED}
        }
        self.overall.setRange(0, 1000)
        self.status.setText(M.PREPARING)
        self._refresh()
        self.batch.start()

    @Slot(object)
    def _job_changed(self, job: Job) -> None:
        self.model.update_job(job)
        if job.status not in TERMINAL:
            self._active_id = job.id
            self._active_received = time.monotonic()
            self._active_elapsed = job.elapsed_sec
        self._tick()

    @Slot(object)
    def _collision(self, job: Job) -> None:
        if not self.batch:
            return
        self._waiting_choice = True
        self.model.waiting_choice = job.id
        self._active_id = job.id
        job.status = JobStatus.QUEUED
        job.elapsed_sec = 0
        self.model.update_job(job)
        self.status.setText(M.WAITING_CHOICE)
        dialog = CollisionDialog(job.outputs[0].name if job.outputs else job.source.name, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.batch.choose_collision(dialog.selected_policy(), dialog.apply_all.isChecked())
        else:
            self.cancel_all()
        self._waiting_choice = False
        self.model.waiting_choice = None
        self.model.layoutChanged.emit()

    def cancel_current(self) -> None:
        if self.batch and self.running:
            self.batch.cancel_current.set()

    def cancel_all(self) -> None:
        if self.batch and self.running:
            self.batch.cancel_all.set()
            self.status.setText(M.CLOSING)

    @Slot()
    def _batch_finished(self) -> None:
        self.running = False
        self._active_id = None
        if self.batch:
            for job in self.batch.jobs:
                self.model.update_job(replace(job, outputs=list(job.outputs)))
        self.overall.setValue(int(overall_progress(self.model.jobs) * 1000))
        self.status.setText(M.summary_counts(counts(self.model.jobs)))
        self._refresh()
        if self.closing:
            self.close()
            return
        if self.interactive:
            dialog = SummaryDialog(self.model.jobs, self)
            dialog.open_folder.clicked.connect(self.open_output)
            result = dialog.exec()
            if result == 2:
                self.start_batch(retry_failed=True)
            else:
                clear_history(self.paths.user_dir / "state/queue.json")
            if any(job.gpu_fallback for job in self.model.jobs):
                TextDialog(M.APP_NAME, (M.GPU_NOTICE,), self).exec()

    def _tick(self) -> None:
        if not self.running or self._waiting_choice:
            return
        for row, job in enumerate(self.model.jobs):
            if job.id == self._active_id and job.status not in TERMINAL:
                job.elapsed_sec = self._active_elapsed + time.monotonic() - self._active_received
                self.model.dataChanged.emit(self.model.index(row, 4), self.model.index(row, 4))
        self.overall.setValue(int(overall_progress(self.model.jobs) * 1000))
        elapsed = time.monotonic() - self._batch_started
        eta = eta_seconds([job for job in self.model.jobs if job.id in self._timed_ids], elapsed)
        completed = sum(job.status in TERMINAL for job in self.model.jobs)
        active = next((job for job in self.model.jobs if job.id == self._active_id), None)
        phase = (
            M.PREPARING if active is None else M.phase_text(active.status.value, active.progress)
        )
        self.status.setText(
            M.FILE_COUNT.format(
                current=min(completed + 1, len(self.model.jobs)), total=len(self.model.jobs)
            )
            + " | "
            + phase
            + " | "
            + (M.ESTIMATING if eta is None else M.ETA.format(time=M.time_label(eta)))
        )

    @Slot()
    def _background_finished(self) -> None:
        self._refresh()
        if self.closing and not any(task.isRunning() for task in self._tasks):
            self.close()

    def _table_clicked(self, index) -> None:
        job = self.model.jobs[index.row()]
        if index.column() == 5 and job.outputs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(job.outputs[0].parent)))

    def _table_details(self, index) -> None:
        job = self.model.jobs[index.row()]
        if job.failure:
            self.show_error(job.failure, filename=job.source.name)

    def open_output(self) -> None:
        folder = next(
            (job.outputs[0].parent for job in self.model.jobs if job.outputs), self.output_dir
        )
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def run_selftest(self) -> None:
        if not self.ready or self.running or not self.model_choice.currentData():
            return
        worker = SelfTestWorker(self.paths, self.model_choice.currentData())
        self._tasks.append(worker)
        worker.result.connect(self._selftest_result)
        worker.finished.connect(self._background_finished)
        worker.start()
        self._refresh()

    def show_error(
        self, code: FailureCode | None = None, *, text: str = "", filename: str | None = None
    ) -> None:
        if self.interactive:
            ErrorDialog(code, text=text, filename=filename, parent=self).exec()
        else:
            self.status.setText(
                text or M.FAILURE_MESSAGES[code].message if code else text or M.PREPARATION_ERROR
            )

    @Slot()
    def _prepare_failed(self) -> None:
        self.show_error(text=M.PREPARATION_ERROR)

    @Slot()
    def _scan_failed(self) -> None:
        self.show_error(text=M.SCAN_ERROR)

    @Slot(bool)
    def _selftest_result(self, ok: bool) -> None:
        if ok and self.settings.get("installer_test_failed"):
            self.settings["installer_test_failed"] = False
            self._save_settings()
            self._refresh()
        text = M.SELF_TEST_OK if ok else M.SELF_TEST_ERROR
        if self.interactive:
            TextDialog(M.SELF_TEST, (text,), self).exec()
        else:
            self.status.setText(text)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.model_manager and self.model_manager.busy:
            self.model_manager.done(QDialog.DialogCode.Rejected)
        if self.running:
            if not self.closing and CloseDialog(self).exec() != QDialog.DialogCode.Accepted:
                event.ignore()
                return
            self.closing = True
            self.cancel_all()
            event.ignore()
            return
        if any(task.isRunning() for task in self._tasks):
            self.closing = True
            for task in self._tasks:
                task.requestInterruption()
            self.status.setText(M.CLOSING)
            event.ignore()
            return
        if self.ready:
            self._save_settings()
        event.accept()
