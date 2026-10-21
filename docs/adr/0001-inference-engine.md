# 0001 - Inference engine
- Status: Accepted
- Date: 2026-10-21
## Context
Dusty needs private, local Whisper inference without a heavy Python runtime.
## Decision
Use whisper.cpp, pinned to a release tag and commit in M1.
## Consequences
Native binaries must be built, audited, and tested on Windows.
## Alternatives considered
Python Whisper runtime; rejected for deployment weight.
