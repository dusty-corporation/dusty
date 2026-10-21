# Minimal FFmpeg for M1

CI run https://github.com/dusty-corporation/dusty/actions/runs/39692158489
cross-compiled pinned FFmpeg `n9.0.2` with Ubuntu 24.04 MinGW-w64. It
produced `ffmpeg.exe` (4,992,512 bytes) and `ffprobe.exe` (4,799,488
bytes). The workflow decoded all 17 supported extensions from the public
domain JFK fixture and rejected the no-audio, zero-byte, and corrupt
fixtures. The format list and provenance are in
`tests/fixtures/AUDIO_SOURCES.md`.

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
