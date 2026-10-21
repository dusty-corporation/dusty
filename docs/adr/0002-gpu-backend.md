# 0002 - GPU backend
- Status: Accepted
- Date: 2026-10-21
## Context
The target machines have different GPU vendors.
## Decision
Use Vulkan with CPU fallback. Exclude CUDA redistributables.
## Consequences
M1 must verify Vulkan behavior on both machines.
## Alternatives considered
CUDA; excluded by the open-source redistribution policy.
