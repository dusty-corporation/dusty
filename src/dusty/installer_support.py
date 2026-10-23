"""Offline installer helpers using the same guarded process and settings code."""

import json
import sys
import tempfile
from pathlib import Path

from dusty.platform.win_process import run_job_process
from dusty.runtime_paths import RuntimePaths


def probe(paths: RuntimePaths, output: Path) -> bool:
    """Driver hangs/crashes always fall back within a five-second child deadline."""
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="dusty-probe-", dir=output.parent) as temp:
            result = Path(temp) / "probe.json"
            command = [str(Path(sys.executable).resolve())]
            if not getattr(sys, "frozen", False):
                command += ["-m", "dusty"]
            run = run_job_process(
                command + ["--probe-vulkan-child", "--out", str(result)], timeout_sec=5
            )
            ok = run.exit_code == 0 and json.loads(result.read_text())["real_gpu_found"] is True
    except (OSError, ValueError, KeyError):
        ok = False
    output.write_text(json.dumps({"real_gpu_found": ok}), encoding="utf-8")
    return ok


def clear_failed_selection(paths: RuntimePaths) -> None:
    from dusty.queue.storage import load_settings, save_settings

    file = paths.user_dir / "settings.json"
    settings = load_settings(file)
    settings["model_id"] = None
    settings["installer_test_failed"] = True
    save_settings(file, settings)


def accept_tests(paths: RuntimePaths, model_id: str) -> None:
    from dusty.queue.storage import load_settings, save_settings

    file = paths.user_dir / "settings.json"
    settings = load_settings(file)
    settings["installer_test_failed"] = False
    if not settings.get("model_id"):
        settings["model_id"] = model_id
    save_settings(file, settings)


def model_size(paths: RuntimePaths) -> str:
    """Actual direct model/partial bytes, without following links or directories."""
    total = 0
    if paths.models_dir.exists():
        for file in paths.models_dir.iterdir():
            if file.is_file() and not file.is_symlink() and not file.is_junction():
                total += file.stat().st_size
    return f"{total / 1_000_000_000:.1f}"
