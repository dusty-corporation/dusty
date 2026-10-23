# Third-party notices (draft)

Generated from actual COLLECT files and embedded module origins.
This audit bundle is not approved for redistribution. UNKNOWN and static LGPL
findings need PM review; metadata is not a complete native license audit.

Qt/PySide6 shared DLLs remain replaceable under LGPL-3.0-only; FFmpeg is
a separate LGPL-2.1-or-later executable. Original available license and copyright
texts are retained in licenses/. Missing source offers/notices remain release blockers.
Copyright statements are preserved in those original texts; where no text is
available, attribution and transitive notices are unresolved, not waived.

| Component | Version | License | Source/evidence |
|---|---|---|---|
| cpython | 3.12.11 | PSF-2.0 | https://github.com/python/cpython |
| dusty | 0.0.1 | MIT | https://github.com/dusty-corporation/dusty |
| embedded-native-review | unresolved | UNKNOWN | UNKNOWN |
| ffmpeg | n9.0.2 | LGPL-2.1-or-later | https://git.ffmpeg.org/ffmpeg.git |
| jfk-fixture | 1961 | LicenseRef-Public-Domain | https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav |
| libffi | unresolved | UNKNOWN | https://github.com/libffi/libffi |
| libxml2 | 2.11.9 | MIT | https://gitlab.gnome.org/GNOME/libxml2 |
| libxslt | 1.1.45 | MIT | https://gitlab.gnome.org/GNOME/libxslt |
| lxml | 6.1.3 | BSD-3-Clause | https://lxml.de/ |
| lxml-iconv | unresolved | LGPL-2.1-or-later | https://www.gnu.org/software/libiconv/ |
| lxml-zlib | unresolved | Zlib | https://zlib.net |
| microsoft-runtime | unresolved | LicenseRef-Microsoft-EULA | https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files |
| openssl | 3.0.16 | Apache-2.0 | https://github.com/openssl/openssl |
| pyinstaller-bootloader | 6.16.0 | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | https://github.com/pyinstaller/pyinstaller |
| pyinstaller-runtime-hooks | 6.16.0 | Apache-2.0 | https://github.com/pyinstaller/pyinstaller |
| pyside6-essentials | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Homepage, https://pyside.org |
| python-docx | 1.2.0 | MIT | Changelog, https://github.com/python-openxml/python-docx/blob/master/HISTORY.rst |
| qt-software-opengl | unresolved | UNKNOWN | https://code.qt.io/cgit/qt/qtbase.git/ |
| shiboken6 | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Homepage, https://pyside.org |
| typing-extensions | 4.16.0 | PSF-2.0 | Bug Tracker, https://github.com/python/typing_extensions/issues |
| whisper.cpp | v1.9.5 | MIT | https://github.com/ggml-org/whisper.cpp |

## Native pins

whisper.cpp: {'tag': 'v1.9.5', 'commit': 'd1be6fde11ac6e0407606b4e42fe72d34add8037', 'patch': 'native/patches/0001-vad-timestamp-mapping.patch', 'patch_sha256': '5dea476a89b6a7ac725cffeb72e2d80a33dc04ac0f0635dfe28cc4a25d911d1b'}

FFmpeg: {'tag': 'n9.0.2', 'commit': '946fcce07b6dcd0331c8cc609192aeff5e1924f8'}

Exact configuration and build output:

```text
wine: created the configuration directory '/home/runner/.wine'
wine: failed to open L"C:\\windows\\syswow64\\rundll32.exe": c0000135
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
