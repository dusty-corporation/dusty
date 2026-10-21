# 0003 — Model source
- Status: Accepted
- Date: 2026-10-21
## Context
Models need authoritative provenance and reproducible conversion.
## Decision
Download official OpenAI `.pt` weights in CI, verify SHA-256, convert with whisper.cpp, and publish GGML assets on a dedicated GitHub Release.
## Consequences
The pipeline must pin source revisions and prove reproducible hashes.
## Alternatives considered
Third-party converted models; provenance and reproducibility are less direct.
