# M2 binary asset pins and path resolution

The active engine-v3 prerelease contains whisper.cpp v1.9.5 with the timestamp
mapping patch and UTF-8 manifest. See [engine-v3 provenance](engine-v3.md) for exact
archive sizes, hashes and original producer identifiers. The public copies are
byte-identical; no private CI artifact is silently substituted. Original
engineering runs are retained separately, not as public build dependencies.

Production hashes are pinned in native/versions.toml. The published models-v1
manifest is pinned independently and contains the tiny, small.en, medium and
voice detection inputs used by development tests. The optional recommended
fetch also obtains Small and Turbo q8_0. The English-only regression uses
small.en, not a model absent from the manifest.

The development layout is `build/bin/cpu/`, `build/bin/vulkan/`,
`build/bin/ffmpeg/`, and `build/models/`. For development and tests,
`DUSTY_BIN_DIR` selects the parent of the three binary folders and
`DUSTY_MODELS_DIR` selects the model folder. When those variables are
absent, source checkouts use `build/bin/` and `build/models/`. In a
packaged build, binaries and resources live next to the app executable,
while verified models live in `%LOCALAPPDATA%/Dusty/models/` as SPEC 5.8
requires. The packaged layout takes precedence over development variables.
Each chosen path is validated before launching a process. App logs never
include these paths.

`uv run python tools/fetch_dev_binaries.py` downloads the three engine
archives and the `tiny`, `small.en`, multilingual `medium` (for the Persian
translation regression), and VAD model files. It checks every
archive against `native/versions.toml`, checks the published model manifest
against its pinned hash, then checks each selected model against that
manifest before use. Existing files are reused only if their hashes match.
CI runs the same script and caches `build/downloads`, `build/bin`, and
`build/models` under a key derived from the pinned versions file. Native
and FFmpeg build workflows remain available only by manual dispatch.
