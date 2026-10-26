"""Verify installed and development path precedence."""

from pathlib import Path

from dusty.runtime_paths import resolve_paths


def test_development_paths_honor_environment(tmp_path: Path) -> None:
    env = {
        "DUSTY_BIN_DIR": str(tmp_path / "native"),
        "DUSTY_MODELS_DIR": str(tmp_path / "weights"),
        "LOCALAPPDATA": str(tmp_path / "user"),
    }
    paths = resolve_paths(frozen=False, repo_root=tmp_path, environment=env)
    assert paths.bin_dir == tmp_path / "native"
    assert paths.models_dir == tmp_path / "weights"
    assert paths.resources_dir == tmp_path / "resources"
    assert paths.user_dir == tmp_path / "user/Dusty"


def test_installed_paths_ignore_development_environment(tmp_path: Path) -> None:
    env = {
        "DUSTY_BIN_DIR": str(tmp_path / "wrong"),
        "DUSTY_MODELS_DIR": str(tmp_path / "wrong"),
        "LOCALAPPDATA": str(tmp_path / "user"),
    }
    paths = resolve_paths(
        frozen=True, executable=tmp_path / "install/dusty/dusty.exe", environment=env
    )
    assert paths.bin_dir == tmp_path / "install/bin"
    assert paths.models_dir == tmp_path / "user/Dusty/models"
    assert paths.resources_dir == tmp_path / "install/resources"
