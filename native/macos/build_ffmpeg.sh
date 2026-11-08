#!/usr/bin/env bash
# Build the existing audited decoder scope for Mac; source fetching is external.
set -euo pipefail
export LC_ALL=C

fail() { echo "$1" >&2; exit 1; }
[[ $# -eq 2 || $# -eq 3 ]] ||
  fail 'Usage: build_ffmpeg.sh <source-checkout> <new-output-directory> [macos-deployment-target]'
# Lowest macOS that the decoder supports (ADR 0031 amendment). The configured scope
# uses no API newer than macOS 13.0; the build refuses any availability warning.
deployment="${3:-13.0}"
[[ "$deployment" =~ ^[1-9][0-9]\.[0-9]$ ]] || fail 'Invalid macOS deployment target'
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
source_dir="$(cd "$1" && pwd -P)"
expected_commit="$(awk '
  /^\[ffmpeg\]$/ { section=1; next }
  /^\[/ { section=0 }
  section && /^commit = / { gsub(/"/, "", $3); print $3 }
' "$repo/native/versions.toml")"
[[ "$expected_commit" =~ ^[0-9a-f]{40}$ ]] || fail 'Missing FFmpeg source pin'
source_root="$(git -C "$source_dir" rev-parse --show-toplevel)"
[[ "$(cd "$source_root" && pwd -P)" == "$source_dir" ]] || fail 'FFmpeg source root mismatch'
actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
[[ "$actual_commit" == "$expected_commit" ]] || fail 'FFmpeg commit mismatch'
git -C "$source_dir" diff --quiet HEAD -- || fail 'FFmpeg tracked source is modified'
[[ -z "$(git -C "$source_dir" ls-files --others)" ]] || fail 'FFmpeg source has untracked additions'
[[ -f "$source_dir/configure" ]] || fail 'FFmpeg configure is missing'
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || fail 'Native Mac arm64 required'

out_parent="$(cd "$(dirname "$2")" && pwd -P)"
out_name="$(basename "$2")"
[[ "$out_name" != . && "$out_name" != .. ]] || fail 'Output must be a new directory'
out_dir="$out_parent/$out_name"
[[ ! -e "$out_dir" && ! -L "$out_dir" ]] || fail 'Refusing existing output directory'
case "$out_dir/" in "$source_dir/"*) fail 'Output must be outside the source checkout';; esac
clang="$(xcrun --find clang)"
sdk="$(xcrun --show-sdk-path)"
mkdir "$out_dir"
cd "$out_dir"
# Build from a copy of exactly the tracked files without Git metadata, as
# tools/stage_macos_runtime.py did for runtime-v1. ffbuild/version.sh then reports
# the RELEASE version instead of a clone dependent git describe result.
mkdir source
git -C "$source_dir" ls-files -z | (cd "$source_dir" && cpio -0 -pdm "$out_dir/source") \
  > source-copy.txt 2>&1
# Fixed environment: no caller PATH tools (for example Homebrew) reach configure or
# make, and Git cannot find a repository above the output folder.
build_env=(env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=C LC_ALL=C
  GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null "GIT_CEILING_DIRECTORIES=$out_dir")
{
  echo "source_commit=$actual_commit"
  echo "source_tree=$(git -C "$source_dir" rev-parse 'HEAD^{tree}')"
  echo "target=macos-arm64"
  echo "deployment_target=$deployment"
  echo "clang=$clang"
  echo "sdk=$sdk"
  echo "build_path=/usr/bin:/bin:/usr/sbin:/sbin"
  uname -a
  sw_vers
  "$clang" --version
  xcrun --show-sdk-version
  /usr/bin/make --version
} > provenance.txt

"${build_env[@]}" /bin/sh "$out_dir/source/configure" \
  --target-os=darwin \
  --arch=arm64 \
  --sysroot="$sdk" \
  --cc="$clang" \
  --host-cc="$clang" \
  --host-cflags="-isysroot $sdk" \
  --host-ldflags="-isysroot $sdk" \
  --extra-cflags="-mmacosx-version-min=$deployment" \
  --extra-ldflags="-mmacosx-version-min=$deployment" \
  --disable-network \
  --disable-everything \
  --disable-autodetect \
  --disable-gpl \
  --disable-nonfree \
  --disable-doc \
  --disable-debug \
  --disable-x86asm \
  --disable-shared \
  --enable-static \
  --enable-ffmpeg \
  --enable-ffprobe \
  --enable-protocol=file,pipe \
  --enable-demuxer=mp3,mov,aac,wav,flac,ogg,asf,matroska,avi,amr \
  --enable-decoder=aac,mp3,mp3float,opus,vorbis,flac,alac,pcm_s16le,pcm_s16be,pcm_u8,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,wmav1,wmav2,amrnb,amrwb,ac3,eac3 \
  --enable-parser=aac,aac_latm,ac3,flac,mpegaudio,opus,vorbis \
  --enable-filter=aresample,pan,aformat,anull \
  --enable-encoder=pcm_s16le \
  --enable-muxer=wav > configure-output.txt 2>&1
"${build_env[@]}" /usr/bin/make -j4 ffmpeg ffprobe > build-output.txt 2>&1
! grep -q 'Wunguarded-availability' build-output.txt || fail 'Unguarded API newer than the deployment target'
mkdir package
cp ffmpeg ffprobe package/
cp source/COPYING.LGPLv2.1 package/LICENSE.txt
./package/ffmpeg -hide_banner -buildconf > buildconf.txt 2>&1
./package/ffmpeg -hide_banner -protocols > protocols.txt 2>&1
./package/ffmpeg -hide_banner -L > license.txt 2>&1
file package/ffmpeg package/ffprobe > architectures.txt
otool -L package/ffmpeg package/ffprobe > dependencies.txt
for image in ffmpeg ffprobe; do
  echo "$image: $(vtool -show-build "package/$image" | awk '$1 == "minos" { print $2 }')"
done > minimum-os.txt
awk -v want="$deployment" '$2 != want { bad=1 } END { exit bad || NR == 0 }' minimum-os.txt ||
  fail 'Output minimum macOS differs from the deployment target'
! grep -rqaF "$out_dir" package || fail 'Output embeds its build path'
(cd package && shasum -a 256 ffmpeg ffprobe LICENSE.txt) > SHA256SUMS.txt
