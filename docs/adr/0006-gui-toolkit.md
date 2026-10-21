# 0006 - GUI toolkit
- Status: Accepted
- Date: 2026-10-21
## Context
Dusty needs a Windows desktop UI usable without Python installation.
## Decision
Use Python 3.12 and PySide6, managed with uv and a committed lockfile.
## Consequences
Qt libraries must remain replaceable for LGPL compliance.
## Alternatives considered
Web UI; would add a browser or server surface.
