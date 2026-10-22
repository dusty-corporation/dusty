# M2 binary asset pins and path resolution

The active published `engine-v2` prerelease contains CPU and Vulkan whisper.cpp v1.9.5
with the ADR 0018 VAD timestamp patch from
[native CI run 39804070663](https://github.com/dusty-corporation/dusty/actions/runs/39804070663)
and minimal FFmpeg n9.0.2 from
[FFmpeg CI run 39718973892](https://github.com/dusty-corporation/dusty/actions/runs/39718973892).
The native run used source commit `c560048bbf0ec7d01fcc3074c61957982fc255dd`;
the unchanged FFmpeg run used `29f9ca75b05c168c6d89e14d784319c2489c38d6`.
The archives contain only runtime executable and DLL files, the native MIT
`LICENSE.txt`, plus `buildconf.txt` in the FFmpeg
archive. Import-check text files from CI were not included.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `whisper-cpu.zip` | 5,126,592 | `a8c0630616b70a00e40b9534f594cd525885cd10ef45e492aa82378ea9a325b6` |
| `whisper-vulkan.zip` | 19,266,294 | `2a4aeae6789391c7cc2fa8bbe01648e0d36c499ca1233cbdcf58d127c47fc6a0` |
| `minimal-ffmpeg.zip` | 4,310,689 | `d687eb1e7403b6ab9c444118c055ac99521ea34782f52538787690d1e53da40c` |

The hashes are pinned in `native/versions.toml` and match the uploaded
[published release assets](https://github.com/dusty-corporation/dusty/releases/tag/engine-v2).
The Owner published it as a prerelease. A fresh release query after
publication confirmed that all three asset digests still match the pins.
Dev fetch verifies the downloaded bytes independently. The original engine-v1
release remains unchanged. The published patch and SHA256SUMS.txt also retain
the verified draft digests recorded in `M2-interim-5.md`.
`models-v1` is also published and supplies `ggml-tiny.bin`,
`ggml-small.en.bin`, and `ggml-silero-vad.bin`. The PM resolved
[ISSUE-005](../pm/issues/ISSUE-005-tiny-en-asset-missing.md) by using
`small.en` for English-only tests and fetching.

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
archives and the `tiny`, `small.en`, multilingual `small` (for the Persian
translation regression), and VAD model files. It checks every
archive against `native/versions.toml`, checks the published model manifest
against its pinned hash, then checks each selected model against that
manifest before use. Existing files are reused only if their hashes match.
CI runs the same script and caches `build/downloads`, `build/bin`, and
`build/models` under a key derived from the pinned versions file. Native
and FFmpeg build workflows remain available only by manual dispatch.
