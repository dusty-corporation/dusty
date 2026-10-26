"""Real native processing with difficult paths, sync consent and exhausted disk."""

import errno
import hashlib
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QDialog

from dusty.app.dialogs import SyncDialog
from dusty.app.window import MainWindow
from dusty.app.workers import Prepared
from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.models import ModelRegistry, load_manifest
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


def runtime(tmp_path):
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    return RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")


def test_unicode_profile_models_and_synced_documents_output(qtbot, tmp_path, monkeypatch):
    base = tmp_path / "User Name گفتگو 日本語"
    paths = runtime(base)
    models = base / "AppData/Local/Dusty/models"
    models.mkdir(parents=True)
    catalog = load_manifest(paths.resources_dir / "models.json")
    for name in (catalog.models["tiny"].file_name, catalog.vad_file_name):
        shutil.copyfile(paths.models_dir / name, models / name)
    paths = RuntimePaths(paths.bin_dir, models, paths.resources_dir, models.parent)
    monkeypatch.setenv("LOCALAPPDATA", str(base / "AppData/Local"))
    monkeypatch.setenv("OneDrive", str(base / "OneDrive"))
    output = base / "OneDrive/Documents/گفتگو Transcripts"
    source = base / "تست ضبط.wav"
    shutil.copyfile(ROOT / "resources/selftest.wav", source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    window = MainWindow(paths, interactive=False)
    qtbot.addWidget(window)
    window.apply_prepared(Prepared(("tiny",), False, {}, vad_installed=True))
    window.output_dir = output
    window._set_combo(window.device_choice, "cpu")
    window.threads_choice.setValue(2)
    window.model.set_jobs([Job(source)])
    warnings = []
    monkeypatch.setattr(
        SyncDialog, "exec", lambda self: warnings.append(True) or QDialog.DialogCode.Accepted
    )
    window.show()
    window._refresh()
    window.start_batch()
    qtbot.waitUntil(lambda: not window.running, timeout=60000)
    assert warnings == [True]
    assert window.model.jobs[0].status == JobStatus.DONE
    assert {p.suffix for p in output.iterdir()} == {".txt", ".docx"}
    assert "Americans" in (output / (source.stem + ".txt")).read_text(encoding="utf-8")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert not list((paths.user_dir / "work").iterdir())


@pytest.mark.parametrize("stage", ["preflight", "decode", "native-decode", "export"])
def test_disk_exhaustion_fails_plainly_and_removes_partial_outputs(tmp_path, monkeypatch, stage):
    import dusty.engine
    import dusty.queue.outputs as outputs

    paths = runtime(tmp_path)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    source = tmp_path / "jfk.wav"
    shutil.copyfile(ROOT / "tests/fixtures/audio/formats/jfk.wav", source)
    before = source.read_bytes()
    job = Job(source)
    if stage == "preflight":
        monkeypatch.setattr(
            "dusty.queue.coordinator.shutil.disk_usage", lambda _: SimpleNamespace(free=0)
        )
    elif stage in {"decode", "native-decode"}:

        def full_decode(executable, source, target, **kwargs):
            target.write_bytes(b"synthetic incomplete PCM")
            if stage == "native-decode":
                raise dusty.engine.DecoderError("Synthetic decoder disk full", disk_full=True)
            raise OSError(errno.ENOSPC, "Synthetic exhausted disk")

        monkeypatch.setattr(dusty.engine, "transcode_audio", full_decode)
    else:
        rename = outputs.os.rename

        def full_export(source, target):
            if str(target).endswith(".docx"):
                raise OSError(errno.ENOSPC, "Synthetic exhausted disk")
            return rename(source, target)

        monkeypatch.setattr(outputs.os, "rename", full_export)
    Coordinator(paths, registry).run_batch(
        [job], BatchOptions("tiny", tmp_path / "out", backend="cpu"), vulkan_ok=False
    )
    assert job.status == JobStatus.FAILED and job.failure == FailureCode.DISK_FULL
    assert not job.outputs
    assert not list((tmp_path / "out").glob("*"))
    assert not list((paths.user_dir / "work").iterdir())
    assert source.read_bytes() == before


def test_real_native_decode_and_all_exports_with_extended_unicode_paths(tmp_path):
    folder = tmp_path
    while len(str(folder)) < 310:
        folder /= "Long recording folder گفتگو"
    folder = Path("\\\\?\\" + str(folder.resolve()))
    folder.mkdir(parents=True)
    source = folder / "تست ضبط public recording.wav"
    shutil.copyfile(ROOT / "tests/fixtures/audio/formats/jfk.wav", source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    paths = runtime(tmp_path)
    job = Job(source)
    options = BatchOptions(
        "tiny",
        folder / "Saved transcripts",
        backend="cpu",
        formats=("txt", "docx", "srt", "vtt", "json"),
    )
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    Coordinator(paths, registry).run_batch([job], options, vulkan_ok=False)
    assert job.status == JobStatus.DONE
    assert len(job.outputs) == 5 and all(p.is_file() for p in job.outputs)
    assert "Americans" in job.outputs[0].read_text(encoding="utf-8")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert not list((paths.user_dir / "work").iterdir())
