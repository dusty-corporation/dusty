# ISSUE-004 - Iris Xe per-run startup cost
- Severity: S2
- Milestone: M1
- Status: Resolved
- Environment: ThinkPad X1 Carbon proxy, i7-1365U, Iris Xe 96EU, Windows, pinned whisper.cpp v1.9.5 Vulkan package

## Steps to reproduce
Run the public benchmark clip with tiny and small on the ThinkPad Iris Xe
backend, each as a separate engine process, and compare wall time with the
same sequence on the desktop GPU.

## Expected
Process startup and backend setup consume a small share of a run, so
batches of short files do not spend most of their time reinitializing.

## Actual
The PM reports an apparent fixed cost of about 40 seconds per Iris Xe run.
The public CSV records tiny at 48.268 seconds and small at 87.760 seconds
on ThinkPad Vulkan, versus 9.877 and 14.004 seconds on desktop Vulkan.
These wall times do not isolate startup from model load or inference time.

## Evidence
PM Phase B observation, now backed by the ThinkPad and desktop public
Vulkan CSVs under `docs/pm/benchmarks/m1/`. No private recording content
belongs in this issue.

## Proposed investigation for M2
Measure process launch, Vulkan pipeline creation, model load, and inference
separately on Iris Xe. Check whether Vulkan pipeline cache reuse lowers the
cost. If not, assess a long-lived engine process per batch against ADR 0004
and the offline, crash isolation, and cancellation requirements. Any change
to ADR 0004 needs PM approval before implementation.

## Regression test added
`tools/bench/startup-probe.ps1` runs five CPU and five Vulkan tiny processes,
checks actual Vulkan selection, and records first progress and engine timings.
`setup-startup-probe.ps1` verifies the published engine archives and tiny model.
The standalone kit is available in draft `startup-probe-m2`.

Desktop kit validation on 2026-10-22 completed all ten runs: Vulkan run 1 took
13.935 seconds, and runs 2-5 took 0.558-0.579 seconds. This is not the requested
ThinkPad evidence and does not establish the driver-internal cause. The Owner
confirmed this is the desktop measurement, so no desktop rerun is needed.
See `docs/pm/benchmarks/m2/startup-probe-local.md`. The ThinkPad measurement
was subsequently supplied and resolves this issue as recorded below.

## Resolution

PM decision, 2026-10-22: close this issue. Owner's ThinkPad probe exited 0
with Tiny, four threads, VAD off, and alderlake CPU dispatch. CPU wall times
were 0.940 / 0.760 / 0.750 / 0.751 / 0.752 s; Vulkan wall times were
1.000 / 0.627 / 0.617 / 0.633 / 0.644 s. Vulkan load was approximately
85-93 ms and encode 85-92 ms. See `startup-probe-thinkpad.md` in the M2
benchmark folder.

There is no significant per-run startup cost on Iris Xe. The M1 fixed-cost
claim was an inference from total transcription times, not a measured
startup overhead. ADR 0004 remains unchanged: one engine process per file.
A fresh machine likely pays a one-time Vulkan shader compile, approximately
13 s on the desktop's first observed run; the installer self-test will absorb
that cost. This is the PM's interpretation, not a direct driver trace.
