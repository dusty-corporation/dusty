# ISSUE-003 - CI native binaries use unsupported CPU instructions
- Severity: S1
- Milestone: M1
- Status: Resolved 2026-10-21
- Environment: CI Windows 2022 runner; Owner desktop Ryzen and target Surface AVX2 CPUs

## Steps to reproduce
Run the CI-built Vulkan `whisper-cli.exe` from run 39691606062 with the tiny
model and the public-domain JFK fixture on the Owner desktop.

## Expected
The CLI initializes a supported CPU backend and transcribes the fixture.

## Actual
The process exits with Windows status `0xc000001d` (illegal instruction)
after reporting the Vulkan device. The Owner independently observed the same
crash. Do not use that binary again.

## Root cause
The original build did not set `GGML_NATIVE`. Pinned whisper.cpp v1.9.5
defaults it to ON for a local, non-cross-compiled build. The CI Vulkan job
log at https://github.com/dusty-corporation/dusty/actions/runs/39691606062
shows `HAS_AVX512_1 - Success` followed by
`Adding CPU backend variant ggml-cpu: /arch:AVX512 GGML_AVX512`.
The Owner's Ryzen and target Surface support AVX2 but not AVX-512. This
establishes the incompatible CI CPU compilation target as the cause of the
illegal instruction.

The initial CI checks inspected imports and built the executable, but did
not inspect CMake's CPU target or execute it on an AVX2-only machine. The
Windows CI runner could execute its own native build, so a runner-only
smoke test would also have missed this portability fault.

## Fix
Build with `GGML_NATIVE=OFF`, `GGML_BACKEND_DL=ON`, and
`GGML_CPU_ALL_VARIANTS=ON`, with shared backend DLLs packaged beside both
executables. The build must print all `GGML_*` cache values and fail if
`GGML_NATIVE` is ON. Verify clean-machine imports, runtime dispatch, and
the Owner desktop rerun before resolving this issue. ADR 0015 records the
portable backend layout.

## Regression test
CI run 39692634372 passed CPU and Vulkan builds. It printed all GGML
cache values, including `GGML_NATIVE:BOOL=OFF`, and checked imports of
both executables and all backend DLLs. The implementing engineer ran
both replacement binaries on the desktop against the public-domain JFK
fixture. Both exited 0 and loaded `ggml-cpu-haswell.dll`; Vulkan also
loaded `ggml-vulkan.dll` and selected the RTX 3080 Ti. The Owner's
independent rerun succeeded. The Owner downloaded run 39692634372's
`whisper-vulkan` artifact and the draft `ggml-tiny.bin` model, then ran the
public-domain JFK fixture on the Ryzen desktop. The process loaded
`ggml-vulkan.dll` and `ggml-cpu-haswell.dll`, reported `using Vulkan0 backend`,
transcribed the clip, and exited 0. This confirms the replacement binary
works on the machine that crashed with the original artifact.
