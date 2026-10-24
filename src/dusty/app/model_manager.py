"""Local model management; networking belongs only to the isolated CLI child."""

import json
import shutil
import threading
import time
from collections.abc import Callable

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry
from dusty.platform.win_process import run_job_process
from dusty.runtime_paths import RuntimePaths, resolve_fetch_command
from dusty.work_area import linked

from . import messages as M
from .dialogs import TextDialog

VOICE_ID = "silero-vad"


def model_name(model_id: str) -> str:
    return M.VOICE_MODEL if model_id == VOICE_ID else M.MODEL_TECHNICAL[model_id]


def format_size(size_bytes: int) -> str:
    """Decimal download units; never wrap a number away from its unit."""
    large = round(size_bytes / 1_000_000, 1) >= 1000
    return M.MODEL_SIZE.format(
        value=size_bytes / (1_000_000_000 if large else 1_000_000),
        unit=M.GIGABYTES if large else M.MEGABYTES,
    )


def model_files(registry: ModelRegistry) -> dict[str, tuple[str, int]]:
    result = {
        key: (item.file_name, item.size_bytes) for key, item in registry.manifest.models.items()
    }
    result[VOICE_ID] = (registry.manifest.vad_file_name, registry.manifest.vad_size_bytes)
    return result


def inspect_models(registry: ModelRegistry) -> dict[str, str]:
    statuses = {}
    for key in model_files(registry):
        try:
            registry.vad_path() if key == VOICE_ID else registry.model_path(key)
            statuses[key] = "installed"
        except ModelMissing:
            statuses[key] = "not_installed"
        except (ModelCorrupt, OSError):
            statuses[key] = "damaged"
    return statuses


class ModelWorker(QThread):
    progress = Signal(object)
    result = Signal(object)

    def __init__(
        self,
        registry: ModelRegistry,
        paths: RuntimePaths,
        *,
        action: str,
        ids: tuple[str, ...] = (),
        command: list[str] | None = None,
        selected: str | None = None,
        voice_in_use: bool = True,
    ):
        super().__init__()
        self.registry, self.paths = registry, paths
        self.action, self.ids = action, ids
        self.command = command if command is not None else resolve_fetch_command()
        self.selected, self.voice_in_use = selected, voice_in_use
        self.cancelled = threading.Event()
        self.pids: list[int] = []
        self.failure: str | None = None
        self.failed_id: str | None = None

    def requestInterruption(self) -> None:
        self.cancelled.set()
        super().requestInterruption()

    def run(self) -> None:
        try:
            if linked(self.paths.models_dir):
                raise ValueError("Linked model folder")
            if self.action == "download":
                for key in self.ids:
                    if self.cancelled.is_set():
                        self.failure = "CANCELLED"
                        break
                    self.failed_id = key
                    events: list[str] = []
                    last_emit = [0.0]

                    def receive(
                        line: str,
                        key: str = key,
                        events: list[str] = events,
                        last_emit: list[float] = last_emit,
                    ) -> None:
                        try:
                            event = json.loads(line)
                            name = event["event"]
                            pid = event["pid"]
                            if type(pid) is not int or pid <= 0:
                                raise ValueError
                            if pid not in self.pids:
                                self.pids.append(pid)
                            if name in {"downloading", "verifying", "complete", "verified"}:
                                done, total = event["bytes"], event["total"]
                                if (
                                    type(done) is not int
                                    or type(total) is not int
                                    or not 0 <= done <= total
                                ):
                                    raise ValueError
                                if total != model_files(self.registry)[key][1]:
                                    raise ValueError
                                events.append(name)
                                now = time.monotonic()
                                if (
                                    name != "downloading"
                                    or done == total
                                    or now - last_emit[0] >= 0.1
                                ):
                                    self.progress.emit(
                                        {"id": key, "event": name, "bytes": done, "total": total}
                                    )
                                    last_emit[0] = now
                            elif name in {"error", "cancelled"} and event.get("code") in {
                                *M.FETCH_ERRORS,
                                "CANCELLED",
                            }:
                                self.failure = event["code"]
                            else:
                                raise ValueError
                        except (ValueError, KeyError, TypeError):
                            self.failure = "PROTOCOL"

                    process = run_job_process(
                        self.command
                        + [
                            "download",
                            "--id",
                            key,
                            "--dest",
                            str(self.paths.models_dir),
                            "--manifest",
                            str(self.paths.resources_dir / "models.json"),
                        ],
                        on_stdout=receive,
                        cancel=self.cancelled,
                    )
                    if process.cancelled or self.cancelled.is_set():
                        # The Windows job terminates the child. Clean only its
                        # manifest-owned partial after all child handles close.
                        part = self.paths.models_dir / (
                            model_files(self.registry)[key][0] + ".part"
                        )
                        if not linked(part):
                            part.unlink(missing_ok=True)
                        self.failure = "CANCELLED"
                    elif process.exit_code or "complete" not in events:
                        self.failure = self.failure or "PROTOCOL"
                    if self.failure:
                        break
                    self.registry._verified.pop(
                        self.registry.directory / model_files(self.registry)[key][0], None
                    )
            elif self.action == "delete":
                key = self.ids[0]
                path = self.registry.directory / model_files(self.registry)[key][0]
                if linked(path):
                    raise ValueError("Model symlink")
                path.unlink(missing_ok=True)
                self.registry._verified.pop(path, None)
            else:
                self.registry._verified.clear()
        except (OSError, ValueError):
            self.failure = "DELETE" if self.action == "delete" else "START_FAILED"
        try:
            statuses = inspect_models(self.registry)
        except (OSError, ValueError):
            statuses = {key: "damaged" for key in model_files(self.registry)}
            self.failure = self.failure or "IO"
        if self.failure == "MISMATCH" and self.failed_id:
            statuses[self.failed_id] = "damaged"
        self.result.emit({"statuses": statuses, "error": self.failure, "action": self.action})


class DownloadDialog(TextDialog):
    def __init__(self, ids: tuple[str, ...], registry: ModelRegistry, parent=None):
        total = sum(model_files(registry)[key][1] for key in ids)
        super().__init__(
            M.DOWNLOAD_TITLE,
            (
                M.DOWNLOAD_CONFIRM.format(
                    names=M.DOWNLOAD_NAMES_JOIN.join(model_name(key) for key in ids),
                    size=format_size(total),
                ),
            ),
            parent,
        )
        self.button(M.CANCEL, self.reject)
        self.button(M.DOWNLOAD, self.accept, default=True)


class ModelManager(TextDialog):
    models_changed = Signal(object)

    def __init__(
        self,
        registry: ModelRegistry,
        paths: RuntimePaths,
        parent=None,
        *,
        selected: Callable[[], str | None] = lambda: None,
        voice_in_use: Callable[[], bool] = lambda: True,
        recommended: str = "small",
        focus_id: str | None = None,
        command: list[str] | None = None,
        track_worker: Callable[[QThread], None] = lambda _: None,
    ):
        super().__init__(M.MODEL_MANAGER, (), parent)
        self.resize(940, 680)
        self.registry, self.paths, self.command = registry, paths, command
        self.selected, self.voice_in_use, self.recommended = selected, voice_in_use, recommended
        self.track_worker = track_worker
        self.worker: ModelWorker | None = None
        self.workers: list[ModelWorker] = []
        self._closing = False
        self.statuses = {key: "not_installed" for key in model_files(registry)}
        self.table = QTableWidget(len(self.statuses), 4)
        self.table.setHorizontalHeaderLabels(M.MANAGER_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setTabKeyNavigation(False)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(88)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(3, 115)
        self.ids = tuple(self.statuses)
        for row, key in enumerate(self.ids):
            label = model_name(key)
            if key == recommended:
                label = M.RECOMMENDED.format(name=label)
            title = QTableWidgetItem()
            title.setData(Qt.ItemDataRole.UserRole, key)
            self.table.setItem(row, 0, title)
            cell = QWidget()
            cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout = QVBoxLayout(cell)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(1)
            for index, text in enumerate((label, M.MODEL_QUALITY[key], M.MODEL_NOTE[key])):
                line = QLabel(text)
                line.setTextFormat(Qt.TextFormat.PlainText)
                font = line.font()
                font.setBold(index == 0)
                if index == 2:
                    font.setPointSizeF(max(8, font.pointSizeF() - 1))
                line.setFont(font)
                layout.addWidget(line)
            self.table.setCellWidget(row, 0, cell)
            self.table.setItem(row, 1, QTableWidgetItem(M.MODEL_BEST_FOR[key]))
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(format_size(model_files(registry)[key][1])),
            )
            self.table.setItem(row, 3, QTableWidgetItem(M.MODEL_STATUSES["not_installed"]))
        self.body.insertWidget(0, self.table, 1)
        self.free_space = QLabel()
        self.message = QLabel(M.VERIFYING_MODELS)
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        self.progress_text = QLabel()
        self.body.insertWidget(1, self.free_space)
        self.body.insertWidget(2, self.message)
        self.body.insertWidget(3, self.progress)
        self.body.insertWidget(4, self.progress_text)
        self.review_notice = QLabel(M.MODEL_REVIEW)
        self.review_notice.setWordWrap(True)
        self.body.insertWidget(1, self.review_notice)
        self.download_button = self.button(M.DOWNLOAD, self.download)
        self.cancel_button = self.button(M.CANCEL_DOWNLOAD, self.cancel)
        self.delete_button = self.button(M.DELETE_MODEL, self.delete)
        self.verify_button = self.button(M.VERIFY_ALL, self.verify_all)
        self.done_button = self.button(M.DISMISS, self.accept, default=True)
        self.table.itemSelectionChanged.connect(self._refresh)
        self.table.selectRow(self.ids.index(focus_id) if focus_id in self.ids else 0)
        self._refresh()
        QTimer.singleShot(0, lambda: self._start("scan"))

    @property
    def busy(self) -> bool:
        return self.worker is not None

    def selected_id(self) -> str:
        return self.ids[max(0, self.table.currentRow())]

    def _refresh(self) -> None:
        key = self.selected_id()
        state = self.statuses[key]
        for row, item in enumerate(self.ids):
            content = self.table.cellWidget(row, 0)
            if content is not None:
                role = (
                    QPalette.ColorRole.HighlightedText
                    if row == self.table.currentRow()
                    else QPalette.ColorRole.WindowText
                )
                for label in content.findChildren(QLabel):
                    label.setForegroundRole(role)
            cell = self.table.item(row, 3)
            assert cell is not None
            cell.setText(M.MODEL_STATUSES[self.statuses[item]])
        self.download_button.setText(M.DOWNLOAD_AGAIN if state == "damaged" else M.DOWNLOAD)
        self.download_button.setEnabled(not self.busy and state != "installed")
        self.verify_button.setEnabled(not self.busy and "installed" in self.statuses.values())
        self.cancel_button.setEnabled(bool(self.worker and self.worker.action == "download"))
        self.delete_button.setEnabled(not self.busy and state in {"installed", "damaged"})
        nearest = self.paths.models_dir
        while not nearest.exists() and nearest.parent != nearest:
            nearest = nearest.parent
        try:
            self.free_space.setText(
                M.FREE_SPACE.format(gb=shutil.disk_usage(nearest).free / 1_000_000_000)
            )
        except OSError:
            self.free_space.setText(M.FREE_SPACE_UNKNOWN)

    def _start(self, action: str, ids: tuple[str, ...] = ()) -> None:
        if self.busy:
            return
        worker = ModelWorker(
            self.registry,
            self.paths,
            action=action,
            ids=ids,
            command=self.command,
            selected=self.selected(),
            voice_in_use=self.voice_in_use(),
        )
        self.worker = worker
        self.workers.append(worker)
        self.track_worker(worker)
        worker.progress.connect(self._progress)
        worker.result.connect(self._result)
        worker.finished.connect(self._finished)
        self.message.setText(M.VERIFYING_MODELS if action in {"verify", "scan"} else M.EMPTY_CELL)
        self._refresh()
        worker.start()

    def verify_all(self) -> None:
        self._start("verify")

    def download(self) -> None:
        if self.busy or not self.download_button.isEnabled():
            return
        key = self.selected_id()
        ids: tuple[str, ...] = (key,)
        # The default silence option requires this same bundled-manifest asset.
        if key != VOICE_ID and self.voice_in_use() and self.statuses[VOICE_ID] != "installed":
            ids += (VOICE_ID,)
        if DownloadDialog(ids, self.registry, self).exec() == QDialog.DialogCode.Accepted:
            self.progress.setValue(0)
            self.progress.show()
            self._start("download", ids)

    def cancel(self) -> None:
        if self.worker:
            self.worker.requestInterruption()

    def delete(self) -> None:
        if self.busy or not self.delete_button.isEnabled():
            return
        key = self.selected_id()
        text = (
            M.DELETE_SELECTED.format(name=model_name(key))
            if key == self.selected()
            else M.DELETE_VOICE.format(name=model_name(key))
            if key == VOICE_ID and self.voice_in_use()
            else M.DELETE_CONFIRM.format(name=model_name(key))
        )
        confirm = TextDialog(M.DELETE_TITLE, (text,), self)
        confirm.button(M.CANCEL, confirm.reject, default=True)
        confirm.button(M.DELETE_MODEL, confirm.accept)
        if confirm.exec() == QDialog.DialogCode.Accepted:
            self._start("delete", (key,))

    @Slot(object)
    def _progress(self, event: dict) -> None:
        key = event["id"]
        self.statuses[key] = "downloading"
        percent = int(100 * event["bytes"] / max(1, event["total"]))
        self.progress.setValue(percent)
        self.progress_text.setText(
            M.DOWNLOAD_PROGRESS.format(
                done=format_size(event["bytes"]), total=format_size(event["total"])
            )
        )
        self.message.setText(
            M.VERIFYING_DOWNLOAD
            if event["event"] == "verifying"
            else M.DOWNLOADING_MODEL.format(name=model_name(key))
        )
        self._refresh()

    @Slot(object)
    def _result(self, result: dict) -> None:
        self.statuses = result["statuses"]
        error = result["error"]
        self.message.setText(
            M.DOWNLOAD_PAUSED
            if error == "CANCELLED"
            else M.FETCH_ERRORS[error]
            if error
            else M.DOWNLOAD_FINISHED
            if result["action"] == "download"
            else M.MODEL_DELETED
            if result["action"] == "delete"
            else M.MODELS_READY
            if result["action"] == "verify"
            and any(state == "installed" for state in self.statuses.values())
            else M.EMPTY_CELL
        )
        self.progress.hide()
        self.progress_text.clear()
        self.models_changed.emit(dict(self.statuses))
        self._refresh()

    @Slot()
    def _finished(self) -> None:
        self.worker = None
        self._refresh()
        if self._closing:
            super().accept()

    def done(self, result: int) -> None:
        if self.busy:
            self._closing = True
            self.cancel()
        else:
            super().done(result)

    def closeEvent(self, event) -> None:
        if self.busy:
            self._closing = True
            self.cancel()
            event.ignore()
        else:
            event.accept()
