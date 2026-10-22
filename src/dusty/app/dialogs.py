"""Small reviewable dialogs with centralized text and safe default choices."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from dusty.core import FailureCode, Job, JobStatus

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
        heading = QLabel(title)
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 18px; font-weight: 600")
        self.body.addWidget(heading)
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


class WelcomeDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.WELCOME_TITLE, (M.WELCOME_HELP, M.PRIVACY, M.ACCURACY), parent)
        self.button(M.WELCOME_BUTTON, self.accept, default=True)


class FolderDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.FOLDER_TITLE, (), parent)
        self.recursive = QCheckBox(M.INCLUDE_SUBFOLDERS)
        self.body.insertWidget(1, self.recursive)
        self.button(M.CANCEL, self.reject)
        self.button(M.ADD_FOLDER, self.accept, default=True)


class CollisionDialog(TextDialog):
    def __init__(self, parent=None):
        super().__init__(M.COLLISION_TITLE, (M.COLLISION_HELP,), parent)
        self.choice = QComboBox()
        for key in ("keep_both", "skip", "overwrite"):
            self.choice.addItem(M.COLLISIONS[key], key)
        self.choice.setAccessibleName(M.COLLISION)
        self.apply_all = QCheckBox(M.APPLY_ALL)
        self.apply_all.setChecked(True)
        self.body.insertWidget(2, self.choice)
        self.body.insertWidget(3, self.apply_all)
        self.button(M.STOP_BATCH, self.reject)
        self.button(M.CONTINUE, self.accept, default=True)


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
        super().__init__(M.SUMMARY, (M.SUMMARY_COUNTS.format(**counts(jobs)),), parent)
        self.retry = self.button(M.RETRY, lambda: self.done(2))
        self.retry.setEnabled(any(job.status == JobStatus.FAILED for job in jobs))
        self.open_folder = self.button(M.OPEN_FOLDER, lambda: None)
        self.button(M.DISMISS, self.accept, default=True)


class ErrorDialog(TextDialog):
    def __init__(self, code: FailureCode | None = None, *, text: str = "", parent=None):
        paragraphs = (
            (text,)
            if text
            else (M.FAILURE_MESSAGES[code].message, M.FAILURE_MESSAGES[code].action)
            if code
            else (M.PREPARATION_ERROR,)
        )
        super().__init__(M.ERROR_TITLE, paragraphs, parent)
        self.button(M.OK, self.accept, default=True)
