"""The extension points (docs/dev/extensions.md) with a made up extension.

"Notes" labels every segment "Part 1" or "Part 2" and needs a model file. It
exercises each point the way a real extension would, without any real one.
"""

import hashlib
import json
import re
import shutil
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_coordinator_collisions import native, paths  # noqa: F401

from dusty import extensions
from dusty.core import BatchOptions, Job, JobStatus, Segment, Transcript
from dusty.core.types import annotate, annotation
from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry, load_manifest
from dusty.queue import Coordinator
from dusty.queue.storage import load_batch, save_batch
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = load_manifest(ROOT / "resources/models.json")
NOTES = "notes"
MODEL = "notes-model"
CONTENT = b"notes model bytes"


class Parts:
    def applies(self, transcript: Transcript) -> bool:
        return annotation(transcript, "parts", False)

    def label(self, transcript: Transcript, segment: Segment) -> str | None:
        part = annotation(segment, "part")
        return None if part is None else f"Part {part}"

    def json_segment(self, transcript: Transcript, segment: Segment) -> dict[str, Any]:
        return {"part": annotation(segment, "part")}

    def json_transcript(self, transcript: Transcript) -> dict[str, Any]:
        return {"parts": 2}


def extension_catalog(entry: dict) -> dict:
    return {"schema_version": 1, "kind": "extension", "models": [entry]}


class Behaviour:
    def __init__(self) -> None:
        self.mode = "label"
        self.seen: list[extensions.StageInput] = []


def notes(behaviour: Behaviour, *, supported: bool = True) -> extensions.Extensions:
    """The made up extension; ``supported`` is read on each call, like a real gate."""

    def run(given: extensions.StageInput) -> Transcript:
        behaviour.seen.append(given)
        given.on_progress(0.5)
        (given.wav.parent / "notes.tmp").write_text("times only", encoding="utf-8")
        if behaviour.mode == "fail":
            raise extensions.StageFailed("notes exit 5")
        if behaviour.mode == "cancel":
            raise extensions.StageFailed("cancelled", cancelled=True)
        if behaviour.mode == "nothing":
            return replace(given.transcript)
        segments = tuple(
            annotate(segment, "part", 1 if index == 0 else 2)
            for index, segment in enumerate(given.transcript.segments)
        )
        return annotate(replace(given.transcript, segments=segments), "parts", True)

    found = extensions.Extensions()
    found.options.append(
        extensions.Option(
            key=NOTES,
            row="Notes",
            label="Add notes",
            help="Labels each part.",
            summary="notes added",
            unsupported="Not on this computer.",
            supported=lambda: supported,
            model=MODEL,
            model_missing="Download notes first.",
            download="Download notes",
        )
    )
    found.stages.append(
        extensions.Stage(NOTES, "Adding notes", "Done, without notes", run, ("notes.tmp",))
    )
    found.decorations.append(Parts())
    found.models.append(
        extensions.ExtraModel(MODEL, "notes-models.json", "Notes", "For notes", "Small", "Notes")
    )
    found.helpers.append(extensions.Helper("dusty-notes", "dusty_notes"))
    return found


class Registry:
    def __init__(self, folder: Path, model: str = "installed"):
        self.folder, self.manifest, self.model = folder, MANIFEST, model

    def model_path(self, model_id: str) -> Path:
        return self.folder / MANIFEST.models[model_id].file_name

    def vad_path(self) -> Path:
        return self.folder / MANIFEST.vad_file_name

    def extra_path(self, model_id: str) -> Path:
        assert model_id == MODEL
        if self.model == "missing":
            raise ModelMissing("missing")
        if self.model == "corrupt":
            raise ModelCorrupt("corrupt")
        return self.folder / "dusty-notes.onnx"


def run(tmp_path, paths, behaviour, *, on=True, model="installed", out="out", found=None):  # noqa: F811
    source = tmp_path / "in" / "talk.wav"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"RIFF public fixture stand-in")
    options = BatchOptions(
        "tiny",
        tmp_path / out,
        formats=("txt", "srt", "vtt", "json", "docx"),
        backend="cpu",
        extension_options=frozenset({NOTES}) if on else frozenset(),
    )
    job = Job(source)
    with extensions.use(found or notes(behaviour)):
        Coordinator(paths, Registry(tmp_path / "models", model)).run_batch(
            [job], options, cancel=threading.Event()
        )
    return job


def outputs(job: Job) -> dict[str, bytes]:
    return {path.suffix[1:]: path.read_bytes() for path in job.outputs}


def test_without_the_extension_package_there_are_no_extensions(monkeypatch) -> None:
    # None in sys.modules makes the import fail exactly as a package not installed.
    monkeypatch.setitem(sys.modules, extensions.EXTENSION_PACKAGE, None)
    extensions.loaded.cache_clear()
    try:
        assert extensions.loaded() == extensions.Extensions()
    finally:
        extensions.loaded.cache_clear()


class _BrokenDependency:
    """Importing the extension package fails on a module it needs."""

    def find_spec(self, name, path=None, target=None):
        if name == extensions.EXTENSION_PACKAGE:
            raise ModuleNotFoundError("No module named 'dusty_missing'", name="dusty_missing")
        return None


def test_an_extension_that_fails_to_import_is_an_error(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, extensions.EXTENSION_PACKAGE, raising=False)
    monkeypatch.setattr(sys, "meta_path", [_BrokenDependency(), *sys.meta_path])
    extensions.loaded.cache_clear()
    try:
        with pytest.raises(ModuleNotFoundError) as error:
            extensions.loaded()
        assert error.value.name == "dusty_missing"
    finally:
        extensions.loaded.cache_clear()


def test_use_chooses_extensions_until_it_ends() -> None:
    outer, inner = extensions.Extensions(), notes(Behaviour())
    with extensions.use(outer):
        assert extensions.active() is outer
        with extensions.use(inner):
            assert extensions.active() is inner
        assert extensions.active() is outer
    assert extensions.active() is extensions.loaded()


def test_a_stage_runs_after_transcription_and_decorates_every_format(
    tmp_path,
    paths,  # noqa: F811
    native,  # noqa: F811
) -> None:
    behaviour = Behaviour()
    job = run(tmp_path, paths, behaviour)
    assert job.status == JobStatus.DONE and job.stage_failed is None
    given = behaviour.seen[0]
    assert given.model == tmp_path / "models/dusty-notes.onnx"
    assert given.threads >= 1 and given.wav.name == "audio.wav"
    out = outputs(job)
    assert out["txt"].decode().startswith("Part 1: ")
    assert "Part 1: " in out["srt"].decode()
    assert "<v Part 1>" in out["vtt"].decode()
    data = json.loads(out["json"])
    assert data["parts"] == 2 and data["segments"][0]["part"] == 1
    assert job.transcript is not None and set(job.written) == set(job.outputs)
    work = paths.user_dir / "work"
    assert not work.exists() or not any(work.rglob("notes.tmp"))


def test_with_the_option_off_nothing_changes(tmp_path, paths, native) -> None:  # noqa: F811
    behaviour = Behaviour()
    plain = run(tmp_path, paths, behaviour, on=False, out="a")
    assert behaviour.seen == [] and plain.transcript is None
    reference = Job(tmp_path / "in" / "talk.wav")
    options = BatchOptions(
        "tiny", tmp_path / "b", formats=("txt", "srt", "vtt", "json"), backend="cpu"
    )
    with extensions.use(extensions.Extensions()):
        Coordinator(paths, Registry(tmp_path / "models")).run_batch(
            [reference], options, cancel=threading.Event()
        )
    for fmt, content in outputs(reference).items():
        if fmt != "json":
            assert outputs(plain)[fmt] == content


@pytest.mark.parametrize("model", ["missing", "corrupt"])
def test_a_missing_model_or_failed_stage_still_saves_the_file(
    tmp_path,
    paths,  # noqa: F811
    native,  # noqa: F811
    model,
) -> None:
    for behaviour, registry_model in ((Behaviour(), model), (Behaviour(), "installed")):
        if registry_model == "installed":
            behaviour.mode = "fail"
        job = run(tmp_path, paths, behaviour, model=registry_model, out=registry_model)
        assert job.status == JobStatus.DONE and job.failure is None
        assert job.stage_failed == "Done, without notes"
        assert "Part" not in outputs(job)["txt"].decode() and job.transcript is None


def test_a_cancelled_stage_cancels_the_file(tmp_path, paths, native) -> None:  # noqa: F811
    behaviour = Behaviour()
    behaviour.mode = "cancel"
    job = run(tmp_path, paths, behaviour)
    assert job.status == JobStatus.CANCELLED and job.outputs == []
    work = paths.user_dir / "work"
    assert not work.exists() or not any(work.iterdir())


def test_options_are_saved_only_while_on_and_dropped_when_not_installed(tmp_path) -> None:
    state = tmp_path / "queue.json"
    on = BatchOptions("tiny", tmp_path / "out", extension_options=frozenset({NOTES}))
    with extensions.use(notes(Behaviour())):
        save_batch(state, on, [Job(tmp_path / "a.wav")])
        loaded = load_batch(state)
    assert loaded is not None and loaded[0].extension_options == {NOTES}
    assert json.loads(state.read_text())["options"]["extension_options"] == [NOTES]
    with extensions.use(extensions.Extensions()):
        loaded = load_batch(state)
        assert loaded is not None and loaded[0].extension_options == frozenset()
        save_batch(state, BatchOptions("tiny", tmp_path / "out"), [Job(tmp_path / "a.wav")])
    assert "extension_options" not in json.loads(state.read_text())["options"]


def test_extension_models_come_from_their_own_catalog_file(tmp_path) -> None:
    shutil.copyfile(ROOT / "resources/models.json", tmp_path / "models.json")
    entry = {
        "id": MODEL,
        "file_name": "dusty-notes.onnx",
        "size_bytes": len(CONTENT),
        "sha256": hashlib.sha256(CONTENT).hexdigest(),
        "url": "https://github.com/dusty-corporation/dusty/releases/download/x/dusty-notes.onnx",
    }
    (tmp_path / "notes-models.json").write_text(
        json.dumps({"schema_version": 1, "kind": "extension", "models": [entry]}), encoding="utf-8"
    )
    with extensions.use(notes(Behaviour())):
        registry = ModelRegistry(load_manifest(tmp_path / "models.json"), tmp_path)
    with extensions.use(extensions.Extensions()):
        assert load_manifest(tmp_path / "models.json").extra == {}
    # A catalog file that is not there leaves its model out.
    (tmp_path / "notes-models.json").rename(tmp_path / "elsewhere.json")
    with extensions.use(notes(Behaviour())):
        assert load_manifest(tmp_path / "models.json").extra == {}
    (tmp_path / "elsewhere.json").rename(tmp_path / "notes-models.json")
    with pytest.raises(ModelMissing):
        registry.extra_path(MODEL)
    (tmp_path / "dusty-notes.onnx").write_bytes(CONTENT)
    assert registry.extra_path(MODEL) == tmp_path / "dusty-notes.onnx"
    registry.invalidate(file_name="dusty-notes.onnx")
    for damage in ({"file_name": "../x.onnx"}, {"id": "other"}, {"sha256": "0"}):
        (tmp_path / "notes-models.json").write_text(
            json.dumps(extension_catalog(entry | damage)), encoding="utf-8"
        )
        with extensions.use(notes(Behaviour())), pytest.raises(ValueError):
            load_manifest(tmp_path / "models.json")


def test_helpers_are_approved_executables(monkeypatch, tmp_path) -> None:
    from dusty.platform.process import approved_executable
    from dusty.runtime_paths import resolve_helper_command

    app = tmp_path / "Dusty.app/Contents/MacOS/Dusty"
    command = resolve_helper_command("dusty-notes", "dusty_notes", frozen=True, executable=app)
    # The frozen helper is the program itself; on Windows its name ends in .exe.
    program = "dusty-notes.exe" if sys.platform == "win32" else "dusty-notes"
    assert command[0].endswith(program) and "-m" not in command
    source = resolve_helper_command("dusty-notes", "dusty_notes", frozen=False, platform="win32")
    assert source[1:] == ["-m", "dusty_notes"]
    helper = tmp_path / "helper/dusty-notes"
    helper.parent.mkdir()
    helper.write_text("#!/bin/sh\n")
    monkeypatch.setattr(
        "dusty.runtime_paths.resolve_helper_command", lambda name, module: [str(helper)]
    )
    with extensions.use(extensions.Extensions()), pytest.raises(ValueError):
        approved_executable(helper)
    with extensions.use(notes(Behaviour())):
        assert approved_executable(helper) == helper.resolve()


def window(qtbot, tmp_path: Path, found: extensions.Extensions, installed=()):
    from dusty.app.window import MainWindow
    from dusty.app.workers import Prepared
    from dusty.runtime_paths import resolve_paths

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    # The bundled resources plus the made up extension's catalog file.
    resources = tmp_path / "resources"
    shutil.copytree(dev.resources_dir, resources)
    entry = {"id": MODEL, "file_name": "dusty-notes.onnx", "size_bytes": 1, "sha256": "0" * 64}
    (resources / "notes-models.json").write_text(
        json.dumps({"schema_version": 1, "kind": "extension", "models": [entry]}), encoding="utf-8"
    )
    user = RuntimePaths(dev.bin_dir, dev.models_dir, resources, tmp_path / "user")
    with extensions.use(found):
        view = MainWindow(user, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            ("tiny",),
            False,
            {"schema_version": 1, "welcome_seen": True, "model_id": "tiny"},
            vad_installed=True,
            extra_installed=installed,
        )
    )
    view.output_dir = tmp_path / "out"
    view.show()
    view._refresh()
    return view


def test_without_extensions_the_window_has_no_extra_option(qtbot, tmp_path) -> None:
    view = window(qtbot, tmp_path, extensions.Extensions())
    assert view.extension_boxes == {}
    assert view.batch_options().extension_options == frozenset()
    assert view._save_settings() and "notes" not in view.settings


def test_an_option_reaches_settings_summary_and_the_batch(qtbot, tmp_path) -> None:
    view = window(qtbot, tmp_path, notes(Behaviour()), installed=(MODEL,))
    box = view.extension_boxes[NOTES]
    assert not box.isChecked() and box.isEnabled() and box.accessibleName() == "Add notes"
    box.setChecked(True)
    assert view.batch_options().extension_options == {NOTES}
    assert "notes added" in view.choices_summary.text()
    assert view._save_settings() and view.settings["extension_options"] == [NOTES]


def test_settings_hold_options_only_while_on_under_their_own_key(qtbot, tmp_path) -> None:
    from dusty.queue.storage import load_settings

    found = notes(Behaviour())
    view = window(qtbot, tmp_path, found, installed=(MODEL,))
    file = view.paths.user_dir / "settings.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    # An option of an extension not installed here is kept as it was.
    view.settings["extension_options"] = ["elsewhere"]
    file.write_text(json.dumps(view.settings), encoding="utf-8")
    view.extension_boxes[NOTES].setChecked(True)
    assert view._save_settings()
    saved = load_settings(file)
    assert saved["extension_options"] == ["elsewhere", NOTES]
    assert NOTES not in saved and saved["vad"] is False
    fresh = window(qtbot, tmp_path / "again", found, installed=(MODEL,))
    assert not fresh.extension_boxes[NOTES].isChecked()
    fresh._apply_settings(dict(saved))
    assert fresh.extension_boxes[NOTES].isChecked()
    view.extension_boxes[NOTES].setChecked(False)
    view.settings.pop("extension_options")
    file.write_text(json.dumps(view.settings), encoding="utf-8")
    assert view._save_settings() and "extension_options" not in load_settings(file)


@pytest.mark.parametrize("value", ["notes", [1], {"notes": True}])
def test_damaged_saved_extension_options_are_refused(tmp_path, value) -> None:
    from dusty.queue.storage import load_settings

    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"schema_version": 1, "extension_options": value}))
    assert "extension_options" not in load_settings(file)
    assert list(tmp_path.glob("settings.json.corrupt-*"))


def test_an_unsupported_option_is_disabled_and_off(qtbot, tmp_path) -> None:
    view = window(qtbot, tmp_path, notes(Behaviour(), supported=False), installed=(MODEL,))
    view.extension_boxes[NOTES].setChecked(True)
    view._refresh()
    assert not view.extension_boxes[NOTES].isEnabled()
    assert view.extension_unavailable[NOTES].isVisibleTo(view.options_dialog)
    assert view.batch_options().extension_options == frozenset()


def test_an_option_waits_for_its_model(qtbot, tmp_path, monkeypatch) -> None:
    view = window(qtbot, tmp_path, notes(Behaviour()))
    view.model.set_jobs([Job(tmp_path / "a.wav")])
    view.extension_boxes[NOTES].setChecked(True)
    view._refresh()
    assert not view.start_button.isEnabled()
    assert view.start_hint.text() == "Download notes first."
    assert view.download_recommended_button.text() == "Download notes"
    targets: list[str | None] = []
    monkeypatch.setattr(
        view, "open_model_manager", lambda *, focus_id=None: targets.append(focus_id)
    )
    view.download_recommended()
    assert targets == [MODEL]


def test_actions_are_offered_for_a_finished_file_of_this_session(qtbot, tmp_path) -> None:
    ran: list[Job] = []
    found = notes(Behaviour())
    found.actions.append(
        extensions.Action(
            "Check notes",
            lambda job: job.transcript is not None,
            lambda view, job, options: ran.append(job),
            default=True,
        )
    )
    view = window(qtbot, tmp_path, found)
    job = Job(tmp_path / "a.wav", status=JobStatus.DONE)
    view.model.set_jobs([job])
    view.table.selectRow(0)
    assert view._job_actions() == (None, [])
    job.written = {tmp_path / "a.txt": "0" * 64}
    view._finished_options[job.id] = BatchOptions("tiny", tmp_path / "out")
    assert view._job_actions() == (job, [])
    job.transcript = Transcript((), "en", "transcribe", "tiny", "cpu", 1.0)
    chosen, actions = view._job_actions()
    assert chosen is job and [item.label for item in actions] == ["Check notes"]
    view._table_details(view.model.index(0, 0))
    assert ran == [job]


def test_the_list_shows_the_stage_status_and_failure(tmp_path) -> None:
    from dusty.app.table import QueueModel

    model = QueueModel()
    working = Job(tmp_path / "a.wav", status=JobStatus.PROCESSING, progress=0.4)
    working.stage_status = "Adding notes"
    failed = Job(tmp_path / "b.wav", status=JobStatus.DONE)
    failed.stage_failed = "Done, without notes"
    model.set_jobs([working, failed])
    assert model.data(model.index(0, 2)) == "Adding notes"
    assert model.data(model.index(1, 2)) == "Done, without notes"


def test_a_stage_that_adds_nothing_keeps_no_transcript(tmp_path, paths, native) -> None:  # noqa: F811
    behaviour = Behaviour()
    behaviour.mode = "nothing"
    job = run(tmp_path, paths, behaviour)
    assert job.status == JobStatus.DONE and behaviour.seen
    assert job.transcript is None and job.stage_failed is None


def test_an_unsupported_option_never_runs_even_from_a_restored_queue(
    tmp_path,
    paths,  # noqa: F811
    native,  # noqa: F811
) -> None:
    behaviour = Behaviour()
    unsupported = notes(behaviour, supported=False)
    job = run(tmp_path, paths, behaviour, found=unsupported)
    assert job.status == JobStatus.DONE and behaviour.seen == []
    assert job.stage_failed is None and "Part" not in outputs(job)["txt"].decode()
    state = tmp_path / "queue.json"
    on = BatchOptions("tiny", tmp_path / "out", extension_options=frozenset({NOTES}))
    with extensions.use(unsupported):
        save_batch(state, on, [Job(tmp_path / "a.wav")])
        loaded = load_batch(state)
    assert loaded is not None and loaded[0].extension_options == frozenset()


def test_the_downloader_takes_onnx_files_only_from_extension_catalogs(tmp_path) -> None:
    from dusty_fetch.downloader import FetchError, HostPolicy, load_asset

    entry = {
        "id": MODEL,
        "file_name": "dusty-notes.onnx",
        "size_bytes": len(CONTENT),
        "sha256": hashlib.sha256(CONTENT).hexdigest(),
        "url": "https://github.com/dusty-corporation/dusty/releases/download/x/dusty-notes.onnx",
    }
    catalog = tmp_path / "notes-models.json"
    catalog.write_text(json.dumps({"schema_version": 1, "kind": "extension", "models": [entry]}))
    assert load_asset(catalog, MODEL, HostPolicy()).file_name == "dusty-notes.onnx"
    # The bundled manifest takes ggml-*.bin files only, as in 1.2.0.
    manifest = json.loads((ROOT / "resources/models.json").read_text(encoding="utf-8"))
    manifest["models"].append(entry)
    (tmp_path / "models.json").write_text(json.dumps(manifest))
    with pytest.raises(FetchError):
        load_asset(tmp_path / "models.json", MODEL, HostPolicy())
    # And an extension catalog takes no ggml files.
    bin_entry = entry | {"file_name": "ggml-notes.bin"}
    catalog.write_text(json.dumps(extension_catalog(bin_entry)))
    with pytest.raises(FetchError):
        load_asset(catalog, MODEL, HostPolicy())


def test_an_option_reason_may_change_while_dusty_runs(qtbot, tmp_path) -> None:
    state = {"reason": "First reason."}
    found = notes(Behaviour(), supported=False)
    found.options[0] = replace(found.options[0], unsupported=lambda: state["reason"])
    view = window(qtbot, tmp_path, found, installed=(MODEL,))
    label = view.extension_unavailable[NOTES]
    assert (
        label.text() == "First reason." and extensions.reason(found.options[0]) == "First reason."
    )
    state["reason"] = "Second reason."
    view._refresh()
    assert label.text() == "Second reason."


def test_about_lines_and_help_commands_come_from_extensions(qtbot, tmp_path, monkeypatch) -> None:
    from dusty.app import dialogs

    ran: list[object] = []
    found = notes(Behaviour())
    found.about.append(lambda: "Notes edition")
    found.about.append(lambda: None)
    found.commands.append(extensions.Command("Notes settings...", lambda view: ran.append(view)))
    view = window(qtbot, tmp_path, found)
    assert [action.text() for action in view.extension_commands] == ["Notes settings..."]
    view.extension_commands[0].trigger()
    assert ran == [view]
    shown: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        dialogs.AboutDialog, "exec", lambda dialog: shown.append(about_texts(dialog)) or 0
    )
    view.show_about()
    assert shown and shown[0][1] == "Notes edition" and None not in shown[0]


def test_without_extensions_help_and_about_are_as_before(qtbot, tmp_path, monkeypatch) -> None:
    from dusty.app import dialogs
    from dusty.app import messages as M

    view = window(qtbot, tmp_path, extensions.Extensions())
    assert view.extension_commands == []
    shown: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        dialogs.AboutDialog, "exec", lambda dialog: shown.append(about_texts(dialog)) or 0
    )
    view.show_about()
    assert shown[0][1] == M.ABOUT_DESCRIPTION


def about_texts(dialog) -> tuple[str, ...]:
    from PySide6.QtWidgets import QLabel

    return tuple(label.text() for label in dialog.findChildren(QLabel))


def test_an_engine_hint_steers_only_its_languages_while_its_option_is_on(
    tmp_path,
    paths,  # noqa: F811
    native,  # noqa: F811
    monkeypatch,
) -> None:
    from dusty.engine import whisper
    from dusty.queue.coordinator import engine_prompt

    found = notes(Behaviour())
    found.stages.clear()
    hint = extensions.EngineHint(NOTES, frozenset({"fr"}), "Euh.", carry=True)
    found.engine_hints.append(hint)
    on = frozenset({NOTES})
    with extensions.use(found):
        base = BatchOptions("tiny", tmp_path, language="fr")
        assert engine_prompt(base) == ("", False)
        steered = replace(base, extension_options=on)
        assert engine_prompt(steered) == ("Euh.", True)
        # The user's hints are used exactly as before, and the hint is left out.
        hinted = replace(steered, prompt="Mill Street")
        assert engine_prompt(hinted) == ("Mill Street", False)
        assert engine_prompt(replace(hinted, prompt="  ")) == ("Euh.", True)
        english = replace(steered, language="en")
        assert engine_prompt(english) == ("", False)
    with extensions.use(notes(Behaviour(), supported=False)) as locked:
        locked.engine_hints.append(hint)
        assert engine_prompt(steered) == ("", False)
    seen: list[list[str]] = []
    real = whisper.run_job_process
    monkeypatch.setattr(
        whisper, "run_job_process", lambda args, **kw: seen.append(list(args)) or real(args, **kw)
    )
    source = tmp_path / "in" / "talk.wav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"RIFF public fixture stand-in")
    runs = (
        (found, steered),
        (found, hinted),
        (found, replace(hinted, extension_options=frozenset())),
        (extensions.Extensions(), replace(hinted, extension_options=frozenset())),
    )
    for active, options in runs:
        with extensions.use(active):
            Coordinator(paths, Registry(tmp_path / "models")).run_batch(
                [Job(source)],
                replace(options, output_dir=tmp_path / f"out{len(seen)}"),
                cancel=threading.Event(),
            )
    carried, with_hints, option_off, bare = seen

    def same_job(args: list[str]) -> list[str]:
        return [re.sub(r"job-[0-9a-f-]+|out[-\w]*", "*", arg) for arg in args]

    # The user's hints reach the engine exactly as with no add-ons (Dusty 1.2.0),
    # with the option on or off.
    assert same_job(with_hints) == same_job(bare) == same_job(option_off)
    assert bare[bare.index("--prompt") + 1] == "Mill Street"
    assert "--carry-initial-prompt" not in bare
    assert carried[carried.index("--prompt") :][:3] == [
        "--prompt",
        "Euh.",
        "--carry-initial-prompt",
    ]


def test_engine_prompts_are_never_logged(tmp_path, caplog, monkeypatch) -> None:
    import logging

    # Another test may have configured Dusty's file log, which stops propagation.
    monkeypatch.setattr(logging.getLogger("dusty"), "propagate", True)

    from dusty.queue.coordinator import engine_prompt

    found = notes(Behaviour())
    hint = extensions.EngineHint(NOTES, frozenset({"fr"}), "Secret filler.", True)
    found.engine_hints.append(hint)
    caplog.set_level(logging.DEBUG)
    with extensions.use(found):
        options = BatchOptions(
            "tiny", tmp_path, language="fr", extension_options=frozenset({NOTES})
        )
        assert engine_prompt(options) == ("Secret filler.", True)
        hinted = replace(options, prompt="Private name")
        assert engine_prompt(hinted) == ("Private name", False)
    assert "Private" not in caplog.text and "Secret" not in caplog.text
