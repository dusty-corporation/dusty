# Minimal Mac decoder build

MAC3-DECODER, 2026-10-31. Worker base
8e7c77bba121033ea7e8a4aaf324a037f648792b, in an isolated worktree. No Windows recipe, pin or published asset changed.

## Recipe contract

`native/macos/build_ffmpeg.sh` builds the existing FFmpeg component for native
Darwin arm64. Source fetching is a separate explicit development action; the
recipe itself has no downloader. Invoke it with a pre-fetched source checkout and
an output directory that does not exist, whose parent already exists:

```sh
bash native/macos/build_ffmpeg.sh <clean-pinned-source> <new-output-directory>
```

Before configuring, it checks that the source is its own Git root, HEAD equals
the FFmpeg commit in native/versions.toml, tracked files match that commit and
there are no untracked source additions (including ignored generated files).
An archive extracted inside the application repository cannot inherit Dusty's
Git identity. Wrong pins and source changes fail before output creation. Existing
output, output symlinks and in-source output are refused, never cleaned or deleted.
A failed build is retained for diagnosis; retry using a new output directory.

The target is Darwin arm64 with Apple's xcrun-selected clang and SDK. Both target
and host-tool compilation need the SDK explicitly. Configure/build/provenance,
protocols, runtime license, architectures, dependency listings and binary hashes
are retained beside package/ffmpeg and package/ffprobe. No output is shipped yet.

All protocol/demuxer/decoder/parser/filter/encoder/muxer lists exactly match the
unchanged native/build_ffmpeg.sh Windows recipe. Preserve disable-network,
disable-everything, disable-autodetect, disable-gpl and disable-nonfree. Libraries
are static within the separate FFmpeg/ffprobe executables; OS libraries/frameworks
remain system-provided. The Windows MinGW target, Wine and global -static linker
flag are not applicable to Darwin and are not copied. No general-purpose FFmpeg
package or alternate codec library was installed.

## Verified source and toolchain

- FFmpeg upstream: https://github.com/FFmpeg/FFmpeg.git.
- Exact existing pin: 946fcce07b6dcd0331c8cc609192aeff5e1924f8, tag n9.0.2.
- Verified source tree: f314f188666de54687c464fc975e5ee43fae26e1.
- Prefetch used a separate scratch Git repository, depth-one fetch of that exact
  commit, and detached checkout. Source remains clean after the out-of-tree build.
- Local environment: M2 arm64, macOS 26.2 (25C56), Apple clang 21.0.0
  (clang-2100.1.1.101), Command Line Tools SDK 26.5, Apple make 3.81.
- Final recipe SHA-256:
  c8d08e6183e7a7de92631b72f1cbaa1f00597d10aefc58f80484f24e16e60b03.

The first build under build/mac3-decoder/arm64 failed the target compiler test:
ld could not find System. A second attempt under arm64-sdk passed that test with
--sysroot, then failed host-tool header detection because ctype.h was not found.
The successful arm64-hostsdk build applies the SDK to target and host flags.
Both failed configure logs and ffbuild/config.log files remain; no source/pin was
substituted. No pkg-config tool was installed: configure warns that it is absent,
while the explicitly restricted, no-autodetect build succeeds.

The final untracked-source refusal guard was added after this successful build;
its separate fail-before-configure test passes. Configure/build commands and
native output below are from the successful SDK-corrected recipe. No repeated
build/reproducible-binary claim is made from the guard-only change.

## Actual native outputs

Scratch root: build/mac3-decoder/arm64-hostsdk. Build command:

```sh
bash native/macos/build_ffmpeg.sh build/mac3-decoder/upstream build/mac3-decoder/arm64-hostsdk
```

| Output | Size in bytes | SHA-256 |
| --- | --- | --- |
| ffmpeg | 4072920 | 75cf8431c1dad7d221516b5d53dc94db0d40dfff7b64c6d5e9ce93ae02a5dd88 |
| ffprobe | 3897512 | d23183d674a1a340bf7d2fb010be02aad73bf037469904a275d83a31bb4df054 |

Both identify as Mach-O 64-bit executable arm64. LC_BUILD_VERSION declares
minimum OS 26.0 and SDK 26.5. This is observed build metadata, not verification of
support on 26.0 or any older Mac. Product minimum OS remains a separate decision.

`-buildconf` confirms all required disable flags and unchanged allowlists.
Generated config.h has NETWORK, GPL, NONFREE, SECURETRANSPORT, AVFOUNDATION,
AUDIOTOOLBOX and VIDEOTOOLBOX all set to zero. Both binaries' `-protocols` output
contains exactly file and pipe as input and output protocols. `ffmpeg -L` reports
LGPL version 2.1 or later. This observes the actual build, not just command text.

`otool -L` lists only libSystem.B.dylib and Apple's system CoreFoundation,
CoreVideo and CoreMedia frameworks for both executables. No Homebrew prefix,
third-party codec dylib or FFmpeg shared library is referenced. System framework
imports do not mean the disabled AudioToolbox/VideoToolbox codecs are enabled.
Signed packaging, recursive runtime auditing and corresponding-source/notices
assembly still need their release gates. Existing LGPL separate-executable and
source-distribution duties are preserved, not waived by this experiment.

## Fixture evidence

Run the retained stdlib-only scratch verifier:

```sh
.venv/bin/python build/mac3-decoder/verify-fixtures.py
```

It runs the actual package binaries with runtime protocol_whitelist file,pipe,
stores JSON probe metadata and per-case stderr in a fresh ignored output folder,
and checks decoded WAV headers for mono, 16 kHz, 16-bit PCM and positive frames.
No private profile or Owner recording is used; all input provenance is in
`tests/fixtures/AUDIO_SOURCES.md`. No media fixture was modified.

Observed: 22 successful probe/decode cases covering all 17 supported extensions
(3gp, aac, amr, avi, flac, m4a, m4v, mkv, mov, mp3, mp4, oga, ogg, opus, wav,
webm, wma). Cases include the Persian filename, long path, Persian speech WAV,
600-second silence/VAD fixture and 660-second public LibriVox benchmark. This
is decoder evidence, not transcription, translation, VAD or performance evidence.

All three negative inputs reject during decoding. The no-audio MP4 probes
successfully with no audio stream and then fails the selected-audio mapping;
corrupt and zero-byte MP3 fail probing and decoding. Raw outcomes and fixture
hashes are in build/mac3-decoder/fixture-summary.json; commands are retained in
the verifier. No network input was contacted to test protocol exclusion.

## Checks and limits

`.venv/bin/python -m pytest -q tests/unit/test_mac_ffmpeg_recipe.py`: 7 passed.
The portable scope test compares the Mac allowlists against the Windows recipe.
Native shell tests exercise actual wrong-repository commit and inherited-parent
refusal, plus controlled source-probe refusals for modified/untracked source,
existing output and in-source output. They prove configure was not invoked or
preserved files overwritten. These shell tests target Darwin; portable source
scope checking remains available on Windows. No existing tests were skipped or
weakened for this task.

`bash -n`, targeted Ruff lint/format, no-network, prohibited-host, documentation
consistency and diff checks pass. An attempted combined run including existing
test_ffmpeg_source.py cannot collect on this Mac because its existing Windows
license-audit import requires pefile, absent from the locked Darwin environment.
No dependency was added and no license test was disabled to bypass that failure.
The runtime license observation above is not a complete release license audit.

NOT RUN: Windows native build, signed app relocation/notarization, clean-machine
installation, lower macOS/Intel execution, full Dusty trusted launch/guard path,
process cancellation/crash lifecycle or dynamic network isolation monitoring.
This task does not declare any package or platform release-ready. Independent QA
and PM acceptance apply before integration.
