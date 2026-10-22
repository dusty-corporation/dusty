# ISSUE-004 - Iris Xe per-run startup cost
- Severity: S2
- Milestone: M1
- Status: Open
- Environment: ThinkPad X1 Carbon proxy, i7-1365U, Iris Xe 96EU, Windows, pinned whisper.cpp v1.9.5 Vulkan package

## Steps to reproduce
Run the public benchmark clip with tiny and small on the ThinkPad Iris Xe
backend, each as a separate engine process, and compare wall time with the
same sequence on the desktop GPU.

## Expected
Process startup and backend setup consume a small share of a run, so
batches of short files do not spend most of their time reinitializing.

## Actual
The PM reports an apparent fixed cost of about 40 seconds per Iris Xe run:
tiny took 48 seconds and small took 88 seconds. The desktop GPU appears to
spend about 9 seconds. These numbers are preliminary and do not isolate
startup from model load or inference time.

## Evidence
PM Phase B observation on the ThinkPad proxy. Preserve the full public
CSV and engine timing evidence under `docs/pm/benchmarks/m1/` when it
arrives. No private recording content belongs in this issue.

## Proposed investigation for M2
Measure process launch, Vulkan pipeline creation, model load, and inference
separately on Iris Xe. Check whether Vulkan pipeline cache reuse lowers the
cost. If not, assess a long-lived engine process per batch against ADR 0004
and the offline, crash isolation, and cancellation requirements. Any change
to ADR 0004 needs PM approval before implementation.

## Regression test added
None yet. M2 should add a repeatable short-file batch timing test after
the root cause is known.
