# 0004 — Engine process model
- Status: Accepted
- Date: 2026-10-21
## Context
Inference must be isolated and cancellable.
## Decision
Launch `whisper-cli.exe` as a child process per file. Do not ship server binaries or Python bindings.
## Consequences
Model startup repeats per file; process crashes are contained.
## Alternatives considered
In-process bindings and a persistent server; both increase complexity.
