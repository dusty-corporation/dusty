# 0022 - Installer model downloads via dusty-fetch

- Status: Accepted by PM
- Date: 2026-10-23

## Context

SPEC section 12 M5 originally requested Inno Setup's built-in downloader.
The M4 downloader now enforces the exact HTTPS host allowlist, redirect checks,
resumable partial files, disk checks and bundled-manifest hashes.

## Decision

The installer launches the bundled dusty-fetch.exe in its separate onedir
folder. It verifies existing models before deciding whether to download them,
verifies downloaded files again, and runs the offline dusty.exe self-test.
Inno Setup does not perform model HTTP requests. This supersedes the built-in
downloader design in SPEC section 12 M5 task 2 under the PM's explicit decision.

## Consequences

Installation and Model Manager use one trust anchor and transport policy.
Download, verification and self-test failures must prevent a success screen
and permit retry. Models remain outside the application directory on upgrades.
Installer clean-machine acceptance, cancellation and uninstall behavior must
be checked before the M5 release gate; draft compilation alone is insufficient.

## Alternatives considered

Inno's downloader would duplicate security policy. A GUI network client would
violate the offline processing boundary.
