# 0008 — Installer
- Status: Accepted
- Date: 2026-10-21
## Context
Nontechnical users need a per-user Windows installer.
## Decision
Use Inno Setup 6 with `PrivilegesRequired=lowest`; unsigned for V1.
## Consequences
M5 must verify downloader APIs and installation failures.
## Alternatives considered
Admin-level installers; unnecessary privileges.
