"""Qt queue model; local file names are displayed, never sent to diagnostics."""

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionProgressBar

from dusty.core import Job, JobStatus

from . import messages as M

_ROOT_INDEX = QModelIndex()


class QueueModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.jobs: list[Job] = []

    def rowCount(self, parent=_ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(self.jobs)

    def columnCount(self, parent=_ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(M.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return M.HEADERS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        job = self.jobs[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.UserRole:
            return job.progress
        if column == 5 and job.outputs:
            if role == Qt.ItemDataRole.ForegroundRole:
                return QApplication.palette().link()
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setUnderline(True)
                return font
        if role == Qt.ItemDataRole.DisplayRole:
            status = (
                M.GPU_FALLBACK
                if job.gpu_fallback and job.status == JobStatus.DONE
                else M.phase_text(job.status.value, job.progress)
            )
            return (
                job.source.name,
                M.time_label(job.duration_sec) if job.duration_sec else M.UNKNOWN_TIME,
                status,
                M.PERCENT.format(value=int(job.progress * 100)),
                M.time_label(job.elapsed_sec),
                M.OPEN_RESULT if job.outputs else M.EMPTY_CELL,
            )[column]
        if role == Qt.ItemDataRole.ToolTipRole and job.failure:
            error = M.FAILURE_MESSAGES[job.failure]
            return error.message + " " + error.action
        return None

    def set_jobs(self, jobs: list[Job]) -> None:
        self.beginResetModel()
        self.jobs = jobs
        self.endResetModel()

    def update_job(self, job: Job) -> None:
        for row, old in enumerate(self.jobs):
            if old.id == job.id:
                self.jobs[row] = job
                self.dataChanged.emit(self.index(row, 0), self.index(row, len(M.HEADERS) - 1))
                break


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # These public Qt properties are missing from PySide6 6.9.2 stubs.
        bar: Any = QStyleOptionProgressBar()
        bar.rect = option.rect.adjusted(6, 10, -6, -10)
        bar.minimum, bar.maximum = 0, 100
        bar.progress = int(index.data(Qt.ItemDataRole.UserRole) * 100)
        bar.text = M.PERCENT.format(value=bar.progress)
        bar.textVisible = True
        bar.textAlignment = Qt.AlignmentFlag.AlignCenter
        bar.palette = option.palette
        bar.state = option.state
        QApplication.style().drawControl(QStyle.ControlElement.CE_ProgressBar, bar, painter)
