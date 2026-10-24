# 0008 - Installer
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

## Approved uninstall entry, 2026-10-24

Windows Settings > Apps is the official route. Registration must pass
/SILENT /DUSTYCONFIRM=yes so Dusty confirms once and Inno does not confirm again.
Audit all registered uninstall commands and created shortcuts; no supported
entry may launch a bare uninstaller. Protected-installation preflight stays first.
