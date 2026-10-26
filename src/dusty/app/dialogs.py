"""Small reviewable dialogs with centralized text and safe default choices."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from dusty.core import FailureCode, Job, JobStatus
from dusty.core.types import CollisionPolicy

from . import messages as M
from .presentation import counts


class TextDialog(QDialog):
    def __init__(self, title: str, paragraphs: tuple[str, ...], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(24, 24, 24, 24)
        self.body.setSpacing(16)
        for text in paragraphs:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.PlainText)
            self.body.addWidget(label)
        self.buttons = QHBoxLayout()
        self.buttons.addStretch()
        self.body.addLayout(self.buttons)

    def button(self, text: str, callback, *, default: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setAccessibleName(text)
        button.setDefault(default)
        button.clicked.connect(callback)
        self.buttons.addWidget(button)
        return button


class GreetingDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.APP_NAME, (M.GREETING,), parent)
        self.setMinimumWidth(240)
        self.button(M.OK, self.accept, default=True)


class AboutDialog(TextDialog):
    def __init__(self, version: str, notices: Callable[[], None], parent=None):
        super().__init__(
            M.ABOUT,
            (
                M.ABOUT_VERSION.format(version=version),
                M.ABOUT_DESCRIPTION,
                M.ABOUT_LICENSE,
                M.REPOSITORY_ADDRESS,
            ),
            parent,
        )
        for label in self.findChildren(QLabel):
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
        self.notices_button = self.button(M.THIRD_PARTY_NOTICES, notices)
        self.button(M.DISMISS, self.accept, default=True)


class NoticesDialog(TextDialog):
    def __init__(self, path: Path, parent=None):
        super().__init__(M.THIRD_PARTY_NOTICES, (), parent)
        self.resize(760, 600)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setAccessibleName(M.THIRD_PARTY_NOTICES)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            text = M.NOTICES_UNAVAILABLE
        self.text.setPlainText(text)
        self.body.insertWidget(0, self.text, 1)
        self.button(M.DISMISS, self.accept, default=True)


class WelcomeDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.WELCOME_TITLE, (M.WELCOME_HELP, M.PRIVACY, M.ACCURACY), parent)
        self.button(M.WELCOME_BUTTON, self.accept, default=True)


class FolderDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.FOLDER_TITLE, (), parent)
        self.recursive = QCheckBox(M.INCLUDE_SUBFOLDERS)
        self.body.insertWidget(0, self.recursive)
        self.button(M.CANCEL, self.reject)
        self.button(M.ADD_FOLDER, self.accept, default=True)


class CollisionDialog(TextDialog):
    def __init__(self, filename: str, parent=None):
        super().__init__(
            M.COLLISION_TITLE,
            (M.EXISTING_TRANSCRIPT.format(name=filename), M.COLLISION_HELP),
            parent,
        )
        self.choices: dict[CollisionPolicy, QRadioButton] = {}
        for index, (key, text) in enumerate(M.COLLISION_CHOICES.items()):
            radio = QRadioButton(text)
            radio.setChecked(key == "keep_both")
            self.choices[cast(CollisionPolicy, key)] = radio
            self.body.insertWidget(2 + index, radio)
        self.apply_all = QCheckBox(M.APPLY_ALL)
        self.apply_all.setChecked(True)
        self.body.insertWidget(5, self.apply_all)
        self.button(M.STOP_BATCH, self.reject)
        self.button(M.CONTINUE, self.accept, default=True)

    def selected_policy(self) -> CollisionPolicy:
        return next(key for key, radio in self.choices.items() if radio.isChecked())


class ResumeDialog(TextDialog):
    def __init__(self, remaining: int, parent=None):
        super().__init__(M.RESUME_TITLE, (M.RESUME_HELP.format(count=remaining),), parent)
        self.button(M.DISCARD, self.reject)
        self.button(M.RESUME, self.accept, default=True)


class SyncDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.SYNC_TITLE, (M.SYNC_HELP,), parent)
        self.button(M.CHOOSE_FOLDER, self.reject, default=True)
        self.button(M.SYNC_CONTINUE, self.accept)


class CloseDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.CLOSE_TITLE, (M.CLOSE_HELP,), parent)
        self.button(M.KEEP_WORKING, self.reject, default=True)
        self.button(M.CLOSE_CONFIRM, self.accept)


class SummaryDialog(TextDialog):
    def __init__(self, jobs: list[Job], parent=None):
        super().__init__(M.SUMMARY, (M.summary_counts(counts(jobs)),), parent)
        failed = [job for job in jobs if job.status == JobStatus.FAILED]
        if failed:
            self.body.insertWidget(1, QLabel(M.FAILED_FILES))
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setMaximumHeight(200)
            content = QWidget()
            layout = QVBoxLayout(content)
            for job in failed:
                reason = (
                    M.FAILURE_MESSAGES[job.failure].message if job.failure else M.PREPARATION_ERROR
                )
                label = QLabel(M.NAMED_FAILURE.format(name=job.source.name, reason=reason))
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setWordWrap(True)
                layout.addWidget(label)
            area.setWidget(content)
            self.body.insertWidget(2, area)
        self.retry = self.button(M.RETRY, lambda: self.done(2))
        self.retry.setEnabled(bool(failed))
        self.dismiss = self.button(
            M.DISMISS, self.accept, default=not any(job.status == JobStatus.DONE for job in jobs)
        )
        if not any(job.status == JobStatus.DONE for job in jobs):
            self.dismiss.setObjectName("primaryButton")
        self.open_folder = self.button(
            M.OPEN_FOLDER, lambda: None, default=any(job.status == JobStatus.DONE for job in jobs)
        )
        self.open_folder.setVisible(any(job.status == JobStatus.DONE for job in jobs))
        self.open_folder.setObjectName("primaryButton")


class ErrorDialog(TextDialog):
    def __init__(
        self,
        code: FailureCode | None = None,
        *,
        text: str = "",
        filename: str | None = None,
        parent=None,
    ):
        reason = text or (M.FAILURE_MESSAGES[code].message if code else M.PREPARATION_ERROR)
        message = M.NAMED_FAILURE.format(name=filename, reason=reason) if filename else reason
        super().__init__(M.ERROR_TITLE, (message,), parent)
        self.button(M.OK, self.accept, default=True)


class ChoiceDelegate(QStyledItemDelegate):
    """Use Qt's item view so disabled model/task entries are visibly unavailable."""
