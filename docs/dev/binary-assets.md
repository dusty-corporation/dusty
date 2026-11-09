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

On a Mac the same command fetches the engine-macos-v2 prerelease instead of
the three Windows archives: `whisper-cpu-macos-arm64.zip`,
`whisper-metal-macos-arm64.zip` and `ffmpeg-macos-arm64.zip`, each checked
against its hash in the `[engine_release_macos]` section of
`native/versions.toml`. They are the unchanged output of the manual
native-macos.yml workflow, run 42542628054 in the public repository
dusty-corporation/dusty-staging at 3433ea3b7023afa11eb484638104e32b8ee20bf5,
the reviewed tree of dusty-dev commit dc4a0f4a874038a642edca4bdbf6aba0acda96d3. It builds whisper.cpp CPU and
Metal and FFmpeg with `native/macos/build_whisper.sh` and `build_ffmpeg.sh` on
a macos-15 runner and checks the architecture, minimum macOS and package hashes.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| whisper-cpu-macos-arm64.zip | 2885692 | c7f26b20056843f7a8bd72a5f620d01a33b28351b84b0f47b1d9ba42d5e8ed20 |
| whisper-metal-macos-arm64.zip | 5951422 | c0ead3a489206aa57f97aa1586e7de133ad15f1a7039374ca827483de01bcc57 |
| ffmpeg-macos-arm64.zip | 3693530 | 6e7a9f06aed57fd8e0f53999799ec4e3f219d95598923ab5d558d2e15ffbc14d |

engine-macos-v2 replaced engine-macos-v1 (run 42451307858 in dusty-dev at
4ad90615bde74557539f68ce46d930fa5033c0a4) to add the speech detection threads
patch (ADR 0032, MAC11-VAD). Inside the archives only `libwhisper` differs from
engine-macos-v1; whisper-cli, the ggml libraries and FFmpeg are byte-identical.

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
