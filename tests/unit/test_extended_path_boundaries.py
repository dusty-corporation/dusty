"""Windows extended namespace aliases cannot bypass managed/protected roots."""

from pathlib import Path

from dusty.installer_cleanup import cleanup, uninstall_allowed
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import canonical, managed_destination


def test_extended_alias_is_blocked_and_protected_before_uninstall(tmp_path):
    install = tmp_path / "app"
    resources = install / "resources"
    resources.mkdir(parents=True)
    sentinel = resources / "models.json"
    sentinel.write_bytes(b"synthetic private transcript, never remove")
    user = tmp_path / "user"
    paths = RuntimePaths(install / "bin", user / "models", resources, user, install)
    alias = Path("\\\\?\\" + str(resources.resolve()))
    assert canonical(alias) == canonical(resources)
    assert managed_destination(alias, paths)
    save_settings(user / "settings.json", {"schema_version": 1, "preserved_paths": [str(alias)]})
    assert not uninstall_allowed(paths)
    assert not cleanup(paths, remove_models=True)
    assert sentinel.read_bytes() == b"synthetic private transcript, never remove"
    assert (user / "settings.json").is_file()


def test_drive_and_unc_namespace_normalization():
    assert canonical(Path(r"\\?\C:\Windows")) == canonical(Path(r"C:\Windows"))
    # Pure spelling check: no share is opened or created by this assertion.
    from unittest.mock import patch

    path = Path(r"\\?\UNC\fixture-server\share\folder")
    with patch.object(type(path), "resolve", return_value=path):
        assert str(canonical(path)) == r"\\fixture-server\share\folder"
