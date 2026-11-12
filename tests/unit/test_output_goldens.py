"""Dusty without extensions writes what Dusty 1.2.0 wrote, byte for byte.

The goldens in tests/fixtures/goldens-1.2.0 were made by
tools/make_output_goldens.py from the 1.2.0 source (49f698e). The same
scenarios run here against the current source.

A saved queue writes each file location with the separator of the computer, as
1.2.0 did, so Windows has its own queue file, made from the 1.2.0 source on Windows.
"""

import io
import sys
import zipfile
from pathlib import Path

import pytest

from dusty import __version__, extensions
from tools import make_output_goldens as goldens

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests/fixtures/goldens-1.2.0"
QUEUE = GOLDEN / ("win32/queue.json" if sys.platform == "win32" else "queue.json")


def docx_parts(data: bytes) -> list[tuple[str, int, bytes]]:
    """Entry names, order, compression and contents; not the time each was written."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return [
            (info.filename, info.compress_type, archive.read(info)) for info in archive.infolist()
        ]


def as_current_version(golden: Path) -> bytes:
    """The golden's bytes with 1.2.0's app version, written once in each JSON
    output, replaced by this version; nothing else may differ."""
    data = golden.read_bytes()
    if golden.suffix != ".json" or "/outputs/" not in golden.as_posix():
        return data
    old = b'"app_version": "1.2.0"'
    assert data.count(old) == 1, golden.name
    return data.replace(old, f'"app_version": "{__version__}"'.encode())


def assert_same(new: Path, golden: Path) -> None:
    if golden.suffix == ".docx":
        assert docx_parts(new.read_bytes()) == docx_parts(golden.read_bytes()), golden.name
    else:
        assert new.read_bytes() == as_current_version(golden), golden.name


def test_the_goldens_cover_every_format_and_scenario() -> None:
    names = sorted(path.name for path in (GOLDEN / "outputs").iterdir())
    assert names == sorted(
        f"{transcript}-{extras}.{fmt}"
        for transcript in ("english", "persian")
        for extras in goldens.EXTRAS
        for fmt in goldens.FORMATS
    )


@pytest.mark.parametrize("loaded", [False, True], ids=["no extensions", "extensions off"])
def test_outputs_match_1_2_0(tmp_path, loaded) -> None:
    registry = extensions.loaded() if loaded else extensions.Extensions()
    with extensions.use(registry):
        written = goldens.outputs(tmp_path / "new", (tmp_path / "work").resolve())
    assert len(written) == 40
    for path in written:
        assert_same(path, GOLDEN / "outputs" / path.name)


def test_a_saved_queue_matches_1_2_0(tmp_path) -> None:
    out = tmp_path.resolve()
    with extensions.use(extensions.Extensions()):
        assert_same(goldens.saved_queue(out), QUEUE)


def test_a_saved_queue_with_extensions_off_matches_1_2_0(tmp_path) -> None:
    # Options of extensions are saved only when one is on.
    with extensions.use(extensions.loaded()):
        assert_same(goldens.saved_queue(tmp_path.resolve()), QUEUE)


@pytest.mark.parametrize("loaded", [False, True], ids=["no extensions", "extensions off"])
def test_window_settings_match_1_2_0(qapp, tmp_path, loaded) -> None:
    # Settings hold extension options only while one is on.
    out = tmp_path.resolve()
    registry = extensions.loaded() if loaded else extensions.Extensions()
    with extensions.use(registry):
        new = goldens.window_settings(out, ROOT / "resources", out / "user")
    assert_same(new, GOLDEN / "settings.json")


def test_window_settings_do_not_depend_on_this_machine(qapp, tmp_path, monkeypatch) -> None:
    # A 3 core runner defaults to 3 threads; the goldens were made where it was 4.
    import dusty.app.window

    monkeypatch.setattr(dusty.app.window, "default_threads", lambda: 3)
    monkeypatch.setattr("os.cpu_count", lambda: 3)
    out = tmp_path.resolve()
    with extensions.use(extensions.Extensions()):
        new = goldens.window_settings(out, ROOT / "resources", out / "user")
    assert_same(new, GOLDEN / "settings.json")
