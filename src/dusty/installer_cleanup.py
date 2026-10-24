"""Remove only recognized app-owned data, never arbitrary output directories."""

import json
import re
from pathlib import Path

from dusty.models import load_manifest
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import cleanup_owned, linked, protected_paths


def uninstall_allowed(paths: RuntimePaths) -> bool:
    """Inno must not remove registered payload inside a protected destination."""
    try:
        protected = protected_paths(paths.user_dir)
        if protected is None:
            return False
        if paths.install_dir is None:
            return True
        install = paths.install_dir.resolve()
        return not linked(paths.install_dir) and not any(
            p.is_relative_to(install) or install.is_relative_to(p) for p in protected
        )
    except (OSError, ValueError):
        return False


def _cleanup(paths: RuntimePaths, *, remove_models: bool) -> bool:
    """Return False if uncertain data was preserved; emit no paths or content."""
    root = paths.user_dir
    if not root.exists():
        return True
    protected: set[Path] = set()
    metadata = [root / "settings.json", root / "state/queue.json"]
    metadata += list(root.glob("settings.json.corrupt-*"))
    metadata += list((root / "state").glob("queue.json.corrupt-*"))

    def inspect(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for name, item in value.items():
                inspect(item, name)
        elif isinstance(value, list):
            for item in value:
                inspect(item, key)
        elif key in {"output_dir", "outputs", "source", "preserved_paths"} and isinstance(
            value, str
        ):
            protected.add(Path(value).resolve())

    try:
        # Reparse points anywhere in the owned subtree make cleanup uncertain.
        if linked(root) or any(linked(p) for p in root.rglob("*")):
            return False
        for path in metadata:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or data.get("schema_version") != 1:
                    return False
                inspect(data)
        owned_root = root.resolve()
        if any(p.is_relative_to(owned_root) or owned_root.is_relative_to(p) for p in protected):
            return False
        candidates = list(metadata)
        candidates += [
            p for p in (root / "logs").glob("*") if re.fullmatch(r"dusty\.log(?:\.[1-5])?", p.name)
        ]
        ownership_protection = protected_paths(root)
        for directory in (root / "work").glob("*"):
            if directory.is_dir():
                cleanup_owned(directory, protected=ownership_protection)
        if remove_models:
            manifest = load_manifest(paths.resources_dir / "models.json")
            names = [m.file_name for m in manifest.models.values()] + [manifest.vad_file_name]
            candidates += [
                root / "models" / (name + suffix)
                for name in names
                for suffix in ("", ".part", ".lock")
            ]
        # Decide before deleting metadata: another attempt must retain protection.
        for path in candidates:
            resolved = path.resolve()
            if any(resolved == p or resolved.is_relative_to(p) for p in protected):
                return False
        for path in candidates:
            if path.is_file():
                path.unlink()
        # Only empty directories disappear. Unknown files and user outputs stay.
        directories = sorted(
            (p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True
        )
        for path in [*directories, root]:
            if path != root / "work" and path.is_relative_to(root / "work"):
                # Even an empty unmarked work folder is not proven app-owned.
                continue
            resolved = path.resolve()
            if any(
                resolved == p or resolved.is_relative_to(p) or p.is_relative_to(resolved)
                for p in protected
            ):
                continue
            if not remove_models and (
                path == root / "models" or path.is_relative_to(root / "models")
            ):
                continue
            try:
                path.rmdir()
            except OSError:
                pass
        remaining = list(root.iterdir()) if root.exists() else []
        return not any(remove_models or p != root / "models" for p in remaining)
    except (OSError, ValueError, TypeError):
        return False


def cleanup(paths: RuntimePaths, *, remove_models: bool) -> bool:
    """Contain filesystem failures even during initial metadata discovery."""
    try:
        if not uninstall_allowed(paths):
            return False
        return _cleanup(paths, remove_models=remove_models)
    except (OSError, ValueError, TypeError):
        return False
