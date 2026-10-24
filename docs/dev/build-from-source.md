# Build and verify Dusty from source

Use a separate checkout and public fixtures. Do not point test tools at a real
Dusty profile. The source app uses build/bin and build/models; frozen apps use
their split install folder and local app data. No model is bundled in the app.

## Windows source environment

Python 3.12 and uv are required. Packaging uses the exact Python 3.12.11 build
and Qt pins checked by packaging/platform-socket-imports.json; a different
interpreter can run source tests but must not silently update those PE pins.

```powershell
uv sync --locked
uv run python tools/fetch_dev_binaries.py
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python tools/check_docs.py
uv run python tools/measure_coverage.py
uv run python tools/check_no_network.py
uv run python tools/check_no_huggingface.py
uv run python tools/check_licenses.py
```

Asset fetching is an explicit developer network action. It verifies the pinned
engine archives, model manifest and model bytes before use. For walkthrough
models, tools/fetch_dev_binaries.py --help describes the optional model set.
Never commit those assets. ISSUE-026 tracks native Unicode-profile compatibility;
the regression stays enabled while the proposed new engine awaits activation.

Run the GUI with a disposable profile inside the repo. Restore the process
environment afterwards; this does not change Windows known folders:

```powershell
$previousLocal = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = Join-Path $PWD 'build/manual-profile'
    uv run python -m dusty
} finally {
    $env:LOCALAPPDATA = $previousLocal
}
```

## Native builds and packaging

[build-native.md](build-native.md) records pinned APIs, CPU dispatch and the VAD
patch; [ffmpeg-build.md](ffmpeg-build.md) records the network-disabled decoder.
The M6 UTF-8 manifest candidate is described in ADR 0024. Native artifacts are
built by native.yml and checked by hash before use; publishing is Owner-only.

On a disposable Windows runner, mirror ci.yml exactly:

```powershell
uv run python -m tools.build_bundle
uv run python tools/check_bundle.py dist/Dusty
uv run python tools/check_pe_imports.py dist/Dusty/dusty --native dist/Dusty/bin
uv run python tools/smoke_packaged_gui.py dist/Dusty
uv run python -m tools.inventory_bundle dist/Dusty
uv run python tools/check_licenses.py --bundle dist/Dusty --inventory build/packaging/audit/inventory.json
```

The build verifies Microsoft redistributable provenance and excludes networking
modules from the processing folder. Do not copy arbitrary runtime DLLs to make
a failing gate pass. [release-process.md](release-process.md) covers the gated
installer and draft assets. The audit packet lists destructive/system-audit
commands that belong only on the disposable CI runner.

## Reproduce model conversion without changing a release

Use a fresh disposable Linux checkout, Python 3.12 and the exact tools in
models.yml. Allow substantial disk space. These are build-only packages, never
app runtime dependencies. Do not dispatch the old upload workflow against the
published models-v1 release. The following reproduces Tiny locally:

```bash
git clone --filter=blob:none https://github.com/ggml-org/whisper.cpp.git build/upstream-whisper
git -C build/upstream-whisper checkout --detach d1be6fde11ac6e0407606b4e42fe72d34add8037
git clone --filter=blob:none https://github.com/openai/whisper.git build/upstream-openai
git -C build/upstream-openai checkout --detach 86098128c0b4f24f0e2aa2994de830614b474227
python -m modelpipeline.verify_sources build/upstream-openai
python -m venv build/conversion-env
. build/conversion-env/bin/activate
python -m pip install 'torch==2.14.1+cpu' --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'numpy==2.3.3' 'silero-vad==6.2.3'
mkdir -p build/model-work
url="$(python -c 'import json; print(json.load(open("modelpipeline/model_sources.json"))["tiny"]["url"])')"
expected="$(python -c 'import json; print(json.load(open("modelpipeline/model_sources.json"))["tiny"]["sha256"])')"
curl --fail --location --retry 3 --output build/model-work/model.pt "$url"
echo "$expected  build/model-work/model.pt" | sha256sum --check --status
set -o pipefail
python -m modelpipeline.convert tiny f16 2>&1 | tee build/conversion.log
python -m modelpipeline.check_log build/conversion.log
python tools/check_no_huggingface.py
sha256sum build/model-package/ggml-tiny.bin
```

Check each command's exit status. Conversion itself runs twice, compares hashes,
rejects assets at or above 2 GiB and removes its temporary checkpoint. Compare
the final hash with the Tiny entry in tests/fixtures/models/models-v1.json. For
quantization, build whisper-quantize under build/upstream-whisper/build and run
modelpipeline.convert with the exact catalog model and quantization; it also
quantizes twice. For silero-vad f16, no checkpoint download is needed: conversion
reads the pinned wheel's local JIT weights with the offline sitecustomize guard.

These instructions document the verified M1 recipe; M6 does not claim a fresh
multi-gigabyte conversion run. Do not upload fragments or mutate models-v1.
