"""The self-test and the GPU check ask whisper.cpp for at most the machine's cores.

Both used to ask for four threads everywhere. On a computer with two logical
processors (one core) whisper.cpp then spins its four threads against each other
and a few seconds of audio did not finish in minutes, which also stopped Setup's
model test. They now use the default thread count, capped at the earlier four.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
CASES = [(1, 1), (2, 2), (4, 4), (8, 4)]


def _fake_whisper(seen: list[int]):
    def whisper(*_args, **kwargs):
        seen.append(kwargs["threads"])
        segment = SimpleNamespace(text="fellow americans your country", start=0.0, end=1.0)
        return SimpleNamespace(transcript=SimpleNamespace(segments=[segment]), device_name=None)

    return whisper


def _paths(tmp_path: Path) -> RuntimePaths:
    user = tmp_path / "user"
    user.mkdir(mode=0o700)
    return RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", user)


@pytest.mark.parametrize(("cores", "expected"), CASES)
def test_selftest_threads_follow_the_machine(tmp_path, monkeypatch, cores, expected):
    from dusty import selftest

    seen: list[int] = []
    monkeypatch.setattr(selftest, "default_threads", lambda: cores)
    monkeypatch.setattr(selftest, "load_manifest", lambda *_: None)
    monkeypatch.setattr(
        selftest, "ModelRegistry", lambda *_: SimpleNamespace(model_path=lambda _: tmp_path / "m")
    )
    monkeypatch.setattr(
        selftest, "probe_audio", lambda *_: SimpleNamespace(has_audio=True, duration_sec=10)
    )
    monkeypatch.setattr(selftest, "transcode_audio", lambda *_: None)
    monkeypatch.setattr(selftest, "run_whisper", _fake_whisper(seen))
    assert selftest.run_selftest(_paths(tmp_path), "tiny", backend="cpu", once=True) == "OK_CPU"
    assert seen == [expected]


@pytest.mark.parametrize(("cores", "expected"), CASES)
def test_gpu_check_threads_follow_the_machine(tmp_path, monkeypatch, cores, expected):
    from dusty.engine import backend

    seen: list[int] = []
    paths = _paths(tmp_path)
    program = backend.whisper_path(paths.bin_dir, backend.gpu_backend())
    program.parent.mkdir(parents=True)
    program.write_bytes(b"pinned engine")
    monkeypatch.setattr(backend, "default_threads", lambda: cores)
    monkeypatch.setattr(backend, "display_driver_signature", lambda: "driver")
    monkeypatch.setattr(
        backend, "probe_audio", lambda *_: SimpleNamespace(has_audio=True, duration_sec=10)
    )
    monkeypatch.setattr(backend, "transcode_audio", lambda *_: None)
    monkeypatch.setattr(backend, "run_whisper", _fake_whisper(seen))
    registry = SimpleNamespace(model_path=lambda _: tmp_path / "m")
    backend.probe_gpu(paths, registry, refresh=True)
    assert seen == [expected]


@pytest.mark.parametrize(("cores", "expected"), CASES)
def test_batch_options_default_threads_follow_the_machine(tmp_path, monkeypatch, cores, expected):
    from dusty.core import BatchOptions
    from dusty.platform import cpu_topology

    monkeypatch.setattr(cpu_topology, "default_threads", lambda: cores)
    assert BatchOptions("tiny", tmp_path).threads == expected
    assert BatchOptions("tiny", tmp_path, threads=6).threads == 6
