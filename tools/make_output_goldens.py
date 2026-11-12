"""Write the files Dusty must keep producing byte for byte (docs/dev/extensions.md).

    python tools/make_output_goldens.py --src <checkout>/src \\
        --resources <checkout>/resources --out tests/fixtures/goldens-1.2.0

Run once against the Dusty 1.2.0 source (49f698e) to make the committed
goldens. tests/unit/test_output_goldens.py runs the same scenarios against the
current source with no extensions loaded and compares the bytes:

- every output format, through write_outputs, for an English and a Persian
  transcript, with no extras, time markers, words that may be wrong, and both;
- a saved queue;
- the settings the window saves, without the window geometry, as on a
  machine whose default is 4 threads (the default follows the CPU).

The scenarios use only the 1.2.0 interfaces, so the same code runs on both.
DOCX files are zip archives whose entries carry the time they were written,
in 1.2.0 too, so DOCX goldens are compared entry by entry: names, order,
compression and contents, without those times.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest import mock
from uuid import UUID

CREATED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
EXTRAS: dict[str, dict[str, Any]] = {
    "plain": {},
    "markers": {"time_markers": True, "marker_minutes": 0.5},
    "unsure": {"mark_unsure": True, "unsure_level": "very"},
    "both": {
        "time_markers": True,
        "marker_minutes": 1.0,
        "mark_unsure": True,
        "unsure_level": "somewhat",
    },
}
FORMATS: tuple[Any, ...] = ("txt", "srt", "vtt", "json", "docx")
THREADS = 4


class _FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return CREATED if tz is None else CREATED.astimezone(tz)


def transcripts() -> dict[str, Any]:
    from dusty.core import Segment, Transcript, Word

    def words(text: str, seed: int) -> tuple[Any, ...]:
        # Mostly sure words, some somewhat unsure (0.6) and some very unsure (0.3).
        parts = text.split(" ")
        levels = (0.97, 0.92, 0.6, 0.99, 0.3, 0.95, 0.88)
        return tuple(
            Word((" " if index else "") + part, levels[(seed + index) % len(levels)])
            for index, part in enumerate(parts)
        )

    english = [
        (0.0, 4.2, "Good morning, and thank you for coming in today."),
        (4.4, 9.8, "We will start with the budget and then talk about the schedule."),
        (12.5, 18.0, "The first item is the new library building on Mill Street."),
        (18.1, 18.4, "   "),
        (31.0, 37.5, "It opened in March, two weeks later than planned."),
        (38.0, 44.0, "Are there any questions before we move on?"),
        (62.0, 70.5, "Yes. How much did the repairs to the roof cost in the end?"),
        (71.0, 79.0, "About forty thousand, which is less than we feared."),
        (95.0, 101.0, "Thank you. Let us move on to the schedule for next year."),
    ]
    persian = [
        (0.0, 3.5, "سلام، خوش آمدید."),
        (3.8, 8.0, "امروز درباره برنامه سال آینده صحبت می کنیم."),
        (40.0, 46.0, "آیا سوالی هست؟"),
    ]

    def build(rows: list[tuple[float, float, str]], language: str) -> Any:
        segments = tuple(
            Segment(index, start, end, text, words(text, index))
            for index, (start, end, text) in enumerate(rows)
        )
        return Transcript(
            segments=segments,
            language=language,
            task="transcribe",
            model_id="small",
            backend="cpu",
            duration_sec=rows[-1][1],
        )

    return {"english": build(english, "en"), "persian": build(persian, "fa")}


def outputs(out: Path, work: Path, **write_options: Any) -> list[Path]:
    """Render every scenario through write_outputs and copy the bytes to out."""
    from dusty.core import BatchOptions, Job
    from dusty.export import formats
    from dusty.queue.outputs import write_outputs

    written = []
    original = formats.datetime
    formats.datetime = _FixedClock  # type: ignore[misc]
    try:
        for name, transcript in transcripts().items():
            for extras, values in EXTRAS.items():
                folder = work / f"{name}-{extras}"
                folder.mkdir(parents=True)
                options = BatchOptions(
                    model_id="small", output_dir=folder, formats=FORMATS, threads=THREADS, **values
                )
                job = Job(Path(f"/recordings/{name}.m4a"))
                for path in write_outputs(job, options, transcript, **write_options):
                    target = out / "outputs" / f"{name}-{extras}.{path.suffix[1:]}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(path.read_bytes())
                    written.append(target)
    finally:
        formats.datetime = original  # type: ignore[misc]
    return written


def saved_queue(out: Path) -> Path:
    from dusty.core import BatchOptions, FailureCode, Job, JobStatus
    from dusty.queue.storage import save_batch

    options = BatchOptions(
        model_id="small",
        output_dir=Path("/transcripts"),
        formats=("txt", "srt"),
        language="en",
        threads=THREADS,
        vad=True,
        prompt="Mill Street",
        collision="keep_both",
        time_markers=True,
        marker_minutes=2.5,
        mark_unsure=True,
        unsure_level="somewhat",
    )
    jobs = [
        Job(
            Path("/recordings/one.m4a"),
            id=UUID(int=1),
            status=JobStatus.DONE,
            progress=1.0,
            outputs=[Path("/transcripts/one.txt"), Path("/transcripts/one.srt")],
            backend_used="cpu",
            duration_sec=60.0,
            elapsed_sec=12.5,
        ),
        Job(
            Path("/recordings/two.wav"),
            id=UUID(int=2),
            relative_dir=Path("day 2"),
            status=JobStatus.FAILED,
            failure=FailureCode.NO_AUDIO,
        ),
        Job(Path("/recordings/three.mp3"), id=UUID(int=3)),
    ]
    target = out / "queue.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    save_batch(target, options, jobs)
    return target


def window_settings(out: Path, resources: Path, user: Path, **window_options: Any) -> Path:
    """The settings the window saves for a chosen set of options, geometry left out."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from dusty.runtime_paths import RuntimePaths

    application = QApplication.instance() or QApplication([])
    user.mkdir(parents=True, exist_ok=True)
    paths = RuntimePaths(resources.parent / "bin", resources.parent / "models", resources, user)
    # The default thread count follows this machine's CPU; the goldens were
    # made where it was 4, so every machine is shown as one with that default.
    cores = max(THREADS, os.cpu_count() or 1)
    with (
        mock.patch("dusty.app.window.default_threads", return_value=THREADS),
        mock.patch("os.cpu_count", return_value=cores),
    ):
        return _saved_window_settings(application, paths, out, user, window_options)


def _saved_window_settings(
    application: Any, paths: Any, out: Path, user: Path, window_options: dict[str, Any]
) -> Path:
    from dusty.app.window import MainWindow
    from dusty.app.workers import Prepared

    view = MainWindow(paths, interactive=False, **window_options)
    try:
        view.apply_prepared(
            Prepared(
                ("tiny", "small"),
                False,
                {"schema_version": 1, "welcome_seen": True, "model_id": "small"},
                vad_installed=True,
            )
        )
        view.time_markers.setChecked(True)
        view.mark_unsure.setChecked(True)
        view.prompt.setPlainText("Mill Street")
        if not view._save_settings():
            raise RuntimeError("The window did not save its settings")
        settings = json.loads((user / "settings.json").read_text(encoding="utf-8"))
    finally:
        view.close()
        view.deleteLater()
        application.processEvents()
    settings.pop("geometry", None)
    target = out / "settings.json"
    target.write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(args.src.resolve()))
    import dusty

    if not Path(dusty.__file__).resolve().is_relative_to(args.src.resolve()):
        raise SystemExit(f"dusty was imported from {dusty.__file__}, not from --src")
    args.out.mkdir(parents=True, exist_ok=True)
    # Dusty refuses to write through linked folders, such as /tmp on macOS.
    out = args.out.resolve()
    with tempfile.TemporaryDirectory(prefix="dusty-goldens-") as name:
        work = Path(name).resolve()
        outputs(out, work / "outputs")
        saved_queue(out)
        window_settings(out, args.resources.resolve(), work / "user")
    print(f"Goldens written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
