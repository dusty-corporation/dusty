"""Identify common sync roots for a local storage warning."""

import json
import os
from pathlib import Path


def sync_roots(environment: dict[str, str] | None = None) -> tuple[Path, ...]:
    """Discover local OneDrive, Dropbox and Google Drive roots without network access."""
    env = os.environ if environment is None else environment
    roots = [
        Path(value)
        for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")
        if (value := env.get(key))
    ]
    for appdata in {env.get("APPDATA"), env.get("LOCALAPPDATA")} - {None, ""}:
        info = Path(str(appdata)) / "Dropbox/info.json"
        try:
            data = json.loads(info.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                roots.extend(
                    Path(item["path"])
                    for item in data.values()
                    if isinstance(item, dict) and isinstance(item.get("path"), str)
                )
        except (OSError, ValueError, TypeError):
            pass
    profile = env.get("USERPROFILE")
    if profile:
        for name in ("Google Drive", "My Drive"):
            candidate = Path(profile) / name
            if candidate.exists():
                roots.append(candidate)
    return tuple(root.resolve() for root in roots)


def is_synced(path: Path, roots: tuple[Path, ...] | None = None) -> bool:
    """Return a warning signal when a destination is below a known sync root."""
    destination = path.resolve()
    selected = sync_roots() if roots is None else roots
    return any(destination == root or root in destination.parents for root in selected)
