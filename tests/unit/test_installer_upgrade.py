"""True upgrades must remove only unchanged obsolete own-license copies."""

from dataclasses import replace
from pathlib import Path

import pytest

from dusty.installer_upgrade import tidy_license_copies
from dusty.runtime_paths import resolve_paths


@pytest.fixture
def upgrade(tmp_path):
    paths = replace(
        resolve_paths(), resources_dir=tmp_path / "new/resources", user_dir=tmp_path / "user"
    )
    source = paths.resources_dir.parent / "licenses/dusty/dusty-0.5.0.dev9.dist-info/licenses"
    old = tmp_path / "installed/licenses/dusty/dusty-0.5.0.dev4.dist-info/licenses"
    for folder in (source, old):
        folder.mkdir(parents=True)
        (folder / "LICENSE").write_bytes(b"same Apache license")
        (folder / "NOTICE").write_bytes(b"same copyright notice")
    return paths, tmp_path / "installed", old


def test_upgrade_removes_only_matching_old_notice_copies(upgrade):
    paths, install, old = upgrade
    assert tidy_license_copies(paths, install)
    assert not old.parent.exists()
    assert (
        paths.resources_dir.parent / "licenses/dusty/dusty-0.5.0.dev9.dist-info/licenses/LICENSE"
    ).exists()


@pytest.mark.parametrize("change", ["receipt", "remaining-file", "unknown-file"])
def test_interrupted_upgrade_does_not_adopt_changed_contents(upgrade, monkeypatch, change):
    from dusty.installer_upgrade import RECEIPT

    paths, install, old = upgrade
    unlink = Path.unlink

    def crash(file, *args, **kwargs):
        unlink(file, *args, **kwargs)
        raise SystemExit(91)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", crash)
        with pytest.raises(SystemExit):
            tidy_license_copies(paths, install)
    assert (old / "NOTICE").exists()
    if change == "receipt":
        (old.parent / RECEIPT).write_bytes(b"unknown marker")
    elif change == "remaining-file":
        (old / "NOTICE").write_bytes(b"user contents")
    else:
        (old / "user.txt").write_bytes(b"user contents")
    before = (old / "NOTICE").read_bytes()
    assert not tidy_license_copies(paths, install)
    assert (old / "NOTICE").read_bytes() == before


@pytest.mark.parametrize("change", ["modified", "unknown", "symlink", "protected"])
def test_upgrade_preserves_unproven_license_folder(upgrade, change, tmp_path):
    paths, install, old = upgrade
    if change == "modified":
        (old / "NOTICE").write_bytes(b"user content")
    elif change == "unknown":
        (old / "keep.txt").write_bytes(b"user content")
    elif change == "symlink":
        target = tmp_path / "outside"
        target.write_bytes(b"user content")
        (old / "NOTICE").unlink()
        (old / "NOTICE").symlink_to(target)
    else:
        from dusty.queue.storage import save_settings

        save_settings(
            paths.user_dir / "settings.json", {"schema_version": 1, "output_dir": str(old)}
        )
    before = (old / "LICENSE").read_bytes()
    assert not tidy_license_copies(paths, install)
    assert (old / "LICENSE").read_bytes() == before
    assert (old / "NOTICE").exists()
