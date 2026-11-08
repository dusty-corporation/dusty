"""Keep Mac decoder scope aligned with Windows and refuse unsafe build inputs."""

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / "native/macos/build_ffmpeg.sh"
PIN = tomllib.loads((ROOT / "native/versions.toml").read_text())["ffmpeg"]["commit"]
DARWIN_ONLY = pytest.mark.skipif(sys.platform != "darwin", reason="native Mac recipe shell checks")


def test_mac_scope_matches_existing_windows_decoder_allowlists():
    def allowlists(path):
        return dict(
            re.findall(
                r"--enable-(protocol|demuxer|decoder|parser|filter|encoder|muxer)=([^\s\\]+)",
                path.read_text(),
            )
        )

    assert allowlists(RECIPE) == allowlists(ROOT / "native/build_ffmpeg.sh")
    source = RECIPE.read_text()
    for option in ["network", "everything", "autodetect", "gpl", "nonfree"]:
        assert f"--disable-{option}" in source
    assert "--disable-shared" in source and "--enable-static" in source
    assert "--target-os=darwin" in source and "--arch=arm64" in source
    assert '--sysroot="$sdk"' in source


@DARWIN_ONLY
def test_wrong_real_commit_is_refused_before_output_creation(tmp_path):
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(RECIPE), str(ROOT), str(output)], capture_output=True, text=True, timeout=15
    )
    assert result.returncode != 0
    assert "FFmpeg commit mismatch" in result.stderr
    assert not output.exists()


@DARWIN_ONLY
def test_inherited_parent_source_identity_is_rejected(tmp_path):
    nested = tmp_path / "source"
    nested.mkdir()
    result = subprocess.run(
        ["bash", str(RECIPE), str(nested), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert "FFmpeg source root mismatch" in result.stderr
    assert not (tmp_path / "out").exists()


@pytest.fixture
def source_probe(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "configure").write_text('#!/bin/sh\ntouch "$RECIPE_TEST_SENTINEL"\n')
    (source / "configure").chmod(0o755)
    tools = tmp_path / "tools"
    tools.mkdir()
    fake_git = tools / "git"
    fake_git.write_text("""#!/bin/sh
shift 2
case "$*" in
  'rev-parse --show-toplevel') printf '%s\n' "$RECIPE_TEST_ROOT";;
  'rev-parse HEAD') printf '%s\n' "$RECIPE_TEST_PIN";;
  'diff --quiet HEAD --') exit "${RECIPE_TEST_DIRTY:-0}";;
  'ls-files --others') printf '%s' "${RECIPE_TEST_UNTRACKED:-}";;
  *) exit 99;;
esac
""")
    fake_git.chmod(0o755)
    env = os.environ.copy()
    env.update(
        PATH=str(tools) + os.pathsep + env["PATH"],
        RECIPE_TEST_ROOT=str(source),
        RECIPE_TEST_PIN=PIN,
        RECIPE_TEST_SENTINEL=str(tmp_path / "configured"),
    )
    return source, env


def probe(source, output, env):
    return subprocess.run(
        ["bash", str(RECIPE), str(source), str(output)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


@DARWIN_ONLY
def test_dirty_pinned_source_is_rejected_before_configure(tmp_path, source_probe):
    source, env = source_probe
    env["RECIPE_TEST_DIRTY"] = "1"
    output = tmp_path / "output"
    result = probe(source, output, env)
    assert result.returncode != 0 and "tracked source is modified" in result.stderr
    assert not output.exists()
    assert not Path(env["RECIPE_TEST_SENTINEL"]).exists()


@DARWIN_ONLY
def test_existing_output_is_not_overwritten(tmp_path, source_probe):
    source, env = source_probe
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("preserve")
    result = probe(source, output, env)
    assert result.returncode != 0 and "Refusing existing output" in result.stderr
    assert sentinel.read_text() == "preserve"
    assert not Path(env["RECIPE_TEST_SENTINEL"]).exists()


@DARWIN_ONLY
def test_in_source_output_is_rejected_before_creation(source_probe):
    source, env = source_probe
    output = source / "build"
    result = probe(source, output, env)
    assert result.returncode != 0 and "outside the source checkout" in result.stderr
    assert not output.exists()
    assert not Path(env["RECIPE_TEST_SENTINEL"]).exists()


@DARWIN_ONLY
def test_untracked_source_additions_are_rejected_before_configure(tmp_path, source_probe):
    source, env = source_probe
    env["RECIPE_TEST_UNTRACKED"] = "config.h"
    output = tmp_path / "output"
    result = probe(source, output, env)
    assert result.returncode != 0 and "untracked additions" in result.stderr
    assert not output.exists()
    assert not Path(env["RECIPE_TEST_SENTINEL"]).exists()


@pytest.mark.skipif(
    not (ROOT / "tools/stage_macos_runtime.py").is_file(),
    reason="the runtime-v1 staging tool is kept only in private development",
)
def test_configure_scope_equals_the_runtime_v1_staging_recipe():
    from tools import stage_macos_runtime

    source = RECIPE.read_text()
    configure = source[source.index('/bin/sh "$out_dir/source/configure"') :]
    configure = configure[: configure.index("> configure-output.txt")]
    flags = re.findall(r"--(?:disable|enable)-[^\s\\]+", configure)
    assert flags == list(stage_macos_runtime.CONFIG_FLAGS)
    assert "--cxx" not in configure


def test_fixed_environment_copy_and_deployment_target_contract():
    source = RECIPE.read_text()
    assert 'deployment="${3:-13.0}"' in source
    assert '--extra-cflags="-mmacosx-version-min=$deployment"' in source
    assert '--extra-ldflags="-mmacosx-version-min=$deployment"' in source
    # Tracked files only, no .git, so the version string comes from RELEASE.
    assert 'git -C "$source_dir" ls-files -z' in source and "cpio -0 -pdm" in source
    assert "env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=C LC_ALL=C" in source
    assert '"GIT_CEILING_DIRECTORIES=$out_dir"' in source
    assert '"${build_env[@]}" /usr/bin/make' in source
    assert "vtool -show-build" in source and "Output embeds its build path" in source


@DARWIN_ONLY
@pytest.mark.parametrize("target", ["13", "13.0.1", "latest", "9.0", "13.0 -fno-pie"])
def test_invalid_deployment_target_fails_without_output(tmp_path, target):
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(RECIPE), str(ROOT), str(output), target],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0 and "Invalid macOS deployment target" in result.stderr
    assert not output.exists()
