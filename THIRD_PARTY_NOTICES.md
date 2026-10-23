# Third-party notices (draft)

Generated from actual COLLECT files and embedded module origins.
Component/provider attribution covers actual files and embedded modules, including
the native runtime files. Unknown providers fail the license gate.

Qt/PySide6 shared DLLs remain replaceable under LGPL-3.0-only; FFmpeg is
a separate LGPL-2.1-or-later executable. Original available license and copyright
texts are retained in licenses/. Qt remains replaceable; corresponding source links
and the exact FFmpeg revision/configuration follow below.
Copyright statements are preserved in those original texts; where no text is
available, attribution and transitive notices are unresolved, not waived.

| Component | Version | License | Copyright | Source/evidence |
|---|---|---|---|---|
| cpython | 3.12.11 | PSF-2.0 | Copyright © 2001-2023 Python Software Foundation. Copyright © 2000 BeOpen.com. Copyright © 1995-2001 CNRI. Copyright © 1991-1995 SMC. | https://github.com/python/cpython |
| dusty | 0.0.1 | Apache-2.0 | Copyright 2026 Dusty contributors | https://github.com/dusty-corporation/dusty |
| ffmpeg | n9.0.2 | LGPL-2.1-or-later | Copyright 2000-2026 the FFmpeg developers; exact build banner retained below | https://git.ffmpeg.org/ffmpeg.git |
| jfk-fixture | 1961 | LicenseRef-Public-Domain | 1961 US government work, President John F. Kennedy; public domain | https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav |
| libffi | ABI-8 (CPython build 20250902) | MIT | libffi - Copyright (c) 1996-2024  Anthony Green, Red Hat, Inc and others. | https://github.com/libffi/libffi |
| microsoft-visual-cpp-runtime | 14.44.35211.0 | LicenseRef-Microsoft-Visual-Cpp-Runtime | © Microsoft Corporation. All rights reserved. | https://aka.ms/vs/17/redistribution |
| openssl | 3.0.16 | Apache-2.0 | Copyright 1998-2025 The OpenSSL Authors. All rights reserved. | https://github.com/openssl/openssl |
| pyinstaller-bootloader | 6.16.0 | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | Copyright 2010-2023 PyInstaller Development Team; additional notices in COPYING.txt | https://github.com/pyinstaller/pyinstaller |
| pyinstaller-runtime-hooks | 6.16.0 | Apache-2.0 | Copyright PyInstaller Development Team; original notice in COPYING.txt | https://github.com/pyinstaller/pyinstaller |
| pyside6-essentials | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Copyright (C) The Qt Company Ltd. and other contributors. | Homepage, https://pyside.org |
| shiboken6 | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | See retained upstream copyright notices | Homepage, https://pyside.org |
| whisper.cpp | v1.9.5 | MIT | Copyright (c) 2023-2026 The ggml authors | https://github.com/ggml-org/whisper.cpp |

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

## Microsoft Visual C++ runtime terms

Redistribution basis: Owner-held VS 2022 Community individual license, section 4.a.i
and the Visual C++ Runtime Files redistribution list. The runtime EULA is protective
end-user terms under section 4.b, not an independent redistribution grant.
Only release VC/redist CRT files are copied unmodified; see crt-provenance.json
in the audit artifact. UCRT/API-set and other Microsoft files are excluded.
The M5 installer must present these terms alongside Dusty's Apache-2.0 license
and require agreement. Originals and document source hashes: licenses/microsoft/.

MICROSOFT SOFTWARE LICENSE TERMS 
MICROSOFT VISUAL C++ 2015 - 2022 RUNTIME  
These license terms are an agreement between Microsoft Corporation (or based on where you live, one of its affiliates) 
and you. They apply to the software named above. The terms also apply to any Microsoft services or updates for the 
software, except to the extent those have different terms. 
IF YOU COMPLY WITH THESE LICENSE TERMS, YOU HAVE THE RIGHTS BELOW. 
1. INSTALLATION AND USE RIGHTS.  
You may install and use any number of copies of the software. 
2. TERMS FOR SPECIFIC COMPONENTS. 
a. Microsoft Platforms. The software may include components from Microsoft Windows; Microsoft Windows 
Server; Microsoft SQL Server; Microsoft Exchange; Microsoft Office; and Microsoft SharePoint. These components 
are governed by separate agreements and their own product support policies, as described in the Microsoft 
“Licenses” folder accompanying the software, except that, if license terms for those components are also included 
in the associated installation directory, those license terms control. 
b. Third Party Components. The software may include third party components with separate legal notices or 
governed by other agreements, as may be described in the notices file(s) accompanying the software.  
3. SCOPE OF LICENSE. The software is licensed, not sold. This agreement only gives you some rights to use the 
software. Microsoft reserves  all other rights. Unless applicable law gives you more rights despite this limitation, you 
may use the software only as expressly permitted in this agreement. In doing so, you must comply with any technical 
limitations in the software that only allow you to use it in certain ways. You may not 
• work around any technical limitations in the software; 
• reverse engineer, decompile or disassemble the software, or otherwise attempt to derive the source code for the 
software except, and only to the extent required by third party licensing terms governing the use of certain open 
source components that may be included in the software; 
• remove, minimize, block or modify any notices of Microsoft or its suppliers in the software;  
• use the software in any way that is against the law;  
• share, publish, rent or lease the software; or  
• provide the software as a stand-alone offering or combined with any of your applications for others to use, or 
transfer the software or this agreement to any third party. 
4. EXPORT RESTRICTIONS. You must comply with all domestic and international export laws and regulations that 
apply to the software, which include restrictions on destinations, end users, and end use. For further information on 
export restrictions, visit www.microsoft.com/exporting.  
5. SUPPORT SERVICES. Because this software is “as is,” we may not provide support services for it. 
6. ENTIRE AGREEMENT. This agreement, and the terms for supplements, updates, Internet-based services and 
support services that you use, are the entire agreement for the software and support services. 
7. APPLICABLE LAW. If you acquired the software in the United States, Washington law applies to interpretation of 
and claims for breach of this agreement, and the laws of the state where you live apply to all other claims. If you 
acquired the software in any other country, its laws apply. 
8. CONSUMER RIGHTS; REGIONAL VARIATIONS. This agreement describes certain legal rights. You may have 
other rights, including consumer rights, under the laws of your state or country. Separate and apart from your 
relationship with Microsoft, you may also have rights with respect to the party from which you acquired the software. 
This agreement does not change those other rights if the laws of your state or country do not permit it to do so. For 
example, if you acquired the software in one of the below regions, or mandatory country law applies, then the 
following provisions apply to you: 
a. Australia. You have statutory guarantees under the Australian Consumer Law and nothing in this agreement is 
intended to affect those rights. 

b. Canada. If you acquired this software in Canada, you may stop receiving updates by turning off the automatic 
update feature, disconnecting your device from the Internet (if and when you re-connect to the Internet, 
however, the software will resume checking for and installing updates), or uninstalling the software. The product 
documentation, if any, may also specify how to turn off updates for your specific device or software. 
c. Germany and Austria. 
(i) Warranty. The properly licensed software will perform substantially as described in any Microsoft 
materials that accompany the software. However, Microsoft gives no contractual guarantee in relation to the 
licensed software. 
(ii) Limitation of Liability. In case of intentional conduct, gross negligence, claims based on the Product 
Liability Act, as well as, in case of death or personal or physical injury, Microsoft is liable according to the 
statutory law. 
Subject to the foregoing clause (ii), Microsoft will only be liable for slight negligence if Microsoft is in breach of 
such material contractual obligations, the fulfillment of which facilitate the due performance of this agreement, 
the breach of which would endanger the purpose of this agreement and the compliance with which a party may 
constantly trust in (so-called "cardinal obligations"). In other cases of slight negligence, Microsoft will not be liable 
for slight negligence. 
9. DISCLAIMER OF WARRANTY. THE SOFTWARE IS LICENSED “AS-IS.” YOU BEAR THE RISK OF USING IT. 
MICROSOFT GIVES NO EXPRESS WARRANTIES, GUARANTEES OR CONDITIONS. TO THE EXTENT 
PERMITTED UNDER YOUR LOCAL LAWS, MICROSOFT EXCLUDES THE IMPLIED WARRANTIES OF 
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. 
10. LIMITATION ON AND EXCLUSION OF DAMAGES. YOU CAN RECOVER FROM MICROSOFT AND ITS 
SUPPLIERS ONLY DIRECT DAMAGES UP TO U.S. $5.00. YOU CANNOT RECOVER ANY OTHER DAMAGES, 
INCLUDING CONSEQUENTIAL, LOST PROFITS, SPECIAL, INDIRECT OR INCIDENTAL DAMAGES. 
This limitation applies to (a) anything related to the software, services, content (including code) on third party 
Internet sites, or third party applications; and (b) claims for breach of contract, breach of warranty, guarantee or 
condition, strict liability, negligence, or other tort to the extent permitted by applicable law. 
It also applies even if Microsoft knew or should have known about the possibility of the damages. The above 
limitation or exclusion may not apply to you because your country may not allow the exclusion or limitation of 
incidental, consequential or other damages. 
 
EULA ID: Cpp_2015-2022_ENU.1033

