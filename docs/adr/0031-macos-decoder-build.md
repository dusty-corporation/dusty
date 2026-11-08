# 0031 - Separate Mac recipe for existing minimal decoder

- Status: Accepted by PM for bounded Mac build verification.
- Date:2026-10-31

Use the exact existing FFmpeg commit from native/versions.toml. Add a separate
Mac arm64 build recipe alongside the stable Windows cross-compile entry point.
Retain disable-network/everything/autodetect/gpl/nonfree and existing explicit
protocol/demuxer/decoder/parser/filter/WAV-encoder scope. Do not substitute a
Homebrew FFmpeg binary or widen protocols. Ship no output from this task yet.

Recipe accepts a verified source checkout and isolated output directory, rejects
wrong source pins before build, never deletes unknown paths and records full
configure/build/provenance evidence. Use system Apple clang/toolchain, no new
codec libraries. Existing LGPL separate-executable/corresponding-source duties
remain; inspect actual output/dependencies before any bundle acceptance.

This is the existing decoder component on a new target, not approval of another
runtime. Minimum macOS support, signed relocation, full app/private-data use and
privacy instrumentation require subsequent evidence. Preserve Windows inputs,
public hashes and source links. No pins or published assets change.

## Amendment 2026-11-07: deployment target and reproducibility (MAC10-NATIVE2)

build_ffmpeg.sh now takes an optional macOS deployment target, default 13.0,
passed to configure with --extra-cflags and --extra-ldflags. A probe build at
13.0 with availability warnings enabled produced no availability diagnostics
and no weak imports, so the configured decoder scope needs nothing newer.
The recipe fails if the build log shows an unguarded availability warning, if
any output's LC_BUILD_VERSION minos differs from the target, or if an output
contains its own build path.

The recipe now builds from a copy of the tracked FFmpeg files without .git, in
a fixed environment (env -i, PATH /usr/bin:/bin:/usr/sbin:/sbin, LC_ALL=C,
isolated Git config, Git ceiling at the output folder) and without --cxx. This
is how tools/stage_macos_runtime.py built runtime-v1. The version string is
now the release (9.0.2) whatever the clone type, and Homebrew tools on PATH no
longer reach configure. The configure scope is unchanged: LGPL, network
disabled, protocols file and pipe only, same allowlists, now tested equal to
the staging recipe flags. With target 26.0 the recipe reproduces the runtime-v1
ffmpeg and ffprobe bit for bit. Two builds at 13.0 into different folders were
identical. The package also carries the LGPL 2.1 text and SHA256SUMS.txt
names are relative to package/.

The build_ffmpeg.sh pin in native/macos/runtime-profile-v1.json (retired MAC-9
bridge runtime, reference only since ADR 0037) was updated to the new script
hash; the old runtime-v1 approval anchor therefore no longer verifies.
