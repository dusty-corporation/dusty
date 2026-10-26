"""Keep test application state inside pytest's repository-local workspace."""

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.test_appdata_guard import install_guard

# Capture before the autouse fixture redirects LOCALAPPDATA for app isolation.
_REAL_WER_ROOTS = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    / "Microsoft/Windows/WER",
    Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/WER",
)


@pytest.fixture
def real_wer_roots() -> tuple[Path, ...]:
    return _REAL_WER_ROOTS


install_guard(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Dusty")


@pytest.fixture(scope="session")
def tls_certificate(tmp_path_factory):
    """Generate a fresh identity in pytest temp space, never in committed fixtures."""
    folder = tmp_path_factory.mktemp("localhost-tls")
    subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(Path(__file__).parent / "fixtures/https/generate.ps1"),
            "-Destination",
            str(folder),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return SimpleNamespace(cert=folder / "localhost.pem", key=folder / "localhost-key.pem")


@pytest.fixture(autouse=True)
def isolate_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses inherit this too; tests must not write the Owner's app data."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
