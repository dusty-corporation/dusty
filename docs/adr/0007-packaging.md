# 0007 - Packaging
- Status: Accepted
- Date: 2026-10-21
## Context
The installer needs a self-contained desktop app with replaceable Qt libraries.
## Decision
Use PyInstaller in `--onedir` mode.
## Consequences
Packaging must exclude networking modules and preserve shared libraries.
## Alternatives considered
`--onefile`; temp extraction and library replacement are problematic.
