"""Resolve development and installed binary, resource, and model locations."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    bin_dir: Path
    models_dir: Path
    resources_dir: Path
    user_dir: Path


def resolve_paths(
    *,
    frozen: bool | None = None,
    executable: Path | None = None,
    repo_root: Path | None = None,
    environment: dict[str, str] | None = None,
) -> RuntimePaths:
    """Use installed paths for frozen builds and configurable paths in source trees."""
    env = os.environ if environment is None else environment
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    app_executable = Path(sys.executable) if executable is None else executable
    root = Path(__file__).resolve().parents[2] if repo_root is None else repo_root
    local_appdata = Path(env.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    user_dir = local_appdata / "Dusty"
    if installed:
        app_dir = app_executable.parent
        return RuntimePaths(app_dir / "bin", user_dir / "models", app_dir / "resources", user_dir)
    bin_dir = Path(env["DUSTY_BIN_DIR"]) if env.get("DUSTY_BIN_DIR") else root / "build/bin"
    models_dir = (
        Path(env["DUSTY_MODELS_DIR"]) if env.get("DUSTY_MODELS_DIR") else root / "build/models"
    )
    return RuntimePaths(bin_dir, models_dir, root / "resources", user_dir)


def resolve_fetch_command(
    *, frozen: bool | None = None, executable: Path | None = None
) -> list[str]:
    """The downloader is always a separate process, including split onedir builds."""
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    app = Path(sys.executable) if executable is None else executable
    if installed:
        return [str((app.parent.parent / "dusty-fetch/dusty-fetch.exe").resolve())]
    return [str(app.resolve()), "-m", "dusty_fetch"]
