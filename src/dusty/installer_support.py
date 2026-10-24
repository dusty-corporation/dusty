"""Offline installer helpers using the same guarded process and settings code."""

import json
import sys
from pathlib import Path

from dusty.platform.win_process import run_job_process
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork, canonical, linked, protected_paths


def probe(paths: RuntimePaths, output: Path) -> bool:
    """Driver hangs/crashes always fall back within a five-second child deadline."""
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        owned = OwnedWork(output.parent, "device-probe")
        try:
            result = owned.path / "probe.json"
            command = [str(Path(sys.executable).resolve())]
            if not getattr(sys, "frozen", False):
                command += ["-m", "dusty"]
            run = run_job_process(
                command + ["--probe-vulkan-child", "--out", str(result)], timeout_sec=5
            )
            ok = run.exit_code == 0 and json.loads(result.read_text())["real_gpu_found"] is True
        finally:
            owned.record("probe.json")
            owned.cleanup(paths.user_dir)
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
    from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry, load_manifest
    from dusty.queue.storage import load_settings, save_settings

    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    registry.model_path(model_id)  # Never install an unverified default choice.
    file = paths.user_dir / "settings.json"
    settings = load_settings(file)
    settings["installer_test_failed"] = False
    try:
        selected = settings.get("model_id")
        if not isinstance(selected, str):
            raise ModelMissing("No model selected")
        registry.model_path(selected)
    except (KeyError, ModelMissing, ModelCorrupt, OSError, ValueError, TypeError):
        settings["model_id"] = model_id
    save_settings(file, settings)


def model_size(paths: RuntimePaths) -> str:
    """Actual direct model/partial bytes, without following links or directories."""
    from dusty.models import load_manifest

    manifest = load_manifest(paths.resources_dir / "models.json")
    names = {item.file_name for item in manifest.models.values()} | {manifest.vad_file_name}
    names |= {name + ".part" for name in names.copy()}
    total = 0
    if paths.models_dir.exists():
        for file in paths.models_dir.iterdir():
            if (
                file.name in names
                and file.is_file()
                and not file.is_symlink()
                and not file.is_junction()
            ):
                total += file.stat().st_size
    from dusty.app import messages as M

    return M.format_size(total)


def model_status(paths: RuntimePaths) -> dict[str, str]:
    """Verify existing catalog files before Setup describes their upgrade state."""
    from dusty.models import ModelCorrupt, ModelMissing, ModelRegistry, load_manifest

    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    statuses = {}
    for model_id in registry.manifest.models:
        try:
            registry.model_path(model_id)
            statuses[model_id] = "installed"
        except ModelMissing:
            statuses[model_id] = "missing"
        except (ModelCorrupt, OSError, ValueError):
            statuses[model_id] = "damaged"
    return statuses


def cancel_partial(paths: RuntimePaths, model_id: str) -> bool:
    from dusty.models import load_manifest

    manifest = load_manifest(paths.resources_dir / "models.json")
    name = (
        manifest.vad_file_name if model_id == "silero-vad" else manifest.models[model_id].file_name
    )
    part = paths.models_dir / (name + ".part")
    protected = protected_paths(paths.user_dir)
    if (
        linked(part)
        or protected is None
        or any(
            canonical(part).is_relative_to(p) or p.is_relative_to(canonical(part))
            for p in protected
        )
    ):
        return False
    try:
        part.unlink(missing_ok=True)
        return True
    except OSError:
        return False
