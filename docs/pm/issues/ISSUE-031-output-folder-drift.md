# ISSUE-031 - Output folder changed without an explicit choice

- Severity: S2
- Milestone: M6
- Status: In progress
- Environment: Owner Windows 11 Home 26H2 VM, .13/.14, 2026-10-24

## Owner observation

Documents/Transcripts was kept at the true upgrade, but later became
Downloads/M5-check. Intervening events: Model Manager download/cancel/close,
Task Manager kill/resume, tampered Tiny repair, offline Setup Finish without,
and online Setup. The exact triggering event was not isolated by the Owner.

## Writer audit and demonstrated mechanism

Bulk _apply_settings applied recovered BatchOptions.output_dir as the global
folder. A later model-change/close/start settings save persisted that stale
batch destination. Initial asynchronous preparation could also replace a folder
chosen while startup was still running. Both are code paths, not proof of the
exact VM trigger. Installer clear/pass helpers and graphics probe read current
settings and change only their own keys; they do not assign output_dir.

## Repair

Only choose_output persists a new folder, atomically and independently of other
controls. Ordinary saves preserve the on-disk choice and exclude cached folder
snapshots. Initial preparation restores a folder only when none has been chosen;
recovery never replaces it. Unfinished jobs use the current explicitly chosen
folder, matching the visible Saving to line; completed outputs remain unchanged.
Managed-destination sanitization may still clear an unsafe legacy choice while
preserving its protection metadata; it never substitutes another folder.
