# 0010 — Manifest trust anchor
- Status: Accepted
- Date: 2026-10-21
## Context
Model integrity must be checked before use.
## Decision
Bundle `models.json` in each app release and accept model files only when their SHA-256 matches it. Never fetch a remote manifest.
## Consequences
New model catalogs require an app release.
## Alternatives considered
Remote manifests; add a mutable trust source.
