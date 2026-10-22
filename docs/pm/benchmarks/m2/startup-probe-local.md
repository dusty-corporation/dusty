# M2 local startup probe validation

Date: 2026-10-22. This is local kit validation, not the requested independent
ThinkPad and desktop evidence. Pinned whisper.cpp v1.9.5, tiny, four threads,
public 11-second JFK clip, VAD off. All ten processes exited 0. Vulkan was
explicitly selected for every Vulkan row; CPU dispatch selected Haswell.

Command: `pwsh -NoProfile -File build/probe-package-1/startup-probe-m2/tools/bench/startup-probe.ps1`

| Backend | Run | First progress s | Load ms | Encode ms | Decode ms | Engine total ms | Wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| CPU | 1 | 0.631 | 85.9 | 252.8 | 0.0 | 526.7 | 0.648 |
| CPU | 2 | 0.560 | 81.3 | 242.5 | 0.0 | 511.5 | 0.574 |
| CPU | 3 | 0.546 | 81.4 | 238.9 | 0.0 | 498.1 | 0.561 |
| CPU | 4 | 0.728 | 96.5 | 356.6 | 0.0 | 680.6 | 0.745 |
| CPU | 5 | 0.653 | 97.7 | 304.3 | 0.0 | 601.0 | 0.669 |
| Vulkan | 1 | 13.872 | 180.7 | 4162.1 | 0.0 | 13585.0 | 13.935 |
| Vulkan | 2 | 0.532 | 162.9 | 14.9 | 0.0 | 325.6 | 0.577 |
| Vulkan | 3 | 0.532 | 148.5 | 17.8 | 0.0 | 339.2 | 0.579 |
| Vulkan | 4 | 0.511 | 151.5 | 16.1 | 0.0 | 316.3 | 0.558 |
| Vulkan | 5 | 0.518 | 153.1 | 16.5 | 0.0 | 323.3 | 0.565 |

The first Vulkan run was slower than the later runs in this session. These
numbers do not identify the driver-internal cause and do not resolve ISSUE-004.
No cache was cleared before the test. First progress on this short clip arrives
near completion and is not a direct shader-compilation timer.
