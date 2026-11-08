# 0030 - Incremental portable runtime foundation

- Status: Accepted by PM within Owner-authorized Mac port scope.
- Date: 2026-10-30

## Decision

Add explicit platform selection to runtime location/executable resolution while
preserving current Windows defaults on Windows and testable Windows fixtures.
Mac frozen app layout: Dusty.app/Contents/MacOS/Dusty, resources and native bin
under Contents/Resources; downloader has a separate runtime under
Contents/Helpers/dusty-fetch/dusty-fetch. User models/state/work remain outside
signed contents in ~/Library/Application Support/Dusty by default. Explicit
LOCALAPPDATA remains an isolation override for existing tests/dev probes; it is
not advertised as the native Mac user-data location. Frozen layouts ignore
DUSTY_BIN_DIR/DUSTY_MODELS_DIR, preserving installed trust boundaries.

Use platform-dispatched CPU topology and sleep implementations. Windows API
initialization happens only when Windows functionality is called. Darwin uses
system sysctlbyname and IOKit/CoreFoundation APIs, not shell/caffeinate/network
calls or a new Python dependency. System APIs are not redistributed proprietary
components; actual bundled native libraries still need inventory/license review.

Make engine package exports lazy so the pure progress parser can be imported
without eagerly loading Windows process control. Preserve names and actual
Windows engine behavior. Extend the parser with exact observed Metal selection
and conservative error/device recognition. Do not change selectable backend,
persisted backend schema or runner implementation in this foundational step.

## Constraints and remaining work

Existing owned-file cleanup, guard and no-network boundaries remain unchanged.
Do not substitute generic subprocess calls for the trusted process launcher.
Single-instance/launch supervision, actual engine selection, platform-specific
crash policy, GPU signatures and production bundle lifecycle remain later tasks.
Ctypes/system API calls need checked signatures, ownership and safe failures.
Tests must exercise behavior and failure cleanup, not merely successful imports.

The worker implementation is reviewed before integration; this ADR defines the
bounded contract, not evidence that it already passes. No signing credential,
new shipped helper, package dependency or release automation is approved here.
