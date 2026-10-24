"""NN-7: a chosen transcript folder must survive app and installer cleanup."""

from pathlib import Path

import pytest

from dusty import selftest
from dusty.queue import cleanup_orphaned_work
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]


def saved_output(tmp_path: Path, name: str) -> tuple[Path, Path]:
    root = tmp_path / "Dusty"
    output = root / "work" / name
    output.mkdir(parents=True)
    transcript = output / "transcript.txt"
    transcript.write_text("Public synthetic preservation sentinel", encoding="utf-8")
    save_settings(root / "settings.json", {"schema_version": 1, "output_dir": str(output)})
    return root, transcript


@pytest.mark.parametrize("name", ["probe", "selftest"])
def test_startup_cleanup_preserves_saved_transcript_folder(tmp_path, name):
    root, transcript = saved_output(tmp_path, name)
    cleanup_orphaned_work(root / "work")
    assert transcript.exists(), "Startup deleted a file in the chosen transcript destination"


def test_installer_selftest_preserves_saved_transcript_folder(tmp_path, monkeypatch):
    root, transcript = saved_output(tmp_path, "selftest")
    paths = RuntimePaths(tmp_path / "bin", root / "models", ROOT / "resources", root)

    def unavailable_model(*args):
        raise ValueError("Synthetic unavailable model; no native process is launched")

    monkeypatch.setattr(selftest, "ModelRegistry", unavailable_model)
    assert selftest.run_selftest(paths, "tiny", backend="cpu", once=True) == "SELFTEST_FAILED_CPU"
    assert transcript.exists(), "Installer self-test deleted a chosen transcript destination"
