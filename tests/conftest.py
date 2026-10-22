"""Keep test application state inside pytest's repository-local workspace."""

import os
from pathlib import Path

import pytest

from tools.test_appdata_guard import install_guard

install_guard(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Dusty")


@pytest.fixture(autouse=True)
def isolate_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses inherit this too; tests must not write the Owner's app data."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
