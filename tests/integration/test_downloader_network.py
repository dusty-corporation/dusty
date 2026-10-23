"""One explicit CI-only integration against the published Tiny release."""

import os
from pathlib import Path

import pytest

from dusty_fetch.__main__ import main


@pytest.mark.real_network
@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("DUSTY_CI_REAL_NETWORK") != "1",
    reason="Requires explicit CI-only network opt-in",
)
def test_download_and_verify_published_tiny(tmp_path: Path):
    manifest = Path(__file__).resolve().parents[2] / "resources/models.json"
    arguments = ["--id", "tiny", "--dest", str(tmp_path / "tiny"), "--manifest", str(manifest)]
    assert main(["download", *arguments]) == 0
    assert main(["verify", *arguments]) == 0
