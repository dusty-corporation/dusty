# 0015 - Native CPU dispatch and backend layout
- Status: Implemented for M1 spike; PM review pending
- Date: 2026-10-21

## Context
The first Windows CI build used whisper.cpp v1.9.5's default
`GGML_NATIVE=ON`. The CI runner detected AVX-512 and built its only CPU
backend with `/arch:AVX512`. The Owner's AVX2 desktop exited with
`0xc000001d`, recorded in ISSUE-003. Both the desktop and Surface must run
the same distributed binaries.

Pinned `ggml/CMakeLists.txt` defines `GGML_BACKEND_DL` and
`GGML_CPU_ALL_VARIANTS`; both default to OFF, and the former requires
`BUILD_SHARED_LIBS`. Pinned `ggml/src/CMakeLists.txt` builds x64, SSE4.2,
Sandy Bridge, Haswell, Skylake-X, Cannon Lake, Cascade Lake, Ice Lake,
and Alder Lake variants with MSVC. The variants are selected at runtime
from separate backend DLLs.

## Decision
Build separate CPU and Vulkan packages. Both use `GGML_NATIVE=OFF`,
`GGML_BACKEND_DL=ON`, `GGML_CPU_ALL_VARIANTS=ON`, `BUILD_SHARED_LIBS=ON`,
and `/MT`. Bundle every generated whisper.cpp and ggml DLL in the same
folder as each CLI. The CPU package has no Vulkan dependency. The Vulkan
package may import only the system `vulkan-1.dll` beyond Windows system
DLLs and bundled DLLs. Its use still requires a working GPU driver.

CI prints every `GGML_*` CMake cache value and fails if `GGML_NATIVE` is
ON, if either dispatch option is OFF, or if the x64 and Haswell backend
DLLs are absent. CI checks imports of every packaged executable and DLL
with `dumpbin /dependents`.

## Evidence
The first static CPU package imported only `KERNEL32.dll` and
`ADVAPI32.dll`; the first Vulkan package additionally imported
`vulkan-1.dll`. Those binaries were not portable because their compiled
CPU backend required AVX-512. The dispatch build's imports, runtime
variant selection, and Owner test remain pending and must be recorded
before ISSUE-003 is resolved.

## Consequences
The package includes more DLLs and is larger. Every backend DLL must be
copied into the bench kit and later app package. The startup log must be
used to confirm the loaded CPU variant during benchmarks.

## Alternatives considered
A single Vulkan build would leave the CPU fallback coupled to Vulkan
loader availability. A single AVX2 baseline would be portable to the two
target machines but would discard faster variants on capable CPUs. If the
dynamic dispatch build fails on pinned Windows/MSVC, the approved fallback
is a conservative AVX2 baseline with `GGML_NATIVE=OFF`, AVX, AVX2, FMA,
and F16C enabled and AVX-512 disabled. Any fallback must be measured and
recorded before use.
