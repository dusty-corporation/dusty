# Native version pins for M1

`native/versions.toml` is the source of the M1 pins. Native builds must fail if
the checked-out commit, installed SDK, or toolchain differs from these values.

## whisper.cpp

`v1.9.5` is the latest stable upstream release reported when M1 began on
2026-10-21. Its tag resolves to commit
`d1be6fde11ac6e0407606b4e42fe72d34add8037`. The pinned source has
`GGML_VULKAN` in `ggml/CMakeLists.txt` and `--vad` and `--vad-model` in
`examples/cli/cli.cpp`. It also contains `whisper-bench` and
`whisper-quantize` targets. Source:
https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.5

The first CPU and Vulkan static-library builds passed CI import checks but
used `GGML_NATIVE=ON`. The runner selected AVX-512, and the Owner desktop
raised `0xc000001d`. ISSUE-003 records the regression. ADR 0015 switches
both packages to runtime CPU backend dispatch with `GGML_NATIVE=OFF`,
`GGML_BACKEND_DL=ON`, and `GGML_CPU_ALL_VARIANTS=ON`. CI must prove that
each packaged DLL is present and that no developer runtime is imported.

## Model conversion sources

`openai/whisper` is pinned to
`86098128c0b4f24f0e2aa2994de830614b474227`. It is used only by the
model conversion pipeline for the official model URLs and assets.

Silero VAD is pinned to package `6.2.3` and tag commit
`5cd7945676eb32225748052e2e6a0580e4686a08`. The installed wheel
contains `silero_vad/data/silero_vad.jit` (2,272,526 bytes). The pinned
whisper.cpp converter calls `load_silero_vad()`, whose default path opens that
wheel resource through `importlib.resources`. The package also contains an
unrelated optional URL downloader in `utils_vad.py`; the conversion path does
not call it. CI must still verify conversion with outbound network blocked.
Source: https://github.com/snakers4/silero-vad/releases/tag/v6.2.3

## Build dependencies

LunarG Vulkan SDK `1.4.363.0` is the official latest SDK at M1 start. Its
Windows installer SHA-256 is
`94a82d378f7a5e3e54c9db7d2fb7016af136e14ac0a18dbf0f2f67a36352d141`,
from LunarG's versioned SHA endpoint:
https://sdk.lunarg.com/sdk/sha/1.4.363.0/windows/vulkan_sdk.exe.json
CI must verify the downloaded installer before running it.

FFmpeg `n9.0.2` is the current stable release, resolving to
`946fcce07b6dcd0331c8cc609192aeff5e1924f8` (the tag object is
`ce8f11b9fac4cd7ccfb41ca7c01bc17f5cda8cc3`). Its source is built with
networking, GPL, and nonfree features disabled. Source:
https://ffmpeg.org/download.html

The Linux cross-build uses Ubuntu 24.04's MinGW-w64 POSIX GCC package
`13.2.0-6ubuntu1+26.1` and headers package `11.0.1-3build1`. These are
published by Ubuntu at https://packages.ubuntu.com/noble/gcc-mingw-w64-x86-64-posix
and https://packages.ubuntu.com/noble/mingw-w64-x86-64-dev. CI checks the
installed versions explicitly.
