"""Render synthetic M4 model-management states without downloading any files."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLISH_STATES = {
    "02-no-models-start-hint",
    "22-no-models-vulkan-recommendation",
    "06-all-not-installed",
    "10-delete-confirmation",
    "23-delete-normal-confirmation",
    "21-voice-deletion-confirmation",
    "11-download-consent-with-voice-detection",
    "24-download-consent-gb",
    "12-downloading-progress-and-cancel",
    "13-verifying-download",
    "20-no-selected-model-options-prompt",
    "25-open-installed-models-quiet",
    "26-explicit-verify-complete",
    "27-explicit-verify-empty-quiet",
    "28-voice-silences-label",
}

FINAL_STATES = {
    "06-all-not-installed",
    "08-selected-model-delete-enabled",
    "21-voice-deletion-confirmation",
    "27-explicit-verify-empty-quiet",
}


def render(output: Path, theme: str, *, polish: bool = False, final: bool = False) -> None:
    from dusty.privacy.network_guard import install_guard

    install_guard()
    from PySide6.QtGui import QFont, QRawFont
    from PySide6.QtWidgets import QApplication

    from dusty.app import messages as M
    from dusty.app.dialogs import TextDialog
    from dusty.app.model_manager import DownloadDialog, ModelManager, ModelWorker
    from dusty.app.theme import apply_theme
    from dusty.app.window import MainWindow
    from dusty.app.workers import Prepared
    from dusty.core import Job
    from dusty.runtime_paths import RuntimePaths

    app = QApplication([])
    apply_theme(app, theme)
    if not QRawFont.fromFont(QFont("Segoe UI", 10)).supportsCharacter("A"):
        raise RuntimeError("Screenshot font is unavailable")
    output.mkdir(parents=True, exist_ok=True)
    paths = RuntimePaths(
        ROOT / "build/bin", output / "models", ROOT / "resources", output / "state"
    )
    window = MainWindow(paths, interactive=False)
    window.apply_prepared(
        Prepared((), False, {"schema_version": 1, "theme": theme}, vad_installed=False)
    )
    window.output_dir = None

    def capture(widget, name: str) -> None:
        if final and name not in FINAL_STATES:
            return
        if polish and not final and name not in POLISH_STATES:
            return
        widget.show()
        app.processEvents()
        if not widget.grab().save(str(output / (name + ".png"))):
            raise RuntimeError("Screenshot save failed")

    window._refresh()
    capture(window, "01-no-models-no-output")
    window.output_dir = Path("C:/Transcripts")
    window.model.set_jobs([Job(Path("C:/Recordings/Lecture.wav"), duration_sec=900)])
    window._refresh()
    capture(window, "02-no-models-start-hint")
    if polish:
        window.vulkan_ok = True
        window._refresh()
        capture(window, "22-no-models-vulkan-recommendation")
        window.vulkan_ok = False
        window._refresh()
    statuses = {key: "not_installed" for key in window.registry.manifest.models}
    statuses["tiny"] = statuses["silero-vad"] = "installed"
    window._models_changed(statuses)
    capture(window, "03-installed-no-recommendation-prompt")
    statuses["small"] = "installed"
    window._models_changed(statuses)
    capture(window, "04-recommendation-now-installed")
    window.options_dialog.show()
    capture(window.options_dialog, "05-options-and-model-manager-entry")
    window.options_dialog.hide()

    manager = ModelManager(
        window.registry, paths, window, selected=lambda: "small", recommended="small"
    )
    manager.show()
    deadline = time.monotonic() + 10
    while (not manager.workers or manager.busy) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    if manager.busy or not manager.workers:
        raise RuntimeError("Initial local model scan did not finish")

    def manager_capture(name: str) -> None:
        manager._refresh()
        manager.free_space.setText(M.FREE_SPACE.format(gb=42))
        capture(manager, name)

    manager_capture("06-all-not-installed")
    if polish:
        manager.table.scrollToBottom()
        manager_capture("28-voice-silences-label")
        manager.table.scrollToTop()
        manager.verify_button.click()
        app.processEvents()
        manager_capture("27-explicit-verify-empty-quiet")
    manager.statuses.update(statuses)
    if polish:
        manager_capture("25-open-installed-models-quiet")
        manager._result({"statuses": dict(manager.statuses), "error": None, "action": "verify"})
        manager_capture("26-explicit-verify-complete")
        manager.message.clear()
    manager.statuses["medium"] = "damaged"
    manager.table.selectRow(manager.ids.index("medium"))
    manager_capture("07-damaged-download-again")
    manager.table.selectRow(manager.ids.index("small"))
    manager_capture("08-selected-model-delete-enabled")
    manager.table.selectRow(manager.ids.index("tiny"))
    manager_capture("09-other-model-delete-enabled")
    confirm = TextDialog(
        M.DELETE_TITLE, (M.DELETE_SELECTED.format(name=M.MODEL_TECHNICAL["small"]),), manager
    )
    confirm.button(M.CANCEL, confirm.reject, default=True)
    confirm.button(M.DELETE_MODEL, confirm.accept)
    capture(confirm, "10-delete-confirmation")
    confirm.hide()
    if polish:
        normal = TextDialog(
            M.DELETE_TITLE, (M.DELETE_CONFIRM.format(name=M.MODEL_TECHNICAL["tiny"]),), manager
        )
        normal.button(M.CANCEL, normal.reject, default=True)
        normal.button(M.DELETE_MODEL, normal.accept)
        capture(normal, "23-delete-normal-confirmation")
        normal.hide()
        medium = DownloadDialog(("medium",), window.registry, manager)
        capture(medium, "24-download-consent-gb")
        medium.hide()
    consent = DownloadDialog(("large-v3-turbo-q8_0", "silero-vad"), window.registry, manager)
    capture(consent, "11-download-consent-with-voice-detection")
    consent.hide()

    # A never-started worker models busy controls; no child or network is created.
    manager.worker = ModelWorker(window.registry, paths, action="download")
    manager.table.selectRow(manager.ids.index("large-v3-turbo-q8_0"))
    total = window.registry.manifest.models["large-v3-turbo-q8_0"].size_bytes
    manager.progress.show()
    manager._progress(
        {"id": "large-v3-turbo-q8_0", "event": "downloading", "bytes": total // 3, "total": total}
    )
    manager_capture("12-downloading-progress-and-cancel")
    manager._progress(
        {"id": "large-v3-turbo-q8_0", "event": "verifying", "bytes": total, "total": total}
    )
    manager_capture("13-verifying-download")
    manager.worker = None
    for error, name in (
        ("CANCELLED", "14-cancelled-part-removed"),
        ("MISMATCH", "15-hash-mismatch-damaged"),
        ("DISK_FULL", "16-disk-space-error"),
        ("NETWORK", "17-connection-error"),
    ):
        manager.statuses["large-v3-turbo-q8_0"] = (
            "damaged" if error == "MISMATCH" else "not_installed"
        )
        manager._result({"statuses": manager.statuses, "error": error, "action": "download"})
        manager_capture(name)
    manager.statuses = {key: "not_installed" for key in manager.ids}
    manager.statuses["tiny"] = "installed"
    manager.table.selectRow(manager.ids.index("tiny"))
    manager_capture("18-last-model-delete-enabled")
    manager.worker = ModelWorker(window.registry, paths, action="verify")
    manager.message.setText(M.VERIFYING_MODELS)
    manager_capture("19-verify-all-busy")
    manager.worker = None
    window._models_changed({**statuses, "tiny": "not_installed"})
    window.model_choice.setCurrentIndex(-1)
    window._refresh()
    capture(window, "20-no-selected-model-options-prompt")
    voice_confirm = TextDialog(
        M.DELETE_TITLE, (M.DELETE_VOICE.format(name=M.VOICE_MODEL),), manager
    )
    voice_confirm.button(M.CANCEL, voice_confirm.reject, default=True)
    voice_confirm.button(M.DELETE_MODEL, voice_confirm.accept)
    capture(voice_confirm, "21-voice-deletion-confirmation")
    voice_confirm.hide()
    manager.close()
    window.ready = False
    window.close()
    app.processEvents()
    print(f"Rendered {len(list(output.glob('*.png')))} M4 screens")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/m4-screenshots")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--polish", action="store_true")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Screenshot output must stay inside the repository")
    if args.child:
        render(output, args.theme, polish=args.polish or args.final, final=args.final)
        return
    for theme in ("light", "dark"):
        for scale in ("1",) if args.polish or args.final else ("1", "1.5"):
            subprocess.run(
                [
                    sys.executable,
                    __file__,
                    "--child",
                    "--output",
                    str(output / f"{theme}-{scale}"),
                    "--theme",
                    theme,
                ]
                + (["--final"] if args.final else ["--polish"] if args.polish else []),
                env=dict(
                    os.environ,
                    QT_QPA_PLATFORM="offscreen",
                    QT_SCALE_FACTOR=scale,
                    LOCALAPPDATA=str(output / "appdata"),
                ),
                cwd=ROOT,
                check=True,
            )
    count = len(list(output.rglob("*.png")))
    (output / "README.md").write_text(
        "# M4 UI review\n\n"
        + (
            f"Review round: {len(FINAL_STATES) if args.final else len(POLISH_STATES)} states "
            f"in light-1 and dark-1 ({count} PNGs).\n"
            if args.polish or args.final
            else "21 synthetic states in both themes at 100% and 150% (84 PNGs).\n"
        )
        + "No user content or real downloads; 42 GB free-space value is synthetic.\n"
        "The actual Model Manager and main-window widgets are rendered with PySide6 6.9.2.\n"
        "Client areas only: native title bars and hover tooltips are not in widget grabs.\n"
        + "Reproduce: uv run python tools/render_models.py"
        + (" --final" if args.final else " --polish" if args.polish else "")
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
