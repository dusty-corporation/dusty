"""Startup prefix retention is local, bounded by age and never follows entries."""

import os
from pathlib import Path

from dusty.models import cleanup_stale_partials
from dusty.models.partials import PARTIAL_MAX_AGE_SEC
from dusty_fetch.downloader import record_partial


def test_partial_age_boundary_and_non_partial_files(tmp_path):
    now = 2_000_000_000.0
    for name, age in (
        ("stale.part", PARTIAL_MAX_AGE_SEC + 1),
        ("recent.part", 60),
        ("boundary.part", PARTIAL_MAX_AGE_SEC),
        ("final.bin", PARTIAL_MAX_AGE_SEC + 1),
    ):
        path = tmp_path / name
        path.write_bytes(b"data")
        record_partial(path)
        os.utime(path, (now - age, now - age))
    nested = tmp_path / "nested.part"
    nested.mkdir()
    protected = nested / "keep.part"
    protected.write_bytes(b"preserve")
    assert cleanup_stale_partials(tmp_path, now=now) == 1
    assert not (tmp_path / "stale.part").exists()
    for name in ("recent.part", "boundary.part", "final.bin"):
        assert (tmp_path / name).read_bytes() == b"data"
    assert protected.read_bytes() == b"preserve"
    assert cleanup_stale_partials(tmp_path / "absent", now=now) == 0


def test_busy_partial_does_not_break_startup(tmp_path, monkeypatch):
    part = tmp_path / "busy.part"
    part.write_bytes(b"data")
    record_partial(part)
    os.utime(part, (0, 0))
    original = Path.unlink

    def locked(path, *args, **kwargs):
        if path == part:
            raise PermissionError("Test locked prefix")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked)
    assert cleanup_stale_partials(tmp_path) == 0
    assert part.read_bytes() == b"data"


def test_unknown_or_modified_stale_prefix_is_preserved(tmp_path):
    unknown = tmp_path / "unknown.part"
    unknown.write_bytes(b"user data")
    changed = tmp_path / "changed.part"
    changed.write_bytes(b"prefix")
    record_partial(changed)
    changed.write_bytes(b"user replacement")
    for file in (unknown, changed):
        os.utime(file, (0, 0))
    assert cleanup_stale_partials(tmp_path) == 0
    assert unknown.read_bytes() == b"user data"
    assert changed.read_bytes() == b"user replacement"


def test_stale_partial_in_saved_output_folder_is_not_deleted(tmp_path):
    from dusty.queue.storage import save_settings

    directory = tmp_path / "user/models"
    directory.mkdir(parents=True)
    part = directory / "clip.part"
    part.write_bytes(b"user transcript")
    record_partial(part)
    os.utime(part, (0, 0))
    save_settings(
        directory.parent / "settings.json", {"schema_version": 1, "output_dir": str(directory)}
    )
    assert cleanup_stale_partials(directory) == 0
    assert part.read_bytes() == b"user transcript"
    (directory.parent / "settings.json").write_text("{broken")
    assert cleanup_stale_partials(directory) == 0
    assert part.exists()


def test_invalid_partial_receipt_is_preserved(tmp_path):
    part = tmp_path / "old.part"
    part.write_bytes(b"prefix")
    receipt = tmp_path / "old.lock"
    receipt.write_bytes(b"0{broken")
    os.utime(part, (0, 0))
    assert cleanup_stale_partials(tmp_path) == 0
    assert part.read_bytes() == b"prefix"


def test_linked_partial_receipt_never_deletes_the_prefix(tmp_path):
    part = tmp_path / "old.part"
    part.write_bytes(b"prefix")
    record_partial(part)
    receipt = tmp_path / "old.lock"
    outside = tmp_path / "outside"
    receipt.rename(outside)
    receipt.symlink_to(outside)
    os.utime(part, (0, 0))
    assert cleanup_stale_partials(tmp_path) == 0
    assert part.exists() and outside.exists()
    receipt.unlink()
