# Minimal FFmpeg for M1

CI run 39692158489 (archived producer)
cross-compiled pinned FFmpeg `n9.0.2` with Ubuntu 24.04 MinGW-w64. It
produced `ffmpeg.exe` (4,992,512 bytes) and `ffprobe.exe` (4,799,488
bytes). The workflow decoded all 17 supported extensions from the public
domain JFK fixture and rejected the no-audio, zero-byte, and corrupt
fixtures. The format list and provenance are in
`tests/fixtures/AUDIO_SOURCES.md`.
The later run 39693880471 (archived producer 39693880471)
also passed after Unicode and long-path fixtures were added. The nested
path fixture has a 242-character absolute path on the desktop and was
also decoded there with the packaged binary.

`native/build_ffmpeg.sh` is the reproducible command. The full configure
invocation, as reported by `ffmpeg.exe -buildconf`, was:

```text
--target-os=mingw32 --arch=x86_64 --cross-prefix=x86_64-w64-mingw32- --enable-cross-compile --disable-network --disable-everything --disable-autodetect --disable-gpl --disable-nonfree --disable-doc --disable-debug --disable-x86asm --disable-shared --enable-static --enable-ffmpeg --enable-ffprobe --enable-protocol='file,pipe' --enable-demuxer='mp3,mov,aac,wav,flac,ogg,asf,matroska,avi,amr' --enable-decoder='aac,mp3,mp3float,opus,vorbis,flac,alac,pcm_s16le,pcm_s16be,pcm_u8,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,wmav1,wmav2,amrnb,amrwb,ac3,eac3' --enable-parser='aac,aac_latm,ac3,flac,mpegaudio,opus,vorbis' --enable-filter='aresample,pan,aformat,anull' --enable-encoder=pcm_s16le --enable-muxer=wav --extra-ldflags=-static
```

The complete captured `-buildconf` output follows. The first three Wine
lines are CI's first-run prefix setup and are not FFmpeg output.

```text
wine: created the configuration directory '/home/runner/.wine'
wine: failed to open L"C:\windows\syswow64\rundll32.exe": c0000135
wine: configuration in L"/home/runner/.wine" has been updated.
ffmpeg version n9.0.2 Copyright (c) 2000-2026 the FFmpeg developers
  built with gcc 13-posix (GCC)
  configuration: --target-os=mingw32 --arch=x86_64 --cross-prefix=x86_64-w64-mingw32- --enable-cross-compile --disable-network --disable-everything --disable-autodetect --disable-gpl --disable-nonfree --disable-doc --disable-debug --disable-x86asm --disable-shared --enable-static --enable-ffmpeg --enable-ffprobe --enable-protocol='file,pipe' --enable-demuxer='mp3,mov,aac,wav,flac,ogg,asf,matroska,avi,amr' --enable-decoder='aac,mp3,mp3float,opus,vorbis,flac,alac,pcm_s16le,pcm_s16be,pcm_u8,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,wmav1,wmav2,amrnb,amrwb,ac3,eac3' --enable-parser='aac,aac_latm,ac3,flac,mpegaudio,opus,vorbis' --enable-filter='aresample,pan,aformat,anull' --enable-encoder=pcm_s16le --enable-muxer=wav --extra-ldflags=-static
  libavutil      61.  1.102 / 61.  1.102
  libavcodec     63.  1.102 / 63.  1.102
  libavformat    63.  1.102 / 63.  1.102
  libavdevice    63.  1.102 / 63.  1.102
  libavfilter    12.  1.102 / 12.  1.102
  libswscale     10.  1.102 / 10.  1.102
  libswresample   7.  1.102 /  7.  1.102

  configuration:
    --target-os=mingw32
    --arch=x86_64
    --cross-prefix=x86_64-w64-mingw32-
    --enable-cross-compile
    --disable-network
    --disable-everything
    --disable-autodetect
    --disable-gpl
    --disable-nonfree
    --disable-doc
    --disable-debug
    --disable-x86asm
    --disable-shared
    --enable-static
    --enable-ffmpeg
    --enable-ffprobe
    --enable-protocol='file,pipe'
    --enable-demuxer='mp3,mov,aac,wav,flac,ogg,asf,matroska,avi,amr'
    --enable-decoder='aac,mp3,mp3float,opus,vorbis,flac,alac,pcm_s16le,pcm_s16be,pcm_u8,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,wmav1,wmav2,amrnb,amrwb,ac3,eac3'
    --enable-parser='aac,aac_latm,ac3,flac,mpegaudio,opus,vorbis'
    --enable-filter='aresample,pan,aformat,anull'
    --enable-encoder=pcm_s16le
    --enable-muxer=wav
    --extra-ldflags=-static

Exiting with exit code 0
```

`--disable-x86asm` avoids adding NASM to the build environment. This
may reduce decode speed; Phase B will use the exact bundled binary.


## Corresponding source and static runtime notices (audit F-04)

Every release must carry ffmpeg-n9.0.2-946fcce.tar.gz from the official FFmpeg
repository's exact 946fcce07b6dcd0331c8cc609192aeff5e1924f8 commit, plus the
unmodified build_ffmpeg.sh from the release source tree. The archive URL, commit
and SHA-256 are pinned in packaging/licenses/ffmpeg-source.json. The staging
gate checks both before any draft upload. The archive is not committed.

The existing static MinGW build also embeds runtime code. Exact MinGW v11.0.1
and winpthreads notices (peeled c3e587c067a00a561899d49d3e63a659e38802ec) are
retained under packaging/licenses, copied beside FFmpeg and into licenses, and
included in generated notices and inventory attribution. Hashes and source URLs
are recorded in packaging/licenses/sources.json. winpthreads's conjunction is
MIT AND BSD-3-Clause. The MinGW aggregate is separately identified, not silently
relabeled as one of those licenses; ADR 0026 records the approved exact exception.
Wine initialization output is excluded from the generated build banner, while
the exact original native input remains hash-verified and unchanged.


PM approved ADR 0026 on 2026-10-25. The MinGW aggregate is allowed only for the
two independently pinned existing FFmpeg executables and unchanged shipped notice.
Any byte or attribution change fails the gate again. The global license allowlist
is unchanged. tools/mingw_runtime.py enforces the independent pins.
