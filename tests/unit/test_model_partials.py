"""Startup prefix retention is local, bounded by age and never follows entries."""

import os
from pathlib import Path

from dusty.models import cleanup_stale_partials
from dusty.models.partials import PARTIAL_MAX_AGE_SEC


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
    os.utime(part, (0, 0))
    original = Path.unlink

    def locked(path, *args, **kwargs):
        if path == part:
            raise PermissionError("Test locked prefix")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked)
    assert cleanup_stale_partials(tmp_path) == 0
    assert part.read_bytes() == b"data"
