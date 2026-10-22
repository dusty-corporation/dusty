# M2 binary asset pins and path resolution

The `engine-v1` draft contains the CPU and Vulkan whisper.cpp v1.9.5
packages from [native CI run 39718973902](https://github.com/dusty-corporation/dusty/actions/runs/39718973902)
and minimal FFmpeg n9.0.2 from
[FFmpeg CI run 39718973892](https://github.com/dusty-corporation/dusty/actions/runs/39718973892).
Both successful runs used source commit
`29f9ca75b05c168c6d89e14d784319c2489c38d6`. The archives contain
only runtime executable and DLL files, plus `buildconf.txt` in the FFmpeg
archive. Import-check text files from CI were not included.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `whisper-cpu.zip` | 5,212,204 | `bb98378bfe200f503fdeff5aed8aa9e7c043a3e32f6d274b3ae4fb8ebdcb120c` |
| `whisper-vulkan.zip` | 19,351,908 | `1c6892dea290e4c16b3a1e109ac5950e018fa89ce2a27c679f638009f4921f76` |
| `minimal-ffmpeg.zip` | 4,310,689 | `d687eb1e7403b6ab9c444118c055ac99521ea34782f52538787690d1e53da40c` |

The hashes are pinned in `native/versions.toml` and match the uploaded
[draft release assets](https://github.com/dusty-corporation/dusty/releases/tag/untagged-971f0687d745df6c0919).
The Owner must publish that release before unauthenticated CI download.
`models-v1` is already published and supplies `ggml-tiny.bin` and
`ggml-silero-vad.bin`. It does not supply the M2 brief's `tiny.en` model;
[ISSUE-005](../pm/issues/ISSUE-005-tiny-en-asset-missing.md) records the
decision needed before the development fetch script can satisfy Task 1.

The planned development layout is `build/bin/cpu/`, `build/bin/vulkan/`,
`build/bin/ffmpeg/`, and `build/models/`. For development and tests,
`DUSTY_BIN_DIR` selects the parent of the three binary folders and
`DUSTY_MODELS_DIR` selects the model folder. When those variables are
absent, source checkouts use `build/bin/` and `build/models/`. In a
packaged build, the bundled `bin/` and `models/` layout next to the app
executable takes precedence over checkout defaults. Each chosen path is
validated before launching a process. App logs never include these paths.
