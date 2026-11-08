"""Exercise package imports in fresh interpreters without Windows runtime state."""

import builtins
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_import_probe(source: str) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_progress_import_does_not_load_process_or_runner_modules() -> None:
    run_import_probe("""
import sys
from dusty.engine.progress import ProgressState
import dusty.engine as engine
assert ProgressState(0).backend is None
assert "run_whisper" in dir(engine)
try:
    engine.not_an_export
except AttributeError:
    pass
else:
    raise AssertionError("unknown export accepted")
for name in ("msvcrt", "dusty.platform.win_process", "dusty.engine.whisper", "dusty.engine.ffmpeg"):
    assert name not in sys.modules
""")


def test_lazy_exports_resolve_to_real_runner_api_and_cache_identity() -> None:
    run_import_probe("""
import sys
import dusty.engine as engine
assert "dusty.engine.ffmpeg" not in sys.modules
def reject_effect(event, args):
    if event in {"ctypes.dlopen", "subprocess.Popen", "os.posix_spawn", "os.fork"}:
        raise AssertionError("unexpected import side effect: " + event)
sys.addaudithook(reject_effect)
from dusty.engine import AudioProbe, DecoderError, probe_audio, transcode_audio
assert "dusty.engine.whisper" not in sys.modules
from dusty.engine import EngineError, EngineRun, run_whisper
from dusty.engine import ffmpeg, whisper
for name in engine.__all__:
    module = ffmpeg if hasattr(ffmpeg, name) else whisper
    assert getattr(engine, name) is getattr(module, name)
    assert engine.__dict__[name] is getattr(module, name)
assert "msvcrt" not in sys.modules
assert "dusty.platform.win_process" not in sys.modules
""")


@pytest.mark.parametrize("name", ["ffmpeg", "whisper"])
def test_import_does_not_touch_windows_loader(name: str) -> None:
    run_import_probe(f"""
import ctypes
import sys
def forbidden(*args, **kwargs):
    raise AssertionError("Windows loader used during shared import")
ctypes.WinDLL = forbidden
from dusty.engine import {name}
assert "msvcrt" not in sys.modules
assert "dusty.platform.win_process" not in sys.modules
""")


@pytest.mark.parametrize("name", ["ffmpeg", "whisper"])
def test_process_call_refuses_unsupported_platform_before_import(name, monkeypatch):
    from dusty.engine import ffmpeg, whisper

    module = ffmpeg if name == "ffmpeg" else whisper
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    original_import = builtins.__import__

    def checked_import(module_name, *args, **kwargs):
        assert module_name != "dusty.platform.win_process"
        return original_import(module_name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", checked_import)
    with pytest.raises(OSError, match="^Native process runner unavailable on this platform$"):
        module.run_job_process(["CANARY_SOURCE"])


@pytest.mark.parametrize("name", ["ffmpeg", "whisper"])
def test_windows_call_forwards_unchanged_to_existing_boundary(name, monkeypatch, tmp_path):
    from dusty.engine import ffmpeg, whisper

    module = ffmpeg if name == "ffmpeg" else whisper
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="win32"))
    original_import = builtins.__import__
    calls = []
    expected = object()

    def process(args, **kwargs):
        calls.append((args, kwargs))
        return expected

    def controlled_import(module_name, *args, **kwargs):
        if module_name == "dusty.platform.win_process":
            return SimpleNamespace(run_job_process=process)
        return original_import(module_name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", controlled_import)
    arguments = ["absolute executable", "one argument with spaces"]
    parameters = dict(
        cwd=tmp_path,
        on_stderr=lambda _: None,
        on_stdout=lambda _: None,
        cancel=object(),
        timeout_sec=12.5,
        on_poll=lambda: None,
    )
    assert module.run_job_process(arguments, **parameters) is expected
    assert len(calls) == 1 and calls[0][0] is arguments
    assert calls[0][1] == parameters


def test_existing_whisper_json_parser_is_available_on_host():
    from dusty.engine.whisper import parse_whisper_json

    transcript = parse_whisper_json(
        ROOT / "tests/fixtures/engine/sample-output.json",
        model_id="tiny",
        task="transcribe",
        backend="cpu",
        duration_sec=11.0,
    )
    assert transcript.model_id == "tiny" and transcript.backend == "cpu"
    assert transcript.language == "en" and transcript.duration_sec == 11.0
    assert len(transcript.segments) == 1
    assert (transcript.segments[0].start, transcript.segments[0].end) == (0.0, 10.5)
    assert "fellow Americans" in transcript.segments[0].text


def test_whisper_arguments_progress_and_parser_still_use_process_boundary(tmp_path, monkeypatch):
    from dusty.engine import whisper

    stem = tmp_path / "raw"
    (tmp_path / "raw.json").write_bytes(
        (ROOT / "tests/fixtures/engine/sample-output.json").read_bytes()
    )
    executable, model, wav, vad = (
        tmp_path / name for name in ("whisper-cli.exe", "model.bin", "audio.wav", "vad.bin")
    )
    cancel = object()
    progress = []

    def process(args, **kwargs):
        assert args == [
            str(executable.resolve()),
            "-m",
            str(model),
            "-f",
            str(wav),
            "-l",
            "en",
            "-t",
            "4",
            "-ojf",
            "-of",
            str(stem),
            "-pp",
            "-tr",
            "-ng",
            "--vad",
            "-vm",
            str(vad),
            "--prompt",
            "two words; one argument",
        ]
        assert kwargs["cancel"] is cancel and kwargs["timeout_sec"] == 43200
        kwargs["on_stderr"]("whisper_print_progress_callback: progress = 50%")
        kwargs["on_poll"]()
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=1.25)

    monkeypatch.setattr(whisper, "run_job_process", process)
    result = whisper.run_whisper(
        executable,
        model,
        wav,
        stem,
        model_id="tiny",
        task="translate",
        language="en",
        threads=4,
        duration_sec=11.0,
        backend="cpu",
        vad_model=vad,
        prompt="two words; one argument",
        cancel=cancel,
        on_progress=progress.append,
    )
    assert result.transcript.task == "translate" and result.process_sec == 1.25
    assert result.first_progress_sec is not None and progress == [0.5]
