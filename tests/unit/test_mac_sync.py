"""Discover Mac warning roots from local metadata without traversing cloud content."""

import json
import sys
from pathlib import Path

import pytest

from dusty.privacy.sync import is_synced, sync_roots

# Mac-only gates: each reason names the macOS mechanism that Windows lacks.
mac_dropbox_config = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="Mac Dropbox discovery opens its config with O_DIRECTORY and O_NOFOLLOW",
)
mac_fifo = pytest.mark.skipif(sys.platform != "darwin", reason="needs POSIX FIFOs (os.mkfifo)")


def test_icloud_and_file_provider_children_warn_without_reading_content(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cloud = home / "Library/CloudStorage"
    providers = [
        cloud / "Dropbox-Personal",
        cloud / "GoogleDrive-test@example.invalid",
        cloud / "OneDrive-Personal",
    ]
    icloud = home / "Library/Mobile Documents/com~apple~CloudDocs"
    for directory in [icloud, *providers]:
        directory.mkdir(parents=True)
        (directory / "private.wav").write_bytes(b"not opened by discovery")
    (cloud / "ordinary-file").write_bytes(b"not a provider root")
    original = Path.iterdir

    def list_only_container(path):
        assert path == cloud
        return original(path)

    monkeypatch.setattr(Path, "iterdir", list_only_container)

    def no_read(*args, **kwargs):
        raise AssertionError("No cloud content should be read")

    monkeypatch.setattr(Path, "read_text", no_read)
    monkeypatch.setattr(Path, "read_bytes", no_read)
    roots = sync_roots({"HOME": str(home)}, platform="darwin")
    assert set(roots) == {root.resolve() for root in [icloud, *providers]}
    assert is_synced(providers[0] / "future/output.txt", roots)
    assert not is_synced(home / "Desktop/output.txt", roots)
    assert not is_synced(home / "Documents/output.txt", roots)
    assert not is_synced(cloud / "Dropbox-Personal-old/output.txt", roots)


@mac_dropbox_config
def test_dropbox_reads_only_supported_config_and_all_valid_accounts(tmp_path):
    home = tmp_path / "home"
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    personal = tmp_path / "Custom Dropbox"
    team = tmp_path / "Team Dropbox"
    info.write_text(
        json.dumps(
            {
                "personal": {"path": str(personal), "host": "DO_NOT_LOG"},
                "business": {"path": str(team)},
                "bad": {"path": 3},
            }
        )
    )
    roots = sync_roots({"HOME": str(home)}, platform="darwin")
    assert set(roots) == {personal.resolve(), team.resolve()}


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "[]",
        "null",
        '{"personal":null}',
        '{"personal":{"path":""}}',
        '{"personal":{"path":"relative"}}',
        '{"personal":{"path":"//remote/share"}}',
        '{"personal":{"path":"https://example.invalid"}}',
        '{"personal":{"path":"/tmp/\\u0000bad"}}',
    ],
)
def test_bad_dropbox_config_does_not_create_root(tmp_path, payload):
    home = tmp_path / "home"
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    info.write_text(payload)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


def test_mac_does_not_fall_back_to_real_home_or_other_platform(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("Explicit env must not read actual HOME")

    monkeypatch.setattr(Path, "home", forbidden)
    assert sync_roots({}, platform="darwin") == ()
    assert sync_roots({"HOME": "relative"}, platform="darwin") == ()
    assert sync_roots({"HOME": str(tmp_path)}, platform="linux") == ()


def test_unreadable_cloudstorage_is_not_a_crash(tmp_path, monkeypatch):
    home = tmp_path / "home"
    cloud = home / "Library/CloudStorage"
    cloud.mkdir(parents=True)

    def denied(path):
        raise PermissionError("private path not logged")

    monkeypatch.setattr(Path, "iterdir", denied)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


def test_mac_config_symlink_not_read(tmp_path):
    home = tmp_path / "home"
    folder = home / ".dropbox"
    folder.mkdir(parents=True)
    private = tmp_path / "private-recording"
    private.write_text(json.dumps({"personal": {"path": str(tmp_path / "not-trusted")}}))
    (folder / "info.json").symlink_to(private)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


def test_windows_environment_detection_is_preserved_on_mac(tmp_path):
    appdata = tmp_path / "appdata"
    info = appdata / "Dropbox/info.json"
    info.parent.mkdir(parents=True)
    root = tmp_path / "WindowsDropbox"
    info.write_text(json.dumps({"personal": {"path": str(root)}}))
    (tmp_path / "Google Drive").mkdir()
    env = {
        "APPDATA": str(appdata),
        "USERPROFILE": str(tmp_path),
        "OneDrive": str(tmp_path / "OneDrive"),
    }
    assert set(sync_roots(env, platform="win32")) == {
        root.resolve(),
        (tmp_path / "Google Drive").resolve(),
        (tmp_path / "OneDrive").resolve(),
    }


def test_unreadable_dropbox_config_is_ignored_without_logging(tmp_path, monkeypatch, caplog):
    import os

    home = tmp_path / "home"
    (home / ".dropbox").mkdir(parents=True)

    def denied(*args, **kwargs):
        raise PermissionError("CANARY private config path")

    monkeypatch.setattr(os, "open", denied)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()
    assert not caplog.records


def test_dropbox_placeholder_is_not_opened(tmp_path, monkeypatch):
    import os
    from types import SimpleNamespace

    home = tmp_path / "home"
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    info.write_text("{}")
    original_stat = os.stat
    original_open = os.open

    def metadata(path, *args, **kwargs):
        value = original_stat(path, *args, **kwargs)
        if path == "info.json":
            return SimpleNamespace(
                st_mode=value.st_mode, st_size=value.st_size, st_flags=0x40000000
            )
        return value

    def directory_only(path, *args, **kwargs):
        assert path == info.parent
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", metadata)
    monkeypatch.setattr(os, "open", directory_only)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


@pytest.mark.parametrize(
    "kind",
    ["directory", pytest.param("fifo", marks=mac_fifo), "oversized", "deep-json"],
)
def test_nonregular_large_or_deep_dropbox_config_is_ignored(tmp_path, kind):
    import os

    home = tmp_path / "home"
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    if kind == "directory":
        info.mkdir()
    elif kind == "fifo":
        os.mkfifo(info)
    elif kind == "oversized":
        info.write_bytes(b" " * (1024 * 1024 + 1))
    else:
        info.write_text("[" * 2000 + "]" * 2000)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


def test_dropbox_directory_symlink_is_not_traversed(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "info.json").write_text(json.dumps({"personal": {"path": str(tmp_path / "root")}}))
    (home / ".dropbox").symlink_to(elsewhere, target_is_directory=True)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


@mac_dropbox_config
def test_missing_providers_and_duplicate_config_roots(tmp_path):
    home = tmp_path / "home"
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    root = tmp_path / "Dropbox"
    info.write_text(json.dumps({"personal": {"path": str(root)}, "business": {"path": str(root)}}))
    assert sync_roots({"HOME": str(home)}, platform="darwin") == (root.resolve(),)


@pytest.mark.parametrize("payload", ["{}", "malformed", "[" * 2000 + "]" * 2000])
def test_dropbox_config_handles_are_closed_on_success_and_parse_failure(
    tmp_path, monkeypatch, payload
):
    import os

    home = tmp_path / "home"
    info = home / ".dropbox/info.json"
    info.parent.mkdir(parents=True)
    info.write_text(payload)
    opened = set()
    original_open = os.open
    original_close = os.close

    def tracked_open(*args, **kwargs):
        descriptor = original_open(*args, **kwargs)
        opened.add(descriptor)
        return descriptor

    def tracked_close(descriptor):
        original_close(descriptor)
        opened.remove(descriptor)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(os, "close", tracked_close)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()
    assert not opened


@pytest.mark.parametrize(
    "name",
    [
        "Dropbox",
        "Dropbox-Personal",
        "Dropbox - Personal",
        "Dropbox \u2013 Work Team",
        "Dropbox (Personal)",
        "Dropbox (Work Team)",
        "OneDrive-Personal",
        "OneDrive-Contoso",
        "OneDrive - Contoso",
        "GoogleDrive-test@example.invalid",
    ],
)
def test_known_file_provider_names_warn(tmp_path, name):
    home = tmp_path / "home"
    provider = home / "Library/CloudStorage" / name
    provider.mkdir(parents=True)
    roots = sync_roots({"HOME": str(home)}, platform="darwin")
    assert roots == (provider.resolve(),)
    assert is_synced(provider / "new/output.txt", roots)


@pytest.mark.parametrize(
    "name",
    [
        "DropboxBackup",
        "DropboxBackup-Personal",
        "NotOneDrive",
        "NotOneDrive-Personal",
        "GoogleDriveBackup-account",
        "Unrelated",
        "UnknownProvider-Account",
        "OneDrive",
        "Dropbox-",
        "OneDrive-",
        "GoogleDrive-",
        "Dropbox - ",
        "Dropbox ()",
        "Dropbox -  ",
    ],
)
def test_unknown_or_lookalike_provider_names_do_not_warn(tmp_path, name):
    home = tmp_path / "home"
    provider = home / "Library/CloudStorage" / name
    provider.mkdir(parents=True)
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()


@pytest.mark.parametrize("name", ["Dropbox", "OneDrive-Personal", "GoogleDrive-account"])
def test_known_provider_spelling_on_a_regular_file_is_not_a_root(tmp_path, name):
    home = tmp_path / "home"
    candidate = home / "Library/CloudStorage" / name
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"not a provider directory")
    assert sync_roots({"HOME": str(home)}, platform="darwin") == ()
