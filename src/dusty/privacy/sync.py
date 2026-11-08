"""Identify common sync roots for a local storage warning."""

import json
import os
import sys
from pathlib import Path

from dusty.platform.sync_locations import google_drive_roots, mac_sync_roots


def sync_roots(
    environment: dict[str, str] | None = None, *, platform: str | None = None
) -> tuple[Path, ...]:
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
    roots.extend(google_drive_roots(env))
    if (sys.platform if platform is None else platform) == "darwin":
        roots.extend(mac_sync_roots(env))
    resolved = []
    for root in roots:
        try:
            normalized = root.resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if normalized not in resolved:
            resolved.append(normalized)
    return tuple(resolved)


def is_synced(path: Path, roots: tuple[Path, ...] | None = None) -> bool:
    """Return a warning signal when a destination is below a known sync root."""
    destination = path.resolve()
    selected = sync_roots() if roots is None else roots
    return any(destination == root or root in destination.parents for root in selected)
