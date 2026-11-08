"""Verify installed and development path precedence."""

from pathlib import Path

import pytest

from dusty.runtime_paths import resolve_fetch_command, resolve_fetch_environment, resolve_paths


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_development_paths_honor_environment(tmp_path: Path, platform: str) -> None:
    env = {
        "DUSTY_BIN_DIR": str(tmp_path / "native"),
        "DUSTY_MODELS_DIR": str(tmp_path / "weights"),
        "LOCALAPPDATA": str(tmp_path / "user"),
    }
    paths = resolve_paths(frozen=False, repo_root=tmp_path, environment=env, platform=platform)
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
        frozen=True,
        executable=tmp_path / "install/dusty/dusty.exe",
        environment=env,
        platform="win32",
    )
    assert paths.bin_dir == tmp_path / "install/bin"
    assert paths.models_dir == tmp_path / "user/Dusty/models"
    assert paths.resources_dir == tmp_path / "install/resources"
    assert paths.install_dir == tmp_path / "install"


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_explicit_appdata_keeps_development_profiles_isolated(tmp_path, platform):
    paths = resolve_paths(
        frozen=False,
        repo_root=tmp_path / "source",
        environment={"LOCALAPPDATA": str(tmp_path / "isolated")},
        platform=platform,
    )
    assert paths.user_dir == tmp_path / "isolated/Dusty"
    assert paths.bin_dir == tmp_path / "source/build/bin"
    assert paths.models_dir == tmp_path / "source/build/models"
    assert paths.install_dir is None
    assert not paths.user_dir.exists()


@pytest.mark.parametrize(
    ("platform", "directory"),
    [("darwin", "Library/Application Support/Dusty"), ("win32", "AppData/Local/Dusty")],
)
def test_platform_default_user_data_does_not_create_a_profile(
    tmp_path, monkeypatch, platform, directory
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    paths = resolve_paths(frozen=False, environment={}, platform=platform)
    assert paths.user_dir == tmp_path / "home" / directory
    assert not paths.user_dir.exists()


def test_mac_frozen_bundle_is_separate_from_user_models_and_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    bundle = tmp_path / "Applications/Dusty Copy.app"
    paths = resolve_paths(
        frozen=True,
        executable=bundle / "Contents/MacOS/Dusty",
        environment={
            "DUSTY_BIN_DIR": str(tmp_path / "untrusted-native"),
            "DUSTY_MODELS_DIR": str(tmp_path / "untrusted-models"),
        },
        platform="darwin",
    )
    assert paths.bin_dir == bundle / "Contents/Helpers/bin"
    assert paths.resources_dir == bundle / "Contents/Resources"
    assert paths.install_dir == bundle
    assert paths.models_dir == tmp_path / "home/Library/Application Support/Dusty/models"
    assert not paths.models_dir.is_relative_to(bundle)
    assert not bundle.exists()


def test_mac_frozen_profile_isolation_override_and_relocated_fetch(tmp_path):
    bundle = tmp_path / "relocated/Dusty.app"
    executable = bundle / "Contents/MacOS/Dusty"
    paths = resolve_paths(
        frozen=True,
        executable=executable,
        environment={"LOCALAPPDATA": str(tmp_path / "probe-profile")},
        platform="darwin",
    )
    assert paths.user_dir == tmp_path / "probe-profile/Dusty"
    assert paths.models_dir == paths.user_dir / "models"
    assert resolve_fetch_command(frozen=True, executable=executable, platform="darwin") == [
        str(bundle / "Contents/Helpers/dusty-fetch/dusty-fetch")
    ]


@pytest.mark.parametrize(
    ("platform", "flags"),
    [("darwin", ["-S", "-P"]), ("win32", [])],
)
def test_source_downloader_remains_a_separate_python_module(tmp_path, platform, flags):
    executable = tmp_path / "python"
    assert resolve_fetch_command(frozen=False, executable=executable, platform=platform) == [
        str(executable),
        *flags,
        "-m",
        "dusty_fetch",
    ]


def test_mac_source_downloader_names_the_real_interpreter_not_the_venv_link(tmp_path):
    real = tmp_path / "base/bin/python3.12"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"")
    link = tmp_path / "venv/bin/python"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    command = resolve_fetch_command(frozen=False, executable=link, platform="darwin")
    assert command == [str(real.resolve()), "-S", "-P", "-m", "dusty_fetch"]
    assert "-c" not in command


def test_fetch_environment_is_complete_and_names_only_the_source_folder(monkeypatch):
    for name in ("HOME", "TMPDIR", "PYTHONPATH", "SSL_CERT_FILE", "LOCALAPPDATA"):
        monkeypatch.setenv(name, "app value")
    src = Path(__file__).resolve().parents[2] / "src"
    assert (src / "dusty_fetch/__main__.py").is_file()
    assert resolve_fetch_environment(frozen=False) == {"LC_ALL": "C", "PYTHONPATH": str(src)}
    assert resolve_fetch_environment(frozen=True) == {"LC_ALL": "C"}


def test_windows_frozen_downloader_layout_is_preserved(tmp_path):
    assert resolve_fetch_command(
        frozen=True, executable=tmp_path / "install/dusty/dusty.exe", platform="win32"
    ) == [str(tmp_path / "install/dusty-fetch/dusty-fetch.exe")]


@pytest.mark.parametrize(
    "executable",
    [
        Path("relative/Dusty.app/Contents/MacOS/Dusty"),
        Path("/tmp/Dusty"),
        Path("/tmp/Dusty.app/Contents/Wrong/Dusty"),
        Path("/tmp/not-app/Contents/MacOS/Dusty"),
        Path("/tmp/../Dusty.app/Contents/MacOS/Dusty"),
    ],
)
def test_mac_frozen_invalid_bundle_fails_before_selecting_locations(executable):
    with pytest.raises(ValueError, match="Mac app executable"):
        resolve_paths(frozen=True, executable=executable, environment={}, platform="darwin")
    with pytest.raises(ValueError, match="Mac app executable"):
        resolve_fetch_command(frozen=True, executable=executable, platform="darwin")


def test_platform_defaults_to_the_running_interpreter(tmp_path, monkeypatch):
    monkeypatch.setattr("dusty.runtime_paths.sys.platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert resolve_paths(frozen=False, environment={}).user_dir == (
        tmp_path / "Library/Application Support/Dusty"
    )


def test_mac_frozen_defaults_and_locations_need_no_filesystem_access(tmp_path, monkeypatch):
    executable = tmp_path / "Dusty.app/Contents/MacOS/Dusty"
    monkeypatch.setattr("dusty.runtime_paths.sys.platform", "darwin")
    monkeypatch.setattr("dusty.runtime_paths.sys.frozen", True, raising=False)
    monkeypatch.setattr("dusty.runtime_paths.sys.executable", str(executable))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    def unexpected_access(*args, **kwargs):
        raise AssertionError("Runtime path selection must not inspect or resolve the filesystem")

    with monkeypatch.context() as filesystem:
        filesystem.setattr(Path, "resolve", unexpected_access)
        filesystem.setattr(Path, "stat", unexpected_access)
        paths = resolve_paths(environment={})
        command = resolve_fetch_command()
    assert paths.resources_dir == tmp_path / "Dusty.app/Contents/Resources"
    assert command == [str(tmp_path / "Dusty.app/Contents/Helpers/dusty-fetch/dusty-fetch")]


def test_non_darwin_keeps_legacy_fallback_without_claiming_platform_support(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path / "profile")}
    executable = tmp_path / "install/dusty/dusty.exe"
    assert resolve_paths(
        frozen=True, executable=executable, environment=env, platform="other"
    ) == resolve_paths(frozen=True, executable=executable, environment=env, platform="win32")


@pytest.mark.parametrize("suffix", [".APP", ".App", ".aPp"])
def test_macos_bundle_suffix_case_preserves_relocated_paths(tmp_path, suffix):
    bundle = tmp_path / ("Renamed Dusty" + suffix)
    executable = bundle / "Contents/MacOS/Dusty"
    paths = resolve_paths(frozen=True, executable=executable, platform="darwin", environment={})
    assert paths.install_dir == bundle
    assert paths.bin_dir == bundle / "Contents/Helpers/bin"
    assert resolve_fetch_command(frozen=True, executable=executable, platform="darwin") == [
        str(bundle / "Contents/Helpers/dusty-fetch/dusty-fetch")
    ]
