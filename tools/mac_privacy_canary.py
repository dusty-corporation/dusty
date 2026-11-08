"""Audit what Dusty writes on macOS for sensitive canary strings (P32).

    PYTHONPATH=src python tools/mac_privacy_canary.py --out build/canary/run-1 \
        --bin-dir build/bin --models-dir build/models-dev --app build/mac-app/Dusty.app

Development and acceptance tool only; no network, no sudo, no system settings.
Copies of public fixtures (tests/fixtures/audio, public-domain JFK speech) are
placed under a folder and file name that contain unique canary strings, and a
vocabulary hint and output folder carry their own canaries. Dusty then runs
through success, decode failure, model missing, cancel during transcription, a
forced native crash (SIGSEGV sent to whisper-cli), the settings store and the
packaged app. Every child installs Dusty's network guard first.

Afterwards it searches, byte for byte and inside DOCX archives and extended
attributes: everything under the isolated Dusty data folders, new entries in
the per-user temporary folder, new crash reports in
~/Library/Logs/DiagnosticReports, new or changed entries in selected
~/Library folders, the input folders and the unified log for the run window.
It reports every hit for the canaries and for transcript words and classifies
it as by design (queue state, settings, the chosen transcript outputs) or as a
finding. Output file metadata (DOCX core properties, zip entry dates, xattrs)
is recorded too. Results: <out>/results.json and <out>/summary.md.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)  # the venv interpreter
TOOL_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}
FIXTURES = ROOT / "tests/fixtures/audio"
TRANSCRIPT_WORDS = ("Americans", "fellow", "country")
FORMATS = ("txt", "srt", "vtt", "json", "docx")
MAX_SCAN = 64 * 1024 * 1024  # bytes; larger changed files (model copies, caches) are skipped
LIBRARY_FOLDERS = (
    "Library/Logs/DiagnosticReports",
    "Library/Preferences",
    "Library/Caches",
    "Library/Saved Application State",
    "Library/HTTPStorages",
    "Library/Application Support/CrashReporter",
)
# Where a canary may legitimately appear, as documented in docs/privacy.md.
BY_DESIGN = {
    "state/queue.json": "unfinished batch state: recording/output paths and hints (documented)",
    "settings.json": "settings: output folder and vocabulary hints (documented)",
    "settings.json.corrupt-": "renamed unreadable settings keep the same content (documented)",
    "output/": "the user's chosen transcripts",
}

CHILD_PRELUDE = r"""
import json, os, sys, threading, time
from pathlib import Path
from dusty.privacy.network_guard import install_guard
install_guard()
"""

# Drives the real MainWindow through its startup, batch and dialogs, unattended.
# argv: mode, recording, output folder, hint. Modes:
#   batch          run a batch, then dismiss the summary (queue state checked before
#                  and after)
#   close          close the window during transcription, confirming the close
#                  dialog (queue state must remain for resume)
#   discard        start with saved state and choose Discard in the resume dialog
#   clear-history  resume saved state, cancel, then use Tools > Clear history
#   idle           start and stay idle until stopped (no batch)
# Every observation is printed as one JSON line starting with "GUI ".
# The welcome gate is satisfied by settings written before start (a saved output
# folder), as for a returning user. Unknown modal dialogs are rejected after 20 s
# and reported, so nothing waits for a person. File dialogs are not driven: with
# real Cocoa the native panel runs its own modal loop in which Qt timers do not
# fire, so it cannot be closed unattended without UI scripting (Accessibility
# permission, a system setting).
GUI_DRIVER = r"""
import json, os, sys, time
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QDialog
mode, source, out, hint = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
app = QApplication([sys.argv[0]])
from dusty.app import messages as M
from dusty.app.dialogs import CloseDialog, ResumeDialog, SummaryDialog
from dusty.app.theme import apply_theme
from dusty.app.window import MainWindow
from dusty.core import JobStatus
apply_theme(app)
window = MainWindow()
state = window.paths.user_dir / "state/queue.json"
flags = {"started": False, "acted": False, "seen": {}, "dialogs": []}
def report(**values):
    values.update(mode=mode, queue_state_exists=state.exists())
    print("GUI " + json.dumps(values, default=str), flush=True)
def finish(code=0):
    report(event="finish", dialogs=flags["dialogs"])
    QTimer.singleShot(200, lambda: app.exit(code))
def clear_history_action():
    for action in window.findChildren(QAction):
        if action.text().replace("&", "") == M.CLEAR_HISTORY:
            return action
    return None
def watch():
    modal = app.activeModalWidget()
    if modal is not None:
        name = type(modal).__name__
        if id(modal) not in flags["seen"]:
            flags["dialogs"].append({"dialog": name})
        first = flags["seen"].setdefault(id(modal), time.monotonic())
        if isinstance(modal, SummaryDialog):
            report(event="summary", jobs=[j.status.value for j in window.model.jobs])
            if mode == "clear-history":
                action = clear_history_action()
                report(
                    event="clear-history-action",
                    found=action is not None,
                    enabled=bool(action and action.isEnabled()),
                    running=window.running,
                )
                if action is not None:
                    action.trigger()
                report(event="after-clear-history")
            modal.done(QDialog.DialogCode.Rejected)
            QTimer.singleShot(500, lambda: (report(event="after-dismiss"), finish()))
        elif isinstance(modal, CloseDialog):
            modal.done(QDialog.DialogCode.Accepted)
        elif isinstance(modal, ResumeDialog):
            report(event="resume-offered")
            if mode == "discard":
                modal.done(QDialog.DialogCode.Rejected)
                QTimer.singleShot(500, lambda: (report(event="after-discard"), finish()))
            else:
                modal.done(QDialog.DialogCode.Accepted)
        elif time.monotonic() - first > 20:
            report(event="unexpected-dialog", dialog=name, text=modal.windowTitle())
            modal.done(QDialog.DialogCode.Rejected)
        return
    if not window.ready or flags["acted"]:
        if mode == "close" and flags["acted"] and not window.isVisible():
            report(event="closed")
            finish()
        return
    if mode == "idle":
        flags["acted"] = True
        report(event="ready", installed=list(window.installed), gpu_ok=window.vulkan_ok)
        return
    if mode in ("discard", "clear-history"):
        flags["acted"] = True  # the startup resume dialog drives these modes
        if mode == "clear-history":
            def cancel_when_transcribing():
                if any(j.status == JobStatus.TRANSCRIBING for j in window.model.jobs):
                    report(event="cancel-all")
                    window.cancel_all()
                else:
                    QTimer.singleShot(100, cancel_when_transcribing)
            cancel_when_transcribing()
        return
    if not flags["started"]:
        flags["started"] = True
        window.output_dir = out  # one folder per scenario, so names never collide
        window.prompt.setPlainText(hint)
        for box in window.formats.values():
            box.setChecked(True)
        window.add_paths([source])
        return
    if window.model.rowCount() == 1 and not (window.scanner and window.scanner.isRunning()):
        flags["acted"] = True
        window._refresh()
        window.start_batch()
        report(event="started", running=window.running)
        if mode == "close":
            def close_when_transcribing():
                if any(j.status == JobStatus.TRANSCRIBING for j in window.model.jobs):
                    report(event="closing-mid-batch")
                    window.close()
                else:
                    QTimer.singleShot(100, close_when_transcribing)
            close_when_transcribing()
timer = QTimer()
timer.timeout.connect(watch)
timer.start(100)
# Never wait for a person: a scenario that has not finished in time fails.
QTimer.singleShot(180000, lambda: (report(event="timeout"), app.exit(3)))
window.show()
QTimer.singleShot(0, window.initialize)
sys.exit(app.exec())
"""

CHILD_BODIES = {
    "gui": GUI_DRIVER,
    "devcli": r"""
from dusty.devcli import main
sys.exit(main(sys.argv[1:]))
""",
    # Coordinator path with a cancel or a fault, the way the GUI drives a batch.
    "coordinator": r"""
from dusty.core import BatchOptions, JobStatus
from dusty.models import ModelRegistry, load_manifest
from dusty.privacy.logging import configure_logger
from dusty.queue import Coordinator, cleanup_orphaned_work
from dusty.queue.scanning import scan_inputs
from dusty.runtime_paths import resolve_paths
mode, source, out, prompt = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
paths = resolve_paths()
configure_logger(paths.user_dir)
cleanup_orphaned_work(paths.user_dir / "work")
registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
jobs = list(scan_inputs([source]).jobs)
options = BatchOptions(model_id="tiny", output_dir=out, formats=("txt", "docx"),
                       backend="cpu", threads=4, prompt=prompt, vad=True)
cancel = threading.Event()
def changed(job):
    if job.status == JobStatus.TRANSCRIBING:
        print("TRANSCRIBING", flush=True)
        if mode == "cancel" and not cancel.is_set():
            threading.Timer(1.5, cancel.set).start()
Coordinator(paths, registry).run_batch(jobs, options, cancel=cancel, on_change=changed)
for job in jobs:
    print(job.status.value, job.failure.value if job.failure else "OK", flush=True)
""",
    "settings": r"""
from dusty.queue.storage import load_settings, save_settings
from dusty.runtime_paths import resolve_paths
hint, out = sys.argv[1], sys.argv[2]
path = resolve_paths().user_dir / "settings.json"
settings = load_settings(path)
settings.update(prompt=hint, output_dir=out, model_id="tiny")
save_settings(path, settings)
# An unreadable settings file is renamed, not deleted; its content is kept.
path.write_text('{"schema_version": 99, "prompt": "' + hint + '"}', encoding="utf-8")
settings = load_settings(path)
settings.update(prompt=hint, output_dir=out, model_id="tiny")
save_settings(path, settings)
print("settings done")
""",
}


class CanaryError(RuntimeError):
    """The audit itself could not run."""


def make_canaries() -> dict[str, str]:
    token = secrets.token_hex(4)
    return {
        "file": f"DustyCanaryFile{token}",
        "folder": f"DustyCanaryFolder{token}",
        "hint": f"DustyCanaryHint{token}",
        "output": f"DustyCanaryOut{token}",
    }


def snapshot(root: Path, depth: int = 3) -> dict[str, float]:
    """Relative path to modification time, bounded in depth, never following links."""
    found: dict[str, float] = {}
    if not root.is_dir():
        return found
    base = len(root.parts)
    for directory, folders, files in os.walk(root, followlinks=False):
        here = Path(directory)
        if len(here.parts) - base >= depth:
            folders[:] = []
        for name in folders + files:
            path = here / name
            try:
                found[path.relative_to(root).as_posix()] = path.lstat().st_mtime
            except OSError:
                continue
    return found


def changed_entries(before: dict[str, float], after: dict[str, float]) -> list[str]:
    return sorted(name for name, mtime in after.items() if before.get(name) != mtime)


def needles(canaries: dict[str, str]) -> dict[str, list[bytes]]:
    """Each canary and transcript word as UTF-8 and UTF-16LE, as given and lower case."""
    result = {}
    for label, text in list(canaries.items()) + [(f"word:{w}", w) for w in TRANSCRIPT_WORDS]:
        result[label] = [
            text.encode(),
            text.lower().encode(),
            text.encode("utf-16-le"),
            text.lower().encode("utf-16-le"),
        ]
    return result


def search_bytes(data: bytes, patterns: dict[str, list[bytes]]) -> list[str]:
    return sorted(label for label, forms in patterns.items() if any(f in data for f in forms))


def file_hits(path: Path, patterns: dict[str, list[bytes]]) -> list[str]:
    """Hits in the content, inside a zip archive and in xattr values (not the name)."""
    hits: set[str] = set()
    try:
        data = path.read_bytes()
    except OSError:
        return sorted(hits)
    hits.update(search_bytes(data, patterns))
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    hits.update(search_bytes(archive.read(name), patterns))
        except (zipfile.BadZipFile, OSError):
            pass
    for name in xattr_names(path):
        hits.update(search_bytes(xattr_value(path, name), patterns))
    return sorted(hits)


XATTR_NOFOLLOW = 0x0001


def _libc():
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)
    libc.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    libc.listxattr.restype = ctypes.c_ssize_t
    libc.getxattr.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint32,
        ctypes.c_int,
    ]
    libc.getxattr.restype = ctypes.c_ssize_t
    return libc


def xattr_names(path: Path) -> list[str]:
    """Extended attribute names (Python on macOS has no os.listxattr)."""
    import ctypes

    libc, raw = _libc(), os.fsencode(path)
    size = libc.listxattr(raw, None, 0, XATTR_NOFOLLOW)
    if size <= 0:
        return []
    buffer = ctypes.create_string_buffer(size)
    size = libc.listxattr(raw, buffer, size, XATTR_NOFOLLOW)
    if size <= 0:
        return []
    return sorted(
        name.decode("utf-8", "replace") for name in buffer.raw[:size].split(b"\0") if name
    )


def xattr_value(path: Path, name: str) -> bytes:
    import ctypes

    libc, raw, key = _libc(), os.fsencode(path), name.encode()
    size = libc.getxattr(raw, key, None, 0, 0, XATTR_NOFOLLOW)
    if size <= 0:
        return b""
    buffer = ctypes.create_string_buffer(size)
    size = libc.getxattr(raw, key, buffer, size, 0, XATTR_NOFOLLOW)
    return buffer.raw[: max(size, 0)]


def classify(relative: str) -> str:
    for marker, reason in BY_DESIGN.items():
        if marker in relative:
            return "by design: " + reason
    return "FINDING"


def docx_metadata(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        core = archive.read("docProps/core.xml").decode("utf-8")
        names = archive.namelist()
        dates = sorted({info.date_time[:3] for info in archive.infolist()})
        extended = "docProps/app.xml" in names
        document = archive.read("word/document.xml").decode("utf-8")
    return {
        "parts": names,
        "core_properties": core,
        "app_properties_present": extended,
        "zip_entry_dates": [list(date) for date in dates],
        "first_paragraph_is_source_stem": "<w:t" in document
        and document.split("<w:t", 1)[1].split(">", 1)[1].split("<", 1)[0] != "",
    }


def unified_log_hits(started: str, canaries: dict[str, str]) -> list[str]:
    prefix = os.path.commonprefix(list(canaries.values()))
    result = subprocess.run(
        [
            "/usr/bin/log",
            "show",
            "--start",
            started,
            "--style",
            "compact",
            "--info",
            "--predicate",
            f'eventMessage CONTAINS "{prefix}"',
        ],
        env=TOOL_ENV,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()[1:]  # first line is the column header
    return [line[:300] for line in lines if prefix in line and "log run" not in line]


class Audit:
    def __init__(
        self,
        out: Path,
        bin_dir: Path,
        models_dir: Path,
        app: Path | None,
        qt_platform: str = "cocoa",
    ):
        self.out, self.bin_dir, self.models_dir, self.app = out, bin_dir, models_dir, app
        self.canaries = make_canaries()
        self.patterns = needles(self.canaries)
        self.home = Path.home()
        self.tmp = Path(os.environ.get("TMPDIR") or "/var/tmp").resolve()
        self.dev_data = out / "appdata-dev"
        self.app_data = out / "appdata-app"
        self.gui_data = out / "appdata-gui"
        self.qt_platform = qt_platform
        self.inputs = out / "inputs"
        self.runs: list[dict] = []
        self.empty_models = out / "models-empty"

    def place(self, fixture: str, scenario: str) -> Path:
        """Copy a public fixture under a canary folder and canary file name."""
        source = FIXTURES / fixture
        target = (
            self.inputs
            / scenario
            / self.canaries["folder"]
            / f"{self.canaries['file']}{source.suffix}"
        )
        target.parent.mkdir(parents=True)
        shutil.copyfile(source, target)
        return target

    def output_dir(self, scenario: str) -> Path:
        return self.out / "output" / scenario / self.canaries["output"]

    def child(
        self,
        body: str,
        args: list[str],
        *,
        data: Path,
        models: Path | None = None,
        on_line=None,
        timeout: float = 900,
        extra: dict[str, str] | None = None,
    ) -> dict:
        script = self.out / "scripts" / f"{body}.py"
        script.parent.mkdir(exist_ok=True)
        script.write_text(CHILD_PRELUDE + CHILD_BODIES[body], encoding="utf-8")
        env = dict(TOOL_ENV)
        env.update(
            HOME=str(self.home),
            LOCALAPPDATA=str(data),
            PYTHONPATH=str(ROOT / "src"),
            DUSTY_BIN_DIR=str(self.bin_dir),
            DUSTY_MODELS_DIR=str(models or self.models_dir),
        )
        if os.environ.get("TMPDIR"):
            env["TMPDIR"] = os.environ["TMPDIR"]
        env.update(extra or {})
        return self.spawn([str(PYTHON), str(script), *args], env, on_line=on_line, timeout=timeout)

    def spawn(
        self, argv: list[str], env: dict[str, str], *, on_line=None, on_start=None, timeout=900
    ) -> dict:
        started = time.monotonic()
        process = subprocess.Popen(
            argv,
            env=env,
            cwd=self.out,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if on_start:
            on_start(process.pid)
        lines = []
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line.rstrip())
            if on_line:
                on_line(line.rstrip())
            if time.monotonic() - started > timeout:
                process.kill()
                break
        code = process.wait()
        stderr = process.stderr.read() if process.stderr else ""
        return {
            "exit_code": code,
            "stdout_tail": lines[-6:],
            "stderr_tail": stderr.strip().splitlines()[-3:],
            "seconds": round(time.monotonic() - started, 1),
        }

    def record(self, name: str, outcome: dict, expected: str) -> None:
        outcome.update(name=name, expected=expected)
        self.runs.append(outcome)
        print(f"ran {name}: exit {outcome['exit_code']} {outcome['stdout_tail'][-1:]}")

    def devcli(self, scenario: str, fixture: str, *, models: Path | None, expected: str) -> None:
        source = self.place(fixture, scenario)
        args = ["transcribe", str(source), "--out", str(self.output_dir(scenario))]
        args += ["--model", "tiny", "--backend", "cpu", "--vad", "--prompt", self.canaries["hint"]]
        for value in FORMATS:
            args += ["--format", value]
        self.record(
            scenario, self.child("devcli", args, data=self.dev_data, models=models), expected
        )

    def coordinator(self, scenario: str, mode: str, expected: str) -> None:
        source = self.place("vad/mostly-silence-10min.m4a", scenario)
        crashed: list[int] = []

        def on_line(line: str) -> None:
            if mode == "fault" and line == "TRANSCRIBING" and not crashed:
                time.sleep(1.0)
                for pid in self.whisper_pids():
                    os.kill(pid, signal.SIGSEGV)
                    crashed.append(pid)

        args = [mode, str(source), str(self.output_dir(scenario)), self.canaries["hint"]]
        outcome = self.child("coordinator", args, data=self.dev_data, on_line=on_line)
        outcome["signalled_pids"] = crashed
        self.record(scenario, outcome, expected)

    def whisper_pids(self, executable: Path | None = None) -> list[int]:
        """whisper-cli itself only: the lifeline's arguments also name it, so anchor
        the pattern at the start of the command line (argv[0])."""
        target = executable or self.bin_dir / "cpu/whisper-cli"
        pattern = "^" + str(target).replace(".", "\\.")
        result = subprocess.run(
            ["/usr/bin/pgrep", "-f", pattern], env=TOOL_ENV, capture_output=True, text=True
        )
        return [int(value) for value in result.stdout.split()]

    def settings(self) -> None:
        args = [self.canaries["hint"], str(self.output_dir("settings"))]
        outcome = self.child("settings", args, data=self.dev_data)
        self.record("settings-store", outcome, "settings saved; corrupt copy renamed")

    def app_runs(self) -> None:
        assert self.app is not None
        models = self.app_data / "Dusty/models"
        models.mkdir(parents=True, mode=0o700)
        os.chmod(self.app_data / "Dusty", 0o700)
        os.link(self.models_dir / "ggml-tiny.bin", models / "ggml-tiny.bin")
        env = dict(TOOL_ENV, HOME=str(self.home), LOCALAPPDATA=str(self.app_data))
        if os.environ.get("TMPDIR"):
            env["TMPDIR"] = os.environ["TMPDIR"]
        executable = str(self.app / "Contents/MacOS/Dusty")
        for scenario, fixture, expected in (
            ("app-success", "formats/jfk.m4a", "done OK"),
            ("app-decode-failure", "bad/corrupt.mp3", "failed DECODE_ERROR"),
        ):
            source = self.place(fixture, scenario)
            argv = [executable, "--headless-batch", str(source)]
            argv += ["--out", str(self.output_dir(scenario))]
            self.record(scenario, self.spawn(argv, env), expected)
        self.record(
            "app-selftest", self.spawn([executable, "--self-test", "--backend", "cpu"], env), "OK"
        )
        # Packaged fault paths: a native crash, then the app itself crashing mid-batch.
        bin_dir = self.app / "Contents/Helpers/bin"
        for scenario, victim, expected in (
            ("app-native-crash", "whisper", "failed ENGINE_ERROR"),
            ("app-crash", "app", "killed by SIGABRT"),
        ):
            source = self.place("vad/mostly-silence-10min.m4a", scenario)
            argv = [executable, "--headless-batch", str(source)]
            argv += ["--out", str(self.output_dir(scenario))]
            outcome = self.spawn_and_crash(argv, env, bin_dir, victim)
            if victim == "app":
                outcome["work_after_crash"] = self.work_entries(self.app_data)
            self.record(scenario, outcome, expected)
        # The next start cleans up owned work left by the crash.
        source = self.place("bad/corrupt.mp3", "app-restart")
        argv = [executable, "--headless-batch", str(source)]
        argv += ["--out", str(self.output_dir("app-restart"))]
        outcome = self.spawn(argv, env)
        outcome["work_after_restart"] = self.work_entries(self.app_data)
        self.record("app-restart", outcome, "failed DECODE_ERROR; work folder cleaned")

    def work_entries(self, data: Path) -> list[str]:
        work = data / "Dusty/work"
        return sorted(str(p.relative_to(work)) for p in work.rglob("*")) if work.is_dir() else []

    def spawn_and_crash(self, argv: list[str], env: dict[str, str], bin_dir: Path, victim: str):
        """Start the app, wait until whisper-cli runs, then crash whisper-cli or the app."""
        import threading

        crashed: list[int] = []
        holder: dict = {}

        def watch() -> None:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and not crashed:
                found = [
                    pid
                    for backend in ("cpu", "metal")
                    for pid in self.whisper_pids(bin_dir / backend / "whisper-cli")
                ]
                if found:
                    time.sleep(1.0)
                    targets = found if victim == "whisper" else [holder["pid"]]
                    for pid in targets:
                        os.kill(pid, signal.SIGSEGV if victim == "whisper" else signal.SIGABRT)
                        crashed.append(pid)
                time.sleep(0.1)

        def started(pid: int) -> None:
            holder["pid"] = pid
            threading.Thread(target=watch, daemon=True).start()

        outcome = self.spawn(argv, env, on_start=started)
        outcome["signalled_pids"] = crashed
        return outcome

    def gui_runs(self) -> None:
        """The real window: batch and dismiss, close mid-batch, discard, Clear history."""
        profile = self.gui_data / "Dusty"
        profile.mkdir(parents=True, mode=0o700)
        output = self.output_dir("gui")
        (profile / "settings.json").write_text(
            json.dumps({"schema_version": 1, "welcome_seen": True, "output_dir": str(output)}),
            encoding="utf-8",
        )
        extra = {"LANG": "en_US.UTF-8"}
        if self.qt_platform == "offscreen":
            extra["QT_QPA_PLATFORM"] = "offscreen"
        state = profile / "state/queue.json"
        for scenario, mode, fixture, expected_state in (
            ("gui-batch", "batch", "formats/jfk.m4a", False),
            ("gui-close", "close", "vad/mostly-silence-10min.m4a", True),
            ("gui-discard", "discard", None, False),
            ("gui-close-again", "close", "vad/mostly-silence-10min.m4a", True),
            ("gui-clear-history", "clear-history", None, False),
        ):
            source = self.place(fixture, scenario) if fixture else self.inputs / "unused"
            events: list[dict] = []

            def collect(line: str, events: list[dict] = events) -> None:
                if line.startswith("GUI "):
                    events.append(json.loads(line[4:]))

            target = self.output_dir(scenario) if fixture else output
            args = [mode, str(source), str(target), self.canaries["hint"]]
            outcome = self.child(
                "gui", args, data=self.gui_data, on_line=collect, timeout=300, extra=extra
            )
            outcome["gui_events"] = events
            outcome["queue_state_after"] = state.exists()
            outcome["qt_platform"] = self.qt_platform
            if state.exists():
                outcome["queue_state_canaries"] = file_hits(state, self.patterns)
            outcome["stdout_tail"] = [f"queue state after: {state.exists()}"]
            self.record(
                scenario,
                outcome,
                f"queue state {'kept' if expected_state else 'removed'}",
            )

    def library_roots(self) -> dict[str, Path]:
        roots = {name: self.home / name for name in LIBRARY_FOLDERS}
        roots["TMPDIR"] = self.tmp
        # The per-user cache folder holds the Metal shader cache (com.apple.metal).
        cache = subprocess.run(
            ["/usr/bin/getconf", "DARWIN_USER_CACHE_DIR"],
            env=TOOL_ENV,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if cache:
            roots["DARWIN_USER_CACHE_DIR"] = Path(cache).resolve()
        return roots

    def run(self) -> dict:
        roots = self.library_roots()
        before = {name: snapshot(path) for name, path in roots.items()}
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        self.empty_models.mkdir(parents=True)
        self.devcli("success", "formats/jfk.m4a", models=None, expected="done OK")
        self.devcli("decode-failure", "bad/corrupt.mp3", models=None, expected="DECODE_ERROR")
        self.devcli(
            "model-missing", "formats/jfk.m4a", models=self.empty_models, expected="MODEL_MISSING"
        )
        self.coordinator("cancel", "cancel", "cancelled OK")
        self.coordinator("native-crash", "fault", "failed ENGINE_ERROR")
        self.settings()
        self.gui_runs()
        if self.app:
            self.app_runs()
        time.sleep(15)  # ReportCrash writes crash reports asynchronously
        after = {name: snapshot(path) for name, path in roots.items()}
        return self.search(roots, before, after, started)

    def search(self, roots, before, after, started) -> dict:
        hits: list[dict] = []
        scanned = 0

        def scan(path: Path, location: str, relative: str) -> None:
            nonlocal scanned
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SCAN:
                    return
            except OSError:
                return
            scanned += 1
            found = file_hits(path, self.patterns)
            named = search_bytes(path.name.encode(), self.patterns)
            if found or named:
                hits.append(
                    {
                        "location": location,
                        "path": relative,
                        "hits": found,
                        "name_hits": named,
                        "classification": classify(relative)
                        if location.startswith("dusty data") or location == "output"
                        else "FINDING",
                    }
                )

        for location, base in (
            ("dusty data (dev)", self.dev_data),
            ("dusty data (app)", self.app_data),
            ("dusty data (gui)", self.gui_data),
            ("output", self.out / "output"),
            ("input folders", self.inputs),
        ):
            for path in sorted(base.rglob("*")):
                relative = str(path.relative_to(self.out))
                if location == "output":
                    relative = "output/" + str(path.relative_to(base))
                if location == "input folders":
                    if path.is_file() and path.suffix not in (".m4a", ".mp3"):
                        hits.append(
                            {
                                "location": location,
                                "path": relative,
                                "hits": ["new file beside the recording"],
                                "classification": "FINDING",
                            }
                        )
                    continue
                scan(path, location, relative)
        os_entries: dict[str, list[str]] = {}
        for name, root in roots.items():
            changed = changed_entries(before[name], after[name])
            os_entries[name] = changed
            for relative in changed:
                scan(root / relative, name, relative)
        work_left = {
            label: sorted(str(p.relative_to(data)) for p in (data / "Dusty/work").rglob("*"))
            for label, data in (
                ("dev", self.dev_data),
                ("app", self.app_data),
                ("gui", self.gui_data),
            )
            if (data / "Dusty/work").is_dir()
        }
        return {
            "canaries": self.canaries,
            "transcript_words": TRANSCRIPT_WORDS,
            "runs": self.runs,
            "files_scanned": scanned,
            "hits": hits,
            "os_entries_changed": os_entries,
            "work_left": work_left,
            "unified_log_hits": unified_log_hits(started, self.canaries),
            "metadata": self.metadata(),
            "findings": [hit for hit in hits if hit["classification"] == "FINDING"],
        }

    def metadata(self) -> dict:
        result: dict = {"outputs": {}, "inputs": {}}
        for path in sorted((self.out / "output").rglob("*")):
            if not path.is_file():
                continue
            entry: dict = {"xattrs": xattr_names(path)}
            if path.suffix == ".docx":
                entry["docx"] = docx_metadata(path)
            if path.suffix == ".json":
                entry["json_keys"] = sorted(json.loads(path.read_text(encoding="utf-8")))
            result["outputs"][str(path.relative_to(self.out))] = entry
        for path in sorted(self.inputs.rglob("*")):
            if path.is_file():
                result["inputs"][str(path.relative_to(self.out))] = xattr_names(path)
        info = self.app / "Contents/Info.plist" if self.app else None
        if info and info.is_file():
            import plistlib

            plist = plistlib.loads(info.read_bytes())
            result["app_info_plist"] = {
                key: plist.get(key) for key in ("LSFileQuarantineEnabled", "CFBundleIdentifier")
            }
            result["app_xattrs"] = xattr_names(info.parent.parent)
        return result


def summary_markdown(results: dict) -> str:
    lines = ["# Privacy canary audit", ""]
    lines.append("Canaries: " + ", ".join(f"{k}={v}" for k, v in results["canaries"].items()))
    lines += [
        "",
        "## Runs",
        "",
        "| Scenario | Exit | Last output | Expected |",
        "|---|---|---|---|",
    ]
    for run in results["runs"]:
        last = " ".join(run["stdout_tail"][-1:])
        lines.append(f"| {run['name']} | {run['exit_code']} | {last} | {run['expected']} |")
    lines += ["", f"Files scanned: {results['files_scanned']}", ""]
    lines += [
        "## Hits",
        "",
        "| Location | Path | In content | In file name | Classification |",
        "|---|---|---|---|---|",
    ]
    for hit in results["hits"]:
        lines.append(
            f"| {hit['location']} | {hit['path']} | {', '.join(hit['hits']) or 'none'} | "
            f"{', '.join(hit.get('name_hits', [])) or 'none'} | {hit['classification']} |"
        )
    lines += ["", f"Findings: {len(results['findings'])}", ""]
    lines += ["Unified log lines with a canary: " + str(len(results["unified_log_hits"]))]
    lines += ["Work folders left: " + json.dumps(results["work_left"])]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="New folder for this run")
    parser.add_argument("--bin-dir", type=Path, default=ROOT / "build/bin")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "build/models-dev")
    parser.add_argument("--app", type=Path, help="Built Dusty.app to audit as well")
    parser.add_argument(
        "--qt-platform",
        choices=("cocoa", "offscreen"),
        default="cocoa",
        help="cocoa shows real windows briefly (works unattended); offscreen draws nothing",
    )
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("This audit needs macOS", file=sys.stderr)
        return 2
    if args.out.exists():
        print(f"Refusing existing output folder: {args.out}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)
    audit = Audit(
        args.out.resolve(),
        args.bin_dir.resolve(),
        args.models_dir.resolve(),
        args.app.resolve() if args.app else None,
        args.qt_platform,
    )
    results = audit.run()
    (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(summary_markdown(results), encoding="utf-8")
    print(f"{len(results['findings'])} finding(s); details in {args.out / 'summary.md'}")
    return 1 if results["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
