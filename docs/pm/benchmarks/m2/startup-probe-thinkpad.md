# M2 ThinkPad startup probe

Owner supplied on 2026-10-22; exit code 0. ThinkPad X1 Carbon, i7-1365U,
Iris Xe, whisper.cpp v1.9.5, Tiny, four threads, VAD off. CPU dispatch:
alderlake. These are Owner measurements, not local agent runs.

| Backend | Run 1 wall s | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---:|---:|---:|---:|---:|
| CPU | 0.940 | 0.760 | 0.750 | 0.751 | 0.752 |
| Vulkan | 1.000 | 0.627 | 0.617 | 0.633 | 0.644 |

Owner reports Vulkan model load approximately 85-93 ms and encode 85-92 ms.
No finer per-run timing breakdown or cold-cache measurement was supplied.

PM decision: close ISSUE-004. There is no significant recurring startup cost
in these Iris Xe measurements. The M1 apparent fixed cost was inferred from
total transcription times, not isolated overhead. Retain ADR 0004's engine
process per file. A fresh machine likely pays a one-time Vulkan shader compile;
the desktop's first observed run was approximately 13 s, with later runs under
0.6 s. The installer self-test will absorb that first-run cost. The desktop
trace does not directly identify the driver's internal compilation work.
