# ISSUE-009 - Google Drive streaming roots omitted from sync warnings

- Severity: S2
- Milestone: M3
- Status: Resolved
- Environment: Windows, Google Drive for desktop streaming mount

## Steps to reproduce

Configure a streaming mount at the documented default G: or a custom drive
letter/path, then choose an output folder below that mount.

## Expected

The GUI warns before starting and offers Continue or another folder.

## Actual

The inherited detector only checked profile folders named Google Drive or
My Drive, so it omitted streaming roots outside those folders.

## Root cause

M2 implemented a profile-folder heuristic without verifying the Windows
streaming configuration. Existing unit tests covered those profile folders;
the M3 privacy review against Google's official configuration exposed the gap.
There is no evidence of a Dusty network connection or actual user-data upload.

## Fix / proposed fix

Read only the documented DefaultMountPoint policy/user/host settings. For the
documented default, warn on G: only when local DriveFS data exists. Retain the
existing local roots. Do not add a vendor API, dependency or network lookup.
Document limits for arbitrary mirrored folders and stale configuration.

## Regression test added

Injected registry readers verify precedence, custom paths/letters and default
DriveFS presence without touching real registry keys. Existing GUI sync tests
verify warning acknowledgement and refusal behavior. Final code 7551944: 94 local tests passed; PR CI 39827402358 passed with 93 tests and one unavailable-Vulkan skip. WFP GUI processing passed with zero connections.

## Resolution

Closed in M3 after the verified local configuration fix and regression checks.
No vendor data or registry entries are changed. Advisory detection limits are
documented in docs/dev/sync-detection.md and docs/privacy.md.
