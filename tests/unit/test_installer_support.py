"""Real-device classification and bounded installer process contracts."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty import installer_support
from dusty.platform.vulkan_probe import is_real_gpu
from dusty.queue.storage import load_settings, save_settings
from dusty.runtime_paths import resolve_paths


@pytest.mark.parametrize(
    "kind,vendor,name,expected",
    [
        (1, 0x8086, "Intel Iris Xe", True),
        (2, 0x10DE, "NVIDIA graphics", True),
        (4, 0x10005, "llvmpipe", False),
        (2, 0x1AE0, "SwiftShader", False),
        (2, 0x1414, "Microsoft Basic Render Driver", False),
        (3, 0x1234, "virtual", False),
        (0, 0x1234, "unknown", False),
        (2, 0x1234, "lavapipe", False),
    ],
)
def test_only_physical_vulkan_gpus_count(kind, vendor, name, expected):
    assert is_real_gpu(kind, vendor, name) is expected


@pytest.mark.parametrize("mode", ["ok", "none", "crash", "timeout"])
def test_bounded_probe_falls_back_and_removes_work(tmp_path, monkeypatch, mode):
    output = tmp_path / "result.json"

    def run(command, *, timeout_sec):
        assert timeout_sec == 5
        result = Path(command[-1])
        assert command[-3] == "--probe-vulkan-child"
        if mode in {"ok", "none"}:
            result.write_text(json.dumps({"real_gpu_found": mode == "ok"}))
        return SimpleNamespace(exit_code=0 if mode in {"ok", "none"} else -1)

    monkeypatch.setattr(installer_support, "run_job_process", run)
    assert installer_support.probe(resolve_paths(), output) is (mode == "ok")
    assert json.loads(output.read_text())["real_gpu_found"] is (mode == "ok")
    assert list(tmp_path.iterdir()) == [output]


def test_real_entry_point_model_free_probe_is_bounded(tmp_path):
    output = tmp_path / "result.json"
    process = subprocess.run(
        [sys.executable, "-m", "dusty", "--probe-vulkan", "--out", str(output)],
        capture_output=True,
        timeout=12,
    )
    assert process.returncode in (0, 1)
    assert isinstance(json.loads(output.read_text())["real_gpu_found"], bool)


def test_hanging_probe_child_is_terminated_by_real_job_deadline(tmp_path, monkeypatch):
    import time

    from dusty.platform.win_process import run_job_process

    def stalled(command, *, timeout_sec):
        assert timeout_sec == 5
        result = run_job_process(
            [str(Path(sys.executable).resolve()), "-c", "import time; time.sleep(60)"],
            timeout_sec=0.15,
        )
        assert result.cancelled and result.exit_code != 0
        return result

    monkeypatch.setattr(installer_support, "run_job_process", stalled)
    began = time.monotonic()
    output = tmp_path / "result.json"
    assert not installer_support.probe(resolve_paths(), output)
    assert time.monotonic() - began < 3
    assert json.loads(output.read_text())["real_gpu_found"] is False


def test_finish_without_preserves_settings_and_verified_files(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    paths = resolve_paths()
    model = paths.user_dir / "models/keep.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"previous verified file")
    file = paths.user_dir / "settings.json"
    save_settings(
        file, {"schema_version": 1, "model_id": "small", "output_dir": "saved-output", "vad": True}
    )
    installer_support.clear_failed_selection(paths)
    settings = load_settings(file)
    assert settings["model_id"] is None and settings["installer_test_failed"] is True
    assert settings["output_dir"] == "saved-output" and settings["vad"] is True
    assert model.read_bytes() == b"previous verified file"


@pytest.mark.parametrize("gpu,backend", [(True, "auto"), (False, "auto"), (True, "cpu")])
def test_installer_selftest_runs_selected_backend_exactly_once(tmp_path, monkeypatch, gpu, backend):
    from dusty import selftest

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    paths = resolve_paths()
    calls = []
    monkeypatch.setattr(installer_support, "probe", lambda *_: gpu)
    monkeypatch.setattr(selftest, "load_manifest", lambda *_: None)
    monkeypatch.setattr(
        selftest,
        "ModelRegistry",
        lambda *_: SimpleNamespace(model_path=lambda _: tmp_path / "model.bin"),
    )
    monkeypatch.setattr(
        selftest, "probe_audio", lambda *_: SimpleNamespace(has_audio=True, duration_sec=10)
    )
    monkeypatch.setattr(selftest, "transcode_audio", lambda *_: None)

    def whisper(*args, **kwargs):
        calls.append(kwargs["backend"])
        return SimpleNamespace(
            transcript=SimpleNamespace(
                segments=[SimpleNamespace(text="fellow americans your country")]
            )
        )

    monkeypatch.setattr(selftest, "run_whisper", whisper)
    expected = "vulkan" if gpu and backend == "auto" else "cpu"
    assert (
        selftest.run_selftest(paths, "tiny", backend=backend, once=True) == "OK_" + expected.upper()
    )
    assert calls == [expected]
