# Third-party notices

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
| dusty | 1.0.1 | Apache-2.0 | Copyright 2026 Dusty contributors | https://github.com/dusty-corporation/dusty |
| ffmpeg | n9.0.2 | LGPL-2.1-or-later | Copyright 2000-2026 the FFmpeg developers; exact build banner retained below | https://git.ffmpeg.org/ffmpeg.git |
| jfk-fixture | 1961 | LicenseRef-Public-Domain | 1961 US government work, President John F. Kennedy; public domain | https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav |
| libffi | ABI-8 (CPython build 20250902) | MIT | libffi - Copyright (c) 1996-2024  Anthony Green, Red Hat, Inc and others. | https://github.com/libffi/libffi |
| microsoft-visual-cpp-runtime | 14.44.35211.0 | LicenseRef-Microsoft-Visual-Cpp-Runtime | © Microsoft Corporation. All rights reserved. | https://aka.ms/vs/17/redistribution |
| mingw-w64-runtime | 11.0.1 | LicenseRef-MinGW-w64-runtime | See retained upstream notices | https://github.com/mingw-w64/mingw-w64/tree/c3e587c067a00a561899d49d3e63a659e38802ec |
| openssl | 3.0.16 | Apache-2.0 | Copyright 1998-2025 The OpenSSL Authors. All rights reserved. | https://github.com/openssl/openssl |
| public-ca-certificates | 2026-10-24 | LicenseRef-Public-CA-Certificate | See retained upstream notices | resources/tls/sources.json |
| pyinstaller-bootloader | 6.16.0 | GPL-2.0-or-later WITH PyInstaller-bootloader-exception | Copyright 2010-2023 PyInstaller Development Team; additional notices in COPYING.txt | https://github.com/pyinstaller/pyinstaller |
| pyinstaller-runtime-hooks | 6.16.0 | Apache-2.0 | Copyright PyInstaller Development Team; original notice in COPYING.txt | https://github.com/pyinstaller/pyinstaller |
| pyside6-essentials | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Copyright (C) The Qt Company Ltd. and other contributors. | Homepage, https://pyside.org |
| shiboken6 | 6.9.2 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | See retained upstream copyright notices | Homepage, https://pyside.org |
| whisper.cpp | v1.9.5 | MIT | Copyright (c) 2023-2026 The ggml authors | https://github.com/ggml-org/whisper.cpp |
| winpthreads | 11.0.1 | MIT AND BSD-3-Clause | See retained upstream notices | https://github.com/mingw-w64/mingw-w64/tree/c3e587c067a00a561899d49d3e63a659e38802ec |

## Statically linked FFmpeg toolchain runtime notices

MinGW-w64 runtime licensing
***************************

This program or library was built using MinGW-w64 and statically
linked against the MinGW-w64 runtime. Some parts of the runtime
are under licenses which require that the copyright and license
notices are included when distributing the code in binary form.
These notices are listed below.


========================
Overall copyright notice
========================

Copyright (c) 2009, 2010, 2011, 2012, 2013 by the mingw-w64 project

This license has been certified as open source. It has also been designated
as GPL compatible by the Free Software Foundation (FSF).

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

   1. Redistributions in source code must retain the accompanying copyright
      notice, this list of conditions, and the following disclaimer.
   2. Redistributions in binary form must reproduce the accompanying
      copyright notice, this list of conditions, and the following disclaimer
      in the documentation and/or other materials provided with the
      distribution.
   3. Names of the copyright holders must not be used to endorse or promote
      products derived from this software without prior written permission
      from the copyright holders.
   4. The right to distribute this software or to use it for any purpose does
      not give you the right to use Servicemarks (sm) or Trademarks (tm) of
      the copyright holders.  Use of them is covered by separate agreement
      with the copyright holders.
   5. If any files are modified, you must cause the modified files to carry
      prominent notices stating that you changed the files and the date of
      any change.

Disclaimer

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY EXPRESSED
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

======================================== 
getopt, getopt_long, and getop_long_only
======================================== 

Copyright (c) 2002 Todd C. Miller <Todd.Miller@courtesan.com> 
 
Permission to use, copy, modify, and distribute this software for any 
purpose with or without fee is hereby granted, provided that the above 
copyright notice and this permission notice appear in all copies. 
 	 
THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Sponsored in part by the Defense Advanced Research Projects
Agency (DARPA) and Air Force Research Laboratory, Air Force
Materiel Command, USAF, under agreement number F39502-99-1-0512.

        *       *       *       *       *       *       * 

Copyright (c) 2000 The NetBSD Foundation, Inc.
All rights reserved.

This code is derived from software contributed to The NetBSD Foundation
by Dieter Baron and Thomas Klausner.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE NETBSD FOUNDATION, INC. AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


===============================================================
gdtoa: Converting between IEEE floating point numbers and ASCII
===============================================================

The author of this software is David M. Gay.

Copyright (C) 1997, 1998, 1999, 2000, 2001 by Lucent Technologies
All Rights Reserved

Permission to use, copy, modify, and distribute this software and
its documentation for any purpose and without fee is hereby
granted, provided that the above copyright notice appear in all
copies and that both that the copyright notice and this
permission notice and warranty disclaimer appear in supporting
documentation, and that the name of Lucent or any of its entities
not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior
permission.

LUCENT DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
IN NO EVENT SHALL LUCENT OR ANY OF ITS ENTITIES BE LIABLE FOR ANY
SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.

        *       *       *       *       *       *       *

The author of this software is David M. Gay.

Copyright (C) 2005 by David M. Gay
All Rights Reserved

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appear in all copies and that
both that the copyright notice and this permission notice and warranty
disclaimer appear in supporting documentation, and that the name of
the author or any of his current or former employers not be used in
advertising or publicity pertaining to distribution of the software
without specific, written prior permission.

THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.  IN
NO EVENT SHALL THE AUTHOR OR ANY OF HIS CURRENT OR FORMER EMPLOYERS BE
LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
SOFTWARE.

        *       *       *       *       *       *       *

The author of this software is David M. Gay.

Copyright (C) 2004 by David M. Gay.
All Rights Reserved
Based on material in the rest of /netlib/fp/gdota.tar.gz,
which is copyright (C) 1998, 2000 by Lucent Technologies.

Permission to use, copy, modify, and distribute this software and
its documentation for any purpose and without fee is hereby
granted, provided that the above copyright notice appear in all
copies and that both that the copyright notice and this
permission notice and warranty disclaimer appear in supporting
documentation, and that the name of Lucent or any of its entities
not be used in advertising or publicity pertaining to
distribution of the software without specific, written prior
permission.

LUCENT DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
IN NO EVENT SHALL LUCENT OR ANY OF ITS ENTITIES BE LIABLE FOR ANY
SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.


=========================
Parts of the math library
=========================

Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.

Developed at SunSoft, a Sun Microsystems, Inc. business.
Permission to use, copy, modify, and distribute this
software is freely granted, provided that this notice
is preserved.

        *       *       *       *       *       *       *

Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.

Developed at SunPro, a Sun Microsystems, Inc. business.
Permission to use, copy, modify, and distribute this
software is freely granted, provided that this notice
is preserved.

        *       *       *       *       *       *       *

FIXME: Cephes math lib
Copyright (C) 1984-1998 Stephen L. Moshier

It sounds vague, but as to be found at
<http://lists.debian.org/debian-legal/2004/12/msg00295.html>, it gives an
impression that the author could be willing to give an explicit
permission to distribute those files e.g. under a BSD style license. So
probably there is no problem here, although it could be good to get a
permission from the author and then add a license into the Cephes files
in MinGW runtime. At least on follow-up it is marked that debian sees the
version a-like BSD one. As MinGW.org (where those cephes parts are coming
from) distributes them now over 6 years, it should be fine.

===================================
Headers and IDLs imported from Wine
===================================

Some header and IDL files were imported from the Wine project. These files
are prominent maked in source. Their copyright belongs to contributors and
they are distributed under LGPL license.

Disclaimer

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.


Copyright (c) 2011 mingw-w64 project

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.


/*
 * Parts of this library are derived by:
 *
 * Posix Threads library for Microsoft Windows
 *
 * Use at own risk, there is no implied warranty to this code.
 * It uses undocumented features of Microsoft Windows that can change
 * at any time in the future.
 *
 * (C) 2010 Lockless Inc.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *
 *
 *  * Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *  * Neither the name of Lockless Inc. nor the names of its contributors may be
 *    used to endorse or promote products derived from this software without
 *    specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AN
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
 * OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */


## Public CA trust-anchor data

PM-approved public certificate data, not Dusty-owned software or a new library.
Only four fingerprint-pinned PEM files may use this data attribution.
Official CA references, fingerprints and acquisition provenance are retained
in resources/tls/sources.json. No CA update service is invoked.
No Apache-2.0 license is claimed for these public certificate records.

## Native pins

whisper.cpp: {'tag': 'v1.9.5', 'commit': 'd1be6fde11ac6e0407606b4e42fe72d34add8037', 'patch': 'native/patches/0001-vad-timestamp-mapping.patch', 'patch_sha256': '5dea476a89b6a7ac725cffeb72e2d80a33dc04ac0f0635dfe28cc4a25d911d1b'}

FFmpeg: {'tag': 'n9.0.2', 'commit': '946fcce07b6dcd0331c8cc609192aeff5e1924f8'}

Exact configuration and build output:

```text
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

Redistribution basis: maintainer-held VS 2022 Community individual license, section 4.a.i
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

