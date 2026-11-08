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

## The Mac engine

On a Mac the same command fetches the engine-macos-v1 prerelease instead of
the three Windows archives: `whisper-cpu-macos-arm64.zip`,
`whisper-metal-macos-arm64.zip` and `ffmpeg-macos-arm64.zip`, each checked
against its hash in the `[engine_release_macos]` section of
`native/versions.toml`. They are the unchanged output of the manual
native-macos.yml workflow (run 42451307858 at
4ad90615bde74557539f68ce46d930fa5033c0a4), which builds whisper.cpp CPU and
Metal and FFmpeg with `native/macos/build_whisper.sh` and `build_ffmpeg.sh` on
a macos-15 runner and checks the architecture, minimum macOS and package hashes.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| whisper-cpu-macos-arm64.zip | 2885717 | b384b21d068441e4095d035d4420077585a5e1a177723332d4e4fc6ccb6d2ebb |
| whisper-metal-macos-arm64.zip | 5951376 | aa27cfeb79144de33d01a5fd0374a283466de880a45c85469355eb30d3c33a31 |
| ffmpeg-macos-arm64.zip | 3693531 | 0f436373ca3f2de9c35dbe0b1b84fd2bdef1aa01ab165eff38bd7254f194c636 |

Each archive holds one component folder: its `SHA256SUMS.txt`, build facts
such as `minimum-os.txt`, and `package/` with the programs, libraries and
license. The fetch accepts nothing else (no links, no other folders), checks
every package file against that `SHA256SUMS.txt`, and unpacks into
`build/engine-macos/macos-arm64/native-v3`, never over a local engine build in
`build/macos-arm64`. It then runs `tools/stage_macos_dev_bin.py --no-models`
to lay out `build/bin/cpu`, `build/bin/metal`, `build/bin/ffmpeg` and
`build/bin/lifeline` from those packages; `build/bin` must be new or empty.
The CI macos job builds Dusty.app from the same folder with
`tools.build_macos_app --native-root build/engine-macos/macos-arm64`.
