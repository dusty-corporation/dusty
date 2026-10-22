"""Keep test application state inside pytest's repository-local workspace."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses inherit this too; tests must not write the Owner's app data."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
