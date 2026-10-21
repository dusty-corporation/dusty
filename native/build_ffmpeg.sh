#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${1:-$repo/build/upstream-ffmpeg}"
out_dir="${2:-$repo/build/ffmpeg}"
expected_commit="$(sed -n '/^\[ffmpeg\]/,/^\[/{s/^commit = "\([0-9a-f]*\)"/\1/p;}' "$repo/native/versions.toml")"
actual_commit="$(git -C "$source_dir" rev-parse HEAD)"
test "$actual_commit" = "$expected_commit" || { echo 'FFmpeg commit mismatch' >&2; exit 1; }

expected_gcc='13.2.0-6ubuntu1+26.1'
expected_headers='11.0.1-3build1'
test "$(dpkg-query -W -f='${Version}' gcc-mingw-w64-x86-64-posix)" = "$expected_gcc"
test "$(dpkg-query -W -f='${Version}' mingw-w64-x86-64-dev)" = "$expected_headers"

mkdir -p "$out_dir"
cd "$out_dir"
"$source_dir/configure" \
  --target-os=mingw32 \
  --arch=x86_64 \
  --cross-prefix=x86_64-w64-mingw32- \
  --enable-cross-compile \
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
  --enable-muxer=wav \
  --extra-ldflags=-static
make -j"$(nproc)" ffmpeg.exe ffprobe.exe
mkdir -p "$out_dir/package"
cp ffmpeg.exe ffprobe.exe "$out_dir/package/"
WINEDEBUG=-all wine ./ffmpeg.exe -buildconf > "$out_dir/buildconf.txt" 2>&1
