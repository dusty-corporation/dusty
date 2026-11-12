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
    install_dir: Path | None = None


def _mac_contents(executable: Path) -> Path:
    """Validate bundle shape without resolving links or touching the filesystem."""
    contents = executable.parent.parent
    if (
        not executable.is_absolute()
        or executable.parent.name != "MacOS"
        or contents.name != "Contents"
        or contents.parent.suffix.casefold() != ".app"
        or ".." in executable.parts
    ):
        raise ValueError("Mac app executable must be inside an absolute .app/Contents/MacOS path")
    return contents


def resolve_paths(
    *,
    frozen: bool | None = None,
    executable: Path | None = None,
    repo_root: Path | None = None,
    environment: dict[str, str] | None = None,
    platform: str | None = None,
) -> RuntimePaths:
    """Use installed paths for frozen builds and configurable paths in source trees."""
    env = os.environ if environment is None else environment
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    selected_platform = sys.platform if platform is None else platform
    app_executable = Path(sys.executable) if executable is None else executable
    default_data = (
        Path.home() / "Library/Application Support"
        if selected_platform == "darwin"
        else Path.home() / "AppData/Local"
    )
    local_appdata = Path(env.get("LOCALAPPDATA", str(default_data)))
    user_dir = local_appdata / "Dusty"
    if installed:
        if selected_platform == "darwin":
            contents = _mac_contents(app_executable)
            return RuntimePaths(
                contents / "Helpers/bin",
                user_dir / "models",
                contents / "Resources",
                user_dir,
                contents.parent,
            )
        app_dir = app_executable.parent.parent
        return RuntimePaths(
            app_dir / "bin", user_dir / "models", app_dir / "resources", user_dir, app_dir
        )
    root = Path(__file__).resolve().parents[2] if repo_root is None else repo_root
    bin_dir = Path(env["DUSTY_BIN_DIR"]) if env.get("DUSTY_BIN_DIR") else root / "build/bin"
    models_dir = (
        Path(env["DUSTY_MODELS_DIR"]) if env.get("DUSTY_MODELS_DIR") else root / "build/models"
    )
    return RuntimePaths(bin_dir, models_dir, root / "resources", user_dir)


def resolve_fetch_command(
    *,
    frozen: bool | None = None,
    executable: Path | None = None,
    platform: str | None = None,
) -> list[str]:
    """The downloader is always a separate process, including split onedir builds.

    In a macOS source tree the venv interpreter is a symbolic link, which the
    runner refuses, so the command names the real interpreter it points to.
    That interpreter has no venv, so it runs with -S (no site module, so no
    site-packages or .pth files) and -P (no working directory or script folder
    on sys.path). The only extra import location is the exact repository src
    folder, which resolve_fetch_environment supplies. dusty_fetch needs only the
    standard library, so this matches the frozen helper's import surface.
    """
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    selected_platform = sys.platform if platform is None else platform
    app = Path(sys.executable) if executable is None else executable
    if installed:
        if selected_platform == "darwin":
            contents = _mac_contents(app)
            return [str(contents / "Helpers/dusty-fetch/dusty-fetch")]
        return [str((app.parent.parent / "dusty-fetch/dusty-fetch.exe").resolve())]
    if selected_platform == "darwin":
        return [str(app.resolve()), "-S", "-P", "-m", "dusty_fetch"]
    return [str(app.resolve()), "-m", "dusty_fetch"]


def resolve_helper_command(
    name: str,
    module: str,
    *,
    frozen: bool | None = None,
    executable: Path | None = None,
    platform: str | None = None,
) -> list[str]:
    """An extension's helper program is its own process, frozen next to dusty-fetch.

    In a source tree it is the real interpreter running ``-m module``. On macOS
    that is the interpreter the venv links to, started with -S and -P like the
    downloader; the add-on gives it the exact environment it needs.
    """
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    selected_platform = sys.platform if platform is None else platform
    app = Path(sys.executable) if executable is None else executable
    if installed:
        if selected_platform == "darwin":
            contents = _mac_contents(app)
            return [str(contents / f"Helpers/{name}/{name}")]
        return [str((app.parent.parent / f"{name}/{name}.exe").resolve())]
    if selected_platform == "darwin":
        return [str(app.resolve()), "-S", "-P", "-m", module]
    return [str(app.resolve()), "-m", module]


def resolve_fetch_environment(
    *,
    frozen: bool | None = None,
    source_root: Path | None = None,
) -> dict[str, str]:
    """The complete macOS downloader environment; nothing else is inherited.

    LC_ALL=C is the same fixed locale every child gets, so the interpreter
    starts in its UTF-8 mode whatever the user's locale is. The downloader
    reads no HOME, TMPDIR, proxy or certificate variables: every path arrives
    as an argument, proxies are disabled and trust comes only from the code.
    A source tree also needs PYTHONPATH set to its exact src folder, because
    the command runs the real interpreter without the venv.
    """
    installed = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    environment = {"LC_ALL": "C"}
    if not installed:
        src = Path(__file__).resolve().parents[1] if source_root is None else source_root
        environment["PYTHONPATH"] = str(src)
    return environment
