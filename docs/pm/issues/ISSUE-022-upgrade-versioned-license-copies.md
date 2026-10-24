# ISSUE-022 - Obsolete versioned license copies survive upgrade

- Severity: S1
- Milestone: M5
- Status: Resolved (2026-10-24), true-upgrade and installed inventory passed

## Evidence and root cause

Release v0.5.0-m5.8, CI 40066137913, passed source and packaged gates but failed
the installed inventory after upgrading .4. Two old files remained under
licenses/dusty/dusty-0.5.0.dev4.dist-info/licenses: LICENSE and NOTICE.
Package metadata paths include the version, so Inno's normal overwrite did not
replace these names. The strict installed gate correctly rejected them; it is
unchanged. No draft release or installer upload followed this failed gate.

## Fix

Before file installation, the extracted guarded current app checks obsolete
Dusty metadata-license folders. Only the exact two own-license files, in a
strict versioned namespace, byte-identical to the current bundled LICENSE and
NOTICE, are eligible. All folders are preflighted; linked/protected paths,
unknown entries, changed bytes or unreadable metadata preserve the files and
block upgrade with a plain explanation. Recheck each hash immediately before
unlink; remove only the now-empty two directories. No wildcard or recursive
deletion, no model/data/output removal, no installed inventory exception.

Unit regressions cover matching copies and changed/unknown/linked/protected
content. The original true-upgrade gate must pass before any safe-build claim.

## Resolution evidence

ca6ff44, v0.5.0-m5.9, CI 40067407725: every job passed and a draft-only release
was created. Receipt two_distinct_versions=true; strict installed inventory/PE,
installed WFP, fetch-blocked model/hash/time preservation, both uninstall choices,
normal-cancel partial removal/retry and user-output sentinel preservation pass.
Current Setup/GUI/native counts 0; fetch allowed 4, blocked 0, calibrated.
Full local source: 302 passed/1 expected skip, required coverage 94.2%.
The follow-up .9 to .10 run is a separate safe-build-pair acceptance check.
