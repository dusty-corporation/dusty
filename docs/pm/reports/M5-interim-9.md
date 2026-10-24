# M5 interim 9 - ISSUE-020 ownership repair

## Summary

The PM approved the repair on 2026-10-23. The implementation preserves legacy
transcript destinations and replaces name-based recursive work cleanup with
unique owned folders and exact content inventories. ISSUE-020 is resolved: final CI 40061186069 on 1b62946 passed all
source, packaged, installed WFP and uninstall gates. Installer page
polish has not started. No real Owner app-data files were inspected or changed.

## Root cause and repair

Startup, probe, self-test and job cleanup trusted a folder name as proof of
ownership, then called rmtree. Output selection allowed those same folders.
Tests checked removal of temporary files, but did not place a chosen transcript
destination in the managed subtree. The original three failing regressions remain
enabled and now pass in focused runs.

- Every Python work invocation creates a random directory exclusively and writes
  a purpose/name/schema marker. Only explicitly named operation outputs enter
  its SHA-256 inventory. Cleanup checks the complete flat inventory before any
  removal. Missing, unreadable or mismatched markers, changed/unknown entries,
  protected paths and reparse ancestors preserve the whole directory. No runtime
  rmtree remains. Skips log only work_cleanup=preserved.
- Saved settings/queue/source/output references protect cleanup. Malformed or
  unreadable protection metadata blocks it. Legacy internal output folders remain
  untouched; their selection is cleared with persistent preserved_paths and a
  one-time shared message. Log initialization also preserves protected log folders.
- GUI selection, scanned inputs and the shared coordinator reject recording
  sources and transcript destinations within managed areas, including resolved
  aliases, save-next-to-recording and restored jobs. Frozen RuntimePaths carries
  the actual install root; development build siblings remain usable test outputs.
- Normal installer partial cancellation uses the guarded app helper. Downloader
  and Model Manager reject reparse ancestors. Automatic stale-partial cleanup
  requires an exact downloader hash receipt in the existing .lock file. Unknown
  or changed prefixes are preserved. Recent prefixes still resume and the entire
  final model must pass size and SHA-256 verification. A forced crash before a
  receipt is written can leave an unproven old prefix; preserving it follows the
  new PM ownership rule rather than deleting it based on its name alone.
- Damaged upgrade models are verified by the extracted existing payload and
  described as Needs download again, without deleting the file at selection time.

## Tests and gates

- Focused ownership/probe suite: 51 passed before the final sweep additions.
- Focused ownership/privacy/uninstall suite: 33 passed.
- Source suite before final sweep additions: 282 passed, 1 expected skip, 168.39 s.
- Ruff, formatting, mypy (76 sources), and the three source policy checks passed
  at the first repair checkpoint. Final-head coverage and CI evidence pending.
- Junction and symlink regressions both run on Windows; neither is skipped.
  External synthetic sentinels survive both direct and nested cleanup attempts.
- CI 40059180686 exposed a development-boundary regression: offline process
  exit_code=1 because build/offline-*/outputs was rejected. b5e57e7 separates the
  frozen install root from development staging; no WFP violation was reported.
- Full packaged/installed gates and the synchronized m6-docs-v2 checkpoint remain
  required before Part 2. Historical green runs do not establish repair acceptance.

## Delete-call sweep

Command: rg -n '(rmtree|\.unlink\(|\.rmdir\(|DeleteFile|DelTree|Remove-Item)' src installer tools

| Call sites | Safety basis |
|---|---|
| src/dusty/work_area.py: entry.unlink, marker.unlink, directory.rmdir | Exact purpose/name marker and full SHA-256 inventory, no unknown entries or links, saved-path protection, flat removal only. |
| src/dusty/installer_cleanup.py: path.unlink, path.rmdir | Schema-checked metadata, protection/reparse checks before deletion; known settings/log/catalog files only. Work delegates to owned cleanup. Unmarked work folders remain, even empty. Other directories disappear only when empty. |
| src/dusty/models/partials.py: path.unlink | Age over seven days plus matching downloader receipt/hash; regular direct file, no linked ancestors or protected subtree. Unknown/changed prefixes stay. |
| src/dusty/app/model_manager.py: part.unlink | Only the active manifest partial, after the downloader child exits on explicit normal cancellation, with reparse checks. |
| src/dusty/app/model_manager.py: path.unlink | Explicit user-confirmed deletion of the selected manifest model; linked model folders/files rejected. |
| src/dusty/installer_support.py: part.unlink | Normal installer cancellation of the current catalog model only; protection metadata and all reparse ancestors checked. |
| src/dusty/installer_upgrade.py: file.unlink, texts.rmdir, texts.parent.rmdir | Upgrade-only obsolete own-license copies. Strict versioned namespace, exact LICENSE/NOTICE inventory, hashes match current bundled texts, protected/reparse checks, preflight all folders and recheck before unlink; empty directories only. Unknown/changed content blocks upgrade and is preserved. |
| src/dusty/queue/outputs.py: temporary.unlink (two sites) | Exclusive random output temporary created by this invocation, never a deterministic pre-existing filename; linked output parent rejected. |
| src/dusty/queue/outputs.py: target.unlink | Rollback only for outputs newly published by this operation, never overwrite mode; compare rendered-content hash and reject links before removal. |
| src/dusty/queue/storage.py: temporary.unlink | Exclusive random atomic-write temporary; linked state paths rejected before writing. |
| src/dusty/queue/storage.py: clear_history unlink | Explicit discard/clear of Dusty's queue metadata, with reparse guard. |
| src/dusty_fetch/downloader.py: part.unlink (five sites) | Current manifest transfer only: size overflow, hash mismatch or explicit cancellation; process holds the download lock, parent/file reparse points rejected. Final rename occurs only after full size/hash validation. |
| installer/wizard.iss: DeleteFile(test-result.txt) | Result written by the prior test child in Inno's private per-invocation temporary folder; no user-selected directory. Partial DeleteFile removed in favor of guarded helper. |
| tools/fetch_dev_binaries.py: temporary.unlink | Exclusive random temporary owned by the current verified development fetch. |
| tools/stage_microsoft_runtime.py: target.unlink | Build-only removal of an unreferenced collected CRT before provenance inventory; generated bundle, not app data or output. |
| tools/bench/model-free-probe.ps1: Remove-Item (entry, marker, directory) | Unique purpose-marked script-local folder; validate resolved parent, all ancestors and complete known entry set; hash known outputs, no recursive removal, unknown/reparse data preserved. |
| tools/build_bundle.py | Prior rmtree removed. Existing bundle destination is refused; CI uses a fresh checkout. |
| tools/test_appdata_guard.py | Contains rmtree/rmdir audit event names only; these install a denial guard and do not delete. |

Inno's own compiled file/uninstall inventory owns its extraction and installed
payload files. It removes registered app files, not arbitrary transcript trees.
Only Dusty's conservative data helper handles persistent user-data cleanup.

## Owner actions for the morning

AMD SVM is now enabled, as reported by the Owner. Keep historical M5 drafts
unpublished. Use the final repaired build identified in M5-report.md for VM testing
once its gates pass; do not use an older affected draft for ordinary transcription.
No PM decision is pending for the approved repair. Final evidence follows here.

## Final repair acceptance (2026-10-24)

CI https://github.com/dusty-corporation/dusty/actions/runs/40061186069 is green
on 1b62946. Source: 293 passed, 2 expected skips, 286.55 s; separate CI-only
network test: 1 passed. Required coverage 94.2% (all packages above 85%).
Packaged layout/PE/license/GUI/WFP, installer-wide license, installed payload/PE/
WFP, model-preserving same-version upgrade, both uninstall choices and output
sentinel preservation passed. Calibrated Setup 0, GUI/probe 0, native 0, fetch
allowed 4, blocked 0. two_distinct_versions=false is honestly retained; Part 3
must establish the separate true-upgrade requirement.

Final marker continuity checks prevent bookkeeping from recreating lost markers
or adopting changes to previously recorded files. The full repair is on
m6-docs-v2 8c199b0, with implementation parity checked and updated user/privacy
guides. Part 2 may now proceed. Previous pending-status notes above are historical.
