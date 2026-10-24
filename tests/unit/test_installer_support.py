"""Real-device classification and bounded installer process contracts."""

import hashlib
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


@pytest.mark.parametrize("state", ["installed", "missing", "damaged"])
def test_installer_status_hash_checks_voice_detection_too(tmp_path, state):
    from dusty.runtime_paths import RuntimePaths

    resources = tmp_path / "resources"
    resources.mkdir()
    models = tmp_path / "models"
    models.mkdir()
    catalog = json.loads(
        (Path(__file__).resolve().parents[2] / "resources/models.json").read_text(encoding="utf-8")
    )
    voice = catalog["vad"][0]
    content = b"verified voice fixture"
    voice.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    if state != "missing":
        (models / voice["file_name"]).write_bytes(
            content if state == "installed" else b"x" * len(content)
        )
    (resources / "models.json").write_text(json.dumps(catalog), encoding="utf-8")
    paths = RuntimePaths(tmp_path / "bin", models, resources, tmp_path / "user")
    statuses = installer_support.model_status(paths)
    assert statuses["silero-vad"] == state
    assert all(statuses[key] == "missing" for key in statuses if key != "silero-vad")


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
@pytest.mark.parametrize("failed", [False, True])
def test_installer_selftest_runs_selected_backend_exactly_once(
    tmp_path, monkeypatch, gpu, backend, failed
):
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
                segments=[
                    SimpleNamespace(text="incorrect" if failed else "fellow americans your country")
                ]
            )
        )

    monkeypatch.setattr(selftest, "run_whisper", whisper)
    expected = "vulkan" if gpu and backend == "auto" else "cpu"
    assert (
        selftest.run_selftest(paths, "tiny", backend=backend, once=True)
        == ("TEXT_MISMATCH_" if failed else "OK_") + expected.upper()
    )
    assert calls == [expected]


def test_uninstall_size_uses_shared_units_and_ignores_unknown_files(tmp_path):
    from dusty.app import messages as M
    from dusty.runtime_paths import RuntimePaths

    models = tmp_path / "models"
    models.mkdir()
    (models / "ggml-tiny.bin").write_bytes(b"0" * 1_000_000)
    (models / "unrecognized.bin").write_bytes(b"unknown")
    paths = RuntimePaths(
        tmp_path / "bin",
        models,
        Path(__file__).resolve().parents[2] / "resources",
        tmp_path / "user",
    )
    assert installer_support.model_size(paths) == M.format_size(1_000_000)


@pytest.mark.parametrize("profile", ["fresh", "empty", "stale", "valid", "damaged"])
def test_successful_install_keeps_only_a_verified_existing_selection(tmp_path, profile):
    from dusty.runtime_paths import RuntimePaths

    resources = tmp_path / "resources"
    resources.mkdir()
    models = tmp_path / "models"
    models.mkdir()
    catalog = json.loads(
        (Path(__file__).resolve().parents[2] / "resources/models.json").read_text(encoding="utf-8")
    )
    for entry in catalog["models"]:
        if entry["id"] in {"tiny", "small"}:
            content = (entry["id"] + " verified fixture").encode()
            entry.update(size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
            (models / entry["file_name"]).write_bytes(content)
    (resources / "models.json").write_text(json.dumps(catalog), encoding="utf-8")
    paths = RuntimePaths(tmp_path / "bin", models, resources, tmp_path / "user")
    settings = paths.user_dir / "settings.json"
    if profile != "fresh":
        choice = None if profile == "empty" else "uninstalled" if profile == "stale" else "tiny"
        save_settings(
            settings,
            {
                "schema_version": 1,
                "model_id": choice,
                "prompt": "keep hints",
                "installer_test_failed": True,
            },
        )
    if profile == "damaged":
        tiny = next(m for m in catalog["models"] if m["id"] == "tiny")
        target = models / tiny["file_name"]
        target.write_bytes(b"x" * tiny["size_bytes"])
    installer_support.accept_tests(paths, "small")
    result = load_settings(settings)
    assert result["model_id"] == ("tiny" if profile == "valid" else "small")
    assert result["installer_test_failed"] is False
    if profile != "fresh":
        assert result["prompt"] == "keep hints"
