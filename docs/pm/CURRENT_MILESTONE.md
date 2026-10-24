# Current milestone: M6 - Hardening and documentation

Long autonomous run: the Owner is away from the desktop for several hours and will not answer. Work until done or out of usage. Never wait for the Owner; anything needing the Owner or a PM decision goes under "Owner actions" or "Questions for the PM" in the report, and continue. Commit and push at every checkpoint. No PR, no publishing, no deleting of branches, tags, releases or runs. No em dashes or en dashes anywhere. If the approval system declines a read-only status command, retry it in a simpler form instead of stopping.

Freeze: M5 is pending the Owner's VM test of drafts v0.5.0-m5.13 and v0.5.0-m5.14. Do not change m5-installer or those drafts. If the VM test finds a defect, the PM will send separate instructions.

Setup: create branch m6-hardening from m6-docs-v2 (which has M5 parity plus the docs prework). Save this message's requirements as docs/pm/CURRENT_MILESTONE.md there (archive the M5 brief to docs/pm/briefs/M5-brief.md first). Follow SPEC section 12 M6 plus the requirements below; where they conflict, this brief wins.

1. Documentation (SPEC M6). Finish docs/user (install including SmartScreen, first run, batch how-to, choosing a model, vocabulary hints, troubleshooting, FAQ including the exact SPEC 9.6 approved wording), docs/privacy.md (exactly what is stored where, what touches the network and when, what is never sent), docs/dev (build from source, release process, reproducing model conversion), CONTRIBUTING.md, README. Audience for docs/user: a non-technical person; short sentences, no jargon. Every factual claim must match the final M4/M5 behavior; add a docs consistency check where practical (for example, UI strings quoted in docs must exist in messages.py or the installer message source). Reuse accepted screenshots only from the draft screenshot releases; no new image sources.

2. Audit notes. Go through every item in docs/pm/AUDIT-NOTES.md: fix it with tests, or write down why it is acceptable for V1. Includes ModelRegistry private cache access, handle-relative traversal, a possibly retained .dusty-tmp after a crash, older uninstall after an interrupted upgrade, and the Qt diagnostic 0x8001010d (find the real cause; do not suppress it).

3. Backlog items for V1 only: the graphics test failure progress bar consistency, and any other BACKLOG.md item already marked as V1 polish. No new features, no catalog changes, no new dependencies, no new network paths. The Inno wizard artwork stays in the backlog (needs the Owner).

4. Hardening tests (add to CI where possible): Windows user profile path with spaces and non-ASCII characters (installer, app data, models, outputs); output folder inside a OneDrive-style synced Documents folder (sync warning shown, files written correctly); kill the app mid-batch then resume (SPEC 11.4); cancel mid-file leaves no partial outputs; very long paths and non-ASCII recording names; canary log test still passes on the packaged app; low disk space during transcription and during model download.

5. Owner checklist docs/pm/M6-checklist.md: the SPEC 11.5 manual offline test (install, airplane mode, reboot, transcribe a batch) for the desktop and the ThinkPad, about 20 minutes per machine. The Surface version belongs to M7.

6. Audit packet docs/pm/AUDIT-PACKET.md for the final independent audit: architecture map, threat model, every safety-critical code path with file and function names (network, process isolation, file deletion/move/overwrite, licensing gates, installer/uninstaller), how to run every gate locally, accepted risks and ADR exceptions, and known gaps.

When done, write docs/pm/reports/M6-report.md (acceptance table against SPEC M6, what changed, test and CI results, Owner actions, Questions for the PM) and stop.

## PM supplement, 2026-10-24

Owner real-hardware ThinkPad test (Iris Xe, 150%, draft v0.5.0-m5.14) passed no
UAC, recommended Turbo pre-selection, Vulkan and CPU fallback self-tests, Finish
launch, TXT/DOCX, OneDrive Documents warning, 150% layout and full model-removal
uninstall with transcripts untouched. SmartScreen did not appear because gh did
not add Mark of the Web. This is not fresh-VM or offline reboot acceptance.

Fix on M6, with tests:
1. After successful Setup, keep a valid verified existing model choice. If the
   choice is absent, empty or stale, use the tested default: recommended selected
   model, otherwise first selected. Cover fresh, empty, stale and valid profiles.
2. Keep Privacy and accuracy unchanged. About Dusty shows name/version, one-line
   description, Apache-2.0, selectable repository address and a button opening
   the bundled local third-party notices. All wording stays in messages.py.
3. Remove Inno's redundant generic confirmation after Dusty's own uninstall
   confirmation. Keep the protected-installation stop.
4. Document Zone.Identifier/ZoneId=3 tagging before installer testing, including
   the exact Set-Content command, on m5-installer (docs only) and in release docs.

Continue all remaining M6 work autonomously. Record Owner actions and PM
questions instead of waiting. Do not alter frozen .13/.14 drafts. No PR,
publishing or deletion of branches/tags/releases/runs. Stop with M6-report.md.

## PM report decisions, 2026-10-24

1. ADR 0024 accepted. Prepare exact gated engine-v3 draft with packages, hashes,
   provenance and licenses. Owner publishes prerelease; give exact gh command.
   Prepare m6-engine-v3-pins from M6, never merge before PM publication confirmation.
2. No M5 backport or M5-only distribution. M5 merges after VM pass, M6 immediately
   after, first real-use build from main after M6 (M7). Mark report and .13/.14
   draft notes Not for distribution; draft-only edits, no publishing.
3. ISSUE-027 stays S2/open; automatic passive module/context capture, no user data
   or suppression; document in audit packet.
4. Windows Settings > Apps official uninstall route approved. Audit every shortcut
   and registration, remove or correct bare-uninstaller entries, with tests.
5. ThinkPad installed-app endurance instructions: same >=2h public audio/hash as
   desktop, Turbo Vulkan and Small CPU, time/RTF/peak RAM/work cleanup. Surface M7.

Record decisions in ledger/issues/ADRs. Never wait for Owner; commit and push
checkpoints; no PR/publication/deletion. Update M6-report.md and stop.
