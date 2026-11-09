"""Reject source/patch drift and preserve caller/output boundaries before building."""

import hashlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / "native/macos/build_whisper.sh"
PINS = tomllib.loads((ROOT / "native/versions.toml").read_text())
COMMIT = PINS["whisper_cpp"]["commit"]
# The Mac engine has its own complete approved patch (ADR 0032, MAC11-VAD).
PATCH = ROOT / PINS["whisper_cpp_macos"]["patch"]
WINDOWS_PATCH = ROOT / PINS["whisper_cpp"]["patch"]
DARWIN = pytest.mark.skipif(sys.platform != "darwin", reason="native Mac recipe shell behavior")


def test_explicit_backend_and_offline_build_contract():
    source = RECIPE.read_text()
    for flag in [
        "WHISPER_BUILD_IS_DEV=OFF",
        "WHISPER_BUILD_SERVER=OFF",
        "WHISPER_CURL=OFF",
        "GGML_RPC=OFF",
        "GGML_CUDA=OFF",
        "GGML_VULKAN=OFF",
        "GGML_NATIVE=OFF",
        "GGML_BACKEND_DL=OFF",
        "WHISPER_COREML=OFF",
        "WHISPER_OPENVINO=OFF",
        "GGML_METAL_EMBED_LIBRARY=ON",
    ]:
        assert "-D" + flag in source
    assert "--target whisper-cli" in source
    assert "canonical_diff_hash" in source
    assert "--no-ext-diff --no-textconv" in source
    assert "curl " not in source and "wget " not in source


def _changed_lines(patch: Path) -> tuple[list[bytes], list[bytes]]:
    lines = patch.read_bytes().splitlines()
    added = [line for line in lines if line.startswith(b"+") and not line.startswith(b"+++")]
    removed = [line for line in lines if line.startswith(b"-") and not line.startswith(b"---")]
    return added, removed


def test_mac_patch_is_the_windows_patch_plus_the_speech_detection_threads():
    pinned = PINS["whisper_cpp_macos"]["patch_sha256"]
    assert hashlib.sha256(PATCH.read_bytes()).hexdigest() == pinned
    mac_added, mac_removed = _changed_lines(PATCH)
    windows_added, windows_removed = _changed_lines(WINDOWS_PATCH)
    assert mac_removed == windows_removed
    threads = (
        b"+        vad_ctx_params.n_threads = std::min(vad_ctx_params.n_threads, params.n_threads);"
    )
    extra = [line for line in mac_added if line not in windows_added]
    assert extra[-1] == threads
    assert all(line.startswith(b"+        //") for line in extra[:-1]) and len(extra) == 3
    assert [line for line in mac_added if line not in extra] == windows_added


@pytest.fixture
def source_probe(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "CMakeLists.txt").write_text("not executed by rejection tests")
    tools = tmp_path / "tools"
    tools.mkdir()
    fake = tools / "git"
    fake.write_text("""#!/bin/sh
if [ "$1" = '-C' ]; then shift 2; fi
while [ "$1" = '-c' ]; do shift 2; done
case "$1" in
  rev-parse)
    if [ "$2" = '--show-toplevel' ]; then printf '%s\n' "$WHISPER_TEST_ROOT";
    else printf '%s\n' "$WHISPER_TEST_PIN"; fi;;
  ls-files) printf '%s' "${WHISPER_TEST_UNTRACKED:-}";;
  diff) if [ -n "${WHISPER_TEST_DIFF:-}" ]; then cat "$WHISPER_TEST_DIFF"; fi;;
  *) echo 'unexpected build action' >&2; exit 99;;
esac
""")
    fake.chmod(0o755)
    env = os.environ.copy()
    env.update(
        PATH=str(tools) + os.pathsep + env["PATH"],
        WHISPER_TEST_ROOT=str(source),
        WHISPER_TEST_PIN=COMMIT,
    )
    return source, env


def invoke(source, output, env=None, backend="cpu", recipe=RECIPE):
    return subprocess.run(
        ["bash", str(recipe), str(source), str(output), backend],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


@DARWIN
def test_real_wrong_pin_fails_before_build(tmp_path):
    out = tmp_path / "out"
    result = invoke(ROOT, out)
    assert result.returncode != 0 and "Whisper commit mismatch" in result.stderr
    assert not out.exists()


@DARWIN
def test_bad_patch_hash_fails_before_source_or_output_mutation(tmp_path):
    repo = tmp_path / "repo"
    recipe = repo / "native/macos/build_whisper.sh"
    recipe.parent.mkdir(parents=True)
    recipe.write_bytes(RECIPE.read_bytes())
    (repo / "native/versions.toml").write_bytes((ROOT / "native/versions.toml").read_bytes())
    patch = repo / PINS["whisper_cpp_macos"]["patch"]
    patch.parent.mkdir(parents=True)
    patch.write_bytes(PATCH.read_bytes() + b"\nunapproved\n")
    out = tmp_path / "out"
    result = invoke(ROOT, out, recipe=recipe)
    assert result.returncode != 0 and "Approved patch hash mismatch" in result.stderr
    assert not out.exists()


@DARWIN
@pytest.mark.parametrize("change", ["extra-file", "extra-hunk-in-patched-file", "partial-patch"])
def test_full_patch_closure_refuses_additional_or_partial_edits(tmp_path, source_probe, change):
    source, env = source_probe
    payload = tmp_path / "diff.patch"
    if change == "extra-file":
        value = PATCH.read_bytes() + b"diff --git a/other.c b/other.c\n+extra\n"
    elif change == "extra-hunk-in-patched-file":
        value = PATCH.read_bytes() + b"@@ -1 +1 @@\n-unapproved-old\n+unapproved-new\n"
    else:
        value = PATCH.read_bytes()[:200]
    payload.write_bytes(value)
    env["WHISPER_TEST_DIFF"] = str(payload)
    out = tmp_path / "out"
    result = invoke(source, out, env)
    assert result.returncode != 0 and "complete approved patch" in result.stderr
    assert not out.exists()


@DARWIN
def test_untracked_source_refusal(tmp_path, source_probe):
    source, env = source_probe
    env["WHISPER_TEST_UNTRACKED"] = "bindings/javascript/package.json"
    result = invoke(source, tmp_path / "out", env)
    assert result.returncode != 0 and "untracked additions" in result.stderr
    assert not (tmp_path / "out").exists()


@DARWIN
@pytest.mark.parametrize("patched", [False, True])
def test_pristine_or_canonical_patch_never_overwrites_existing_output(
    tmp_path, source_probe, patched
):
    source, env = source_probe
    if patched:
        env["WHISPER_TEST_DIFF"] = str(PATCH)
    out = tmp_path / "out"
    out.mkdir()
    marker = out / "keep"
    marker.write_text("preserved")
    result = invoke(source, out, env)
    assert result.returncode != 0 and "Refusing existing output" in result.stderr
    assert marker.read_text() == "preserved"


@DARWIN
def test_inherited_parent_git_identity_refusal(tmp_path, source_probe):
    source, env = source_probe
    env["WHISPER_TEST_ROOT"] = str(source.parent)
    result = invoke(source, tmp_path / "out", env)
    assert result.returncode != 0 and "source root mismatch" in result.stderr
    assert not (tmp_path / "out").exists()


@DARWIN
def test_source_output_refused_before_creation(source_probe):
    source, env = source_probe
    result = invoke(source, source / "out", env)
    assert result.returncode != 0 and "outside the source checkout" in result.stderr
    assert not (source / "out").exists()


@DARWIN
def test_unknown_backend_fails_without_output(tmp_path):
    result = invoke(ROOT, tmp_path / "out", backend="cuda")
    assert result.returncode != 0 and "Unknown Mac backend" in result.stderr
    assert not (tmp_path / "out").exists()


def test_deployment_target_and_build_path_mapping_contract():
    source = RECIPE.read_text()
    # 13.3 is the first macOS with the Accelerate cblas interface ggml-blas calls.
    assert 'deployment="${4:-13.3}"' in source
    assert '"-DCMAKE_OSX_DEPLOYMENT_TARGET:STRING=$deployment"' in source
    assert "-ffile-prefix-map=$out=/dusty-whisper" in source
    assert "-Werror=unguarded-availability -Werror=unguarded-availability-new" in source
    assert "vtool -show-build" in source and "Output embeds its build path" in source


@DARWIN
@pytest.mark.parametrize("target", ["13", "13.3.1", "latest", "9.0", "13.3; rm -rf /"])
def test_invalid_deployment_target_fails_without_output(tmp_path, target):
    out = tmp_path / "out"
    result = subprocess.run(
        ["bash", str(RECIPE), str(ROOT), str(out), "cpu", target],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0 and "Invalid macOS deployment target" in result.stderr
    assert not out.exists()
