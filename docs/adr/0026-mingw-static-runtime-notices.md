# 0026 - Existing MinGW static runtime notice closure

- Status: Accepted by PM, 2026-10-25
- Date: 2026-10-25

## Context

PM Phase C F-04 directs shipping notices and inventory attribution for the
MinGW-w64 runtime and winpthreads already statically present in pinned FFmpeg.
These are not newly added libraries or native binaries. Review of the exact
upstream v11.0.1 aggregate found terms beyond the currently enumerated allowlist.

## Decision

Retain the complete byte-pinned upstream notices without edits, both next to
FFmpeg and under licenses, and include them in generated notices. Attribute
winpthreads as MIT AND BSD-3-Clause. Attribute the full MinGW runtime aggregate
as LicenseRef-MinGW-w64-runtime. PM approves only these existing FFmpeg/ffprobe static runtime bytes and the
exact retained notice. This is not a general LicenseRef or ZPL-2.1 allowance.
The bundle gate requires independent fixed pins, exact attribution to those two
executables, both shipped/inventoried notice copies and the full notice text.

The overall five-condition section matches SPDX ZPL-2.1; other sections retain
getopt, gdtoa, math and Wine header notices, including the upstream Cephes caveat.
This is not accurately described as only MIT or BSD-3-Clause. Exact text:
packaging/licenses/mingw-w64-runtime.txt; provenance in sources.json.
References reviewed: https://www.mingw-w64.org/source/ and
https://spdx.org/licenses/ZPL-2.1.html. Upstream peeled commit:
c3e587c067a00a561899d49d3e63a659e38802ec.

## Consequences

Only the exact approved bytes pass. Any binary or notice change fails again and
requires a new PM review. No global license allowance, binary substitution,
relabeling, or release publication is authorized. FFmpeg corresponding source
and exact build script remain mandatory separate release assets.

## Independent approved pins

- bin/ffmpeg/ffmpeg.exe:
  c7632b3043595244e4d5b27099701b88eab86c6bebaea9547d471105824e2fa3
- bin/ffmpeg/ffprobe.exe:
  8913237fd8e69fb568836249d31680822d19ff503f93c4cb163e6942c98e9a14
- packaging/licenses/mingw-w64-runtime.txt and both shipped copies:
  e9b2dc02451ea29092a1f25fa0f3c07207ed421f1807dffb0c4e6dce69dee7bd

The binary pins match the unchanged minimal-ffmpeg.zip production archive pin
in native/versions.toml. tools/mingw_runtime.py enforces these independently of
inventory hashes, so regenerating an inventory cannot bless changed bytes.
