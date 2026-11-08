"""Packaged Dusty.app first run, upgrade, removal and relocation (P24, P25).

Opt in by building an app with tools/build_macos_app.py and setting
DUSTY_MAC_APP to its Dusty.app, plus DUSTY_MODELS_DIR to a folder holding the
hash verified ggml-tiny.bin and ggml-silero-vad.bin. DUSTY_MAC_APP_OLD may name
an earlier build to upgrade from; without it the same build is installed twice.
The harness is tools/mac_upgrade_check.py. Every scenario uses its own HOME, so the
real data folder is never used. Quarantined launches are left out here because
Gatekeeper may show a dialog; the harness records them when run by hand.
"""

import json
import os
import sys
from pathlib import Path

import pytest

from tools import mac_upgrade_check as check


def _app(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value and (Path(value) / "Contents/MacOS/Dusty").is_file() else None


def _models() -> Path | None:
    value = os.environ.get("DUSTY_MODELS_DIR")
    if not value or not all((Path(value) / name).is_file() for name in check.MODELS):
        return None
    return Path(value)


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or _app("DUSTY_MAC_APP") is None or _models() is None,
    reason="Needs macOS, DUSTY_MAC_APP (a built Dusty.app) and DUSTY_MODELS_DIR with Tiny "
    "and Voice detection",
)


def test_first_run_upgrade_and_removal_keep_models_settings_and_outputs(tmp_path):
    new = _app("DUSTY_MAC_APP")
    old = _app("DUSTY_MAC_APP_OLD") or new
    models = _models()
    assert new is not None and models is not None
    out = tmp_path / "upgrade run"
    arguments = ["--new", str(new), "--old", str(old), "--models", str(models)]
    code = check.main([*arguments, "--out", str(out), "--no-quarantine"])
    rows = json.loads((out / "results.json").read_text(encoding="utf-8"))
    failed = [row for row in rows if row["result"] == "fail"]
    assert code == 0 and not failed, failed
    steps = {row["step"] for row in rows if row["result"] == "pass"}
    assert "new app --installer-status" in steps
    assert "removal step 2: data folder to the Trash" in steps
    assert "moved app --self-test (Auto)" in steps
