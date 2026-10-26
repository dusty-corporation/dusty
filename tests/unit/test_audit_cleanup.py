"""Independent audit F-01: ancestor outputs do not disable owned cleanup."""

import json
from pathlib import Path

import pytest

from dusty.installer_cleanup import cleanup, uninstall_allowed
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("ancestor", ["home", "drive", "local"])
def test_ancestor_output_allows_owned_work_and_uninstall(tmp_path, ancestor):
    home = tmp_path / "home"
    local = home / "AppData/Local"
    user = local / "Dusty"
    output = {"home": home, "drive": Path(tmp_path.anchor), "local": local}[ancestor]
    save_settings(user / "settings.json", {"schema_version": 1, "output_dir": str(output)})
    work = OwnedWork(user / "work", "job")
    for name in ("audio.wav", "raw.json"):
        (work.path / name).write_bytes(b"synthetic owned content")
    work.record("audio.wav", "raw.json")
    assert work.cleanup(user)
    assert not work.path.exists()
    paths = RuntimePaths(
        local / "Programs/Dusty/bin",
        user / "models",
        ROOT / "resources",
        user,
        local / "Programs/Dusty",
    )
    assert uninstall_allowed(paths)
    assert cleanup(paths, remove_models=True)
    assert not user.exists()


def test_unparseable_backup_does_not_disable_owned_cleanup(tmp_path):
    user = tmp_path / "Dusty"
    user.mkdir()
    (user / "settings.json.corrupt-test").write_text("{broken")
    work = OwnedWork(user / "work", "job")
    (work.path / "audio.wav").write_bytes(b"owned")
    work.record("audio.wav")
    assert work.cleanup(user)
    assert not work.path.exists()


def test_same_folder_has_no_placeholder_output_in_persistence(tmp_path):
    from dusty.core import BatchOptions
    from dusty.queue.storage import load_batch, save_batch

    options = BatchOptions("tiny", None, same_folder=True)
    path = tmp_path / "queue.json"
    save_batch(path, options, [])
    assert json.loads(path.read_text())["options"]["output_dir"] is None
    assert load_batch(path)[0].output_dir is None
