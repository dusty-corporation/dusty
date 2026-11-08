"""Pure helpers of tools/mac_upgrade_check.py (P24, P25 harness)."""

import os
from pathlib import Path

from tools import mac_upgrade_check as check


def test_snapshot_sees_content_identity_and_skips_named_folders(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/dusty.log").write_text("a")
    (tmp_path / "settings.json").write_text("{}")
    before = check.snapshot(tmp_path, skip=("logs",))
    assert sorted(before) == ["settings.json"]
    (tmp_path / "logs/dusty.log").write_text("ab")
    assert check.differences(before, check.snapshot(tmp_path, skip=("logs",))) == []
    (tmp_path / "settings.json").write_text("{ }")
    assert check.differences(before, check.snapshot(tmp_path, skip=("logs",))) == ["settings.json"]


def test_replaced_file_with_same_bytes_and_time_is_a_difference(tmp_path):
    """A model downloaded again (new file renamed over it) differs even if it matches."""
    model = tmp_path / "ggml-tiny.bin"
    model.write_bytes(b"weights")
    before = check.snapshot(tmp_path)
    fresh = tmp_path / "ggml-tiny.bin.part"
    fresh.write_bytes(b"weights")  # Both exist at once, so the inodes differ.
    mtime = before["ggml-tiny.bin"][4]
    os.utime(fresh, ns=(mtime, mtime))
    fresh.replace(model)
    after = check.snapshot(tmp_path)
    assert after["ggml-tiny.bin"][1:3] == before["ggml-tiny.bin"][1:3]
    assert check.differences(before, after) == ["ggml-tiny.bin"]


def test_bundle_listing_compares_content_and_links_not_inodes(tmp_path):
    first, second = tmp_path / "A.app", tmp_path / "B.app"
    for app in (first, second):
        (app / "Contents/MacOS").mkdir(parents=True)
        (app / "Contents/MacOS/Dusty").write_bytes(b"code")
        os.symlink("MacOS/Dusty", app / "Contents/link")
    assert check.differences(check.bundle_listing(first), check.bundle_listing(second)) == []
    (second / "Contents/old-only.txt").write_text("left over")
    assert check.differences(check.bundle_listing(first), check.bundle_listing(second)) == [
        "Contents/old-only.txt"
    ]


def test_trash_uses_free_names_like_finder(tmp_path):
    home = tmp_path / "home"
    for _ in range(3):
        (tmp_path / "Dusty.app").mkdir()
        check.trash(tmp_path / "Dusty.app", home)
    assert sorted(p.name for p in (home / ".Trash").iterdir()) == [
        "Dusty 2.app",
        "Dusty 3.app",
        "Dusty.app",
    ]
    (home / "Library/Application Support").mkdir(parents=True)
    assert check.leftovers(home) == ["Library", "Library/Application Support"]


def test_redact_removes_run_and_home_paths(tmp_path):
    text = f"{tmp_path}/p25/home and {Path.home()}/x"
    assert check.redact(text, tmp_path) == "<out>/p25/home and <home>/x"


def test_cpu_results_are_expected_only_inside_a_virtual_mac():
    virtual = {"ok": False, "unsupported": True, "virtual_mac": True, "device_name": None}
    assert check.virtual_mac(virtual)
    # A real Mac, a GPU the engine itself reported unusable, or a failed check
    # must still pass the Metal rows.
    for probe in (
        {**virtual, "virtual_mac": False},
        {key: value for key, value in virtual.items() if key != "virtual_mac"},
        {**virtual, "unsupported": False},
        {"ok": False, "unsupported": True, "device_name": "Apple Paravirtual device"},
        {"ok": True, "device_name": "Apple M1"},
        {},
    ):
        assert not check.virtual_mac(probe)
