# Independent audit packet - M6

This packet describes the M6 branch, not an approval to merge or publish. M5
code baseline 062d1f1 and drafts .13/.14 remain frozen for the Owner's VM test.
The only authorized M5 follow-up is docs-only d4ee428 (ThinkPad evidence and
internet-zone test instructions). The
candidate native engine and its unactivated pins must be distinguished from
public engine-v2. Read CURRENT_MILESTONE.md, SPEC and the accepted ADRs first.

## Architecture and trust boundaries

```text
Explicit user consent / Setup model choice
  -> dusty-fetch/dusty-fetch.exe -> HTTPS GitHub asset + checked redirect
  -> local .part -> full size/SHA-256 -> model filename

dusty/dusty.exe (Qt + coordinator, no network)
  -> per-file kill-on-close Job -> FFprobe / FFmpeg -> owned PCM
  -> per-file kill-on-close Job -> whisper-cli CPU or Vulkan -> owned JSON
  -> parse -> standard-library exporters -> atomic chosen output

Bundled resources/models.json is the trust anchor, never remotely refreshed.
Separate onedir interpreters; shared bin/ and resources/. No model weights in
the payload. Settings, resume state, logs, models and work live under local app
data. User outputs are outside managed roots and require an explicit folder.
```

GUI work runs in QThreads. Events contain immutable job snapshots. Networking
is restricted to a separate fetch child, never an import into dusty. Children
start suspended until assigned to a Windows Job. CPU fallback is per file.

## Threat model

Protect against accidental processing connections, sensitive logs/metadata,
unverified models, unintended source/output changes and supply-chain surprises.
Treat corrupt local metadata, static reparse points, interrupted writes, crashes
and ordinary OS I/O failures as real input conditions. Preserve unknown content.

An attacker who controls the Windows account or has administrator access is
outside SPEC 9.1. Handle-relative traversal would strengthen deliberate concurrent
path replacement; current checks are not claimed to resist a same-account
attacker switching reparse points between checks. Account encryption, backup
security and independent cloud sync are outside the app. No secure-wipe claim.
Unsigned checksums detect changed downloads; they do not authenticate a compromised
publisher. The catalog hash protects models relative to the downloaded app.

## Safety-critical paths to inspect

| Boundary | Files and functions |
|---|---|
| First startup defense | src/dusty/__main__.py module entry; packaging/runtime_guard.py; privacy/network_guard.py install_guard, _audit, NetworkBlockedError |
| Networking and TLS | src/dusty_fetch/downloader.py HostPolicy.validate, CheckedRedirect.redirect_request, load_asset, Downloader.download, _transfer, _space, matches, io_error; __main__.py CLI error/cancel handling |
| Model integrity/cache | src/dusty/models/registry.py ModelRegistry._verify, _verify_locked, invalidate, model_path, vad_path; models/catalog.py load_manifest |
| GUI download boundary | src/dusty/app/model_manager.py ModelWorker.run/requestInterruption, ModelManager.download/cancel/done/closeEvent, DownloadDialog; runtime_paths.py resolve_fetch_command |
| Child isolation | src/dusty/platform/win_process.py run_job_process, suspended CreateProcessW/AssignProcessToJobObject, reader threads, cancellation/timeout and handle cleanup |
| Native processing | src/dusty/engine/ffmpeg.py probe_audio/transcode_audio; engine/whisper.py run_whisper/parse_whisper_json; engine/backend.py probe_vulkan |
| Pipeline/cleanup | src/dusty/queue/coordinator.py Coordinator.run_batch/_run_one/_changed, cleanup_orphaned_work |
| Ownership and races | src/dusty/work_area.py canonical, linked, protected_paths, managed_destination, sanitize_output, OwnedWork.record/cleanup, cleanup_owned; platform/work_lease.py acquire/available |
| Temp/output publication | src/dusty/queue/outputs.py output_targets/write_outputs; storage.py atomic_json/save_batch/load_batch/save_settings/load_settings/clear_history |
| Partial age/removal | src/dusty/models/partials.py cleanup_stale_partials; dusty_fetch/downloader.py download_lock/record_partial; installer_support.py cancel_partial |
| Redaction/sync | src/dusty/privacy/logging.py configure_logger/RedactionFilter/RotatingFileHandler; privacy/sync.py sync_roots/is_synced; platform/sync_locations.py |
| Installer probe/tests | src/dusty/installer_support.py probe/model_status/accept_tests/clear_failed_selection/model_size; platform/vulkan_probe.py probe_device; selftest.py run_selftest |
| Upgrade removal | src/dusty/installer_upgrade.py tidy_license_copies; purpose/directory/hash receipt, exact old LICENSE/NOTICE only |
| Uninstall removal | src/dusty/installer_cleanup.py uninstall_allowed/cleanup/_cleanup; installer/dusty.iss.template InitializeUninstall before every native deletion path |
| Native wizard | installer/wizard.iss StartChild/ReleaseChild/ShowAmount/Failure, stage transitions, CleanupActivePartial, FinishStopped, CancelButtonClick/SetupCloseQuery; template PE32 ABI records |
| Uninstall confirmation | installer/wizard.iss CurStepChanged registry command; installer/dusty.iss.template InitializeUninstall; tools/test_uninstall_ui.ps1 registered Settings route, one custom confirmation, no generic prompt |
| Local About/notices | src/dusty/app/window.py show_about/open_notices; app/dialogs.py AboutDialog/NoticesDialog; selectable plain repository text and read-only bundled notice, no external URL launch |
| Installer generation | installer/generate_iss.py generate; unmodified catalog, shared messages, retained license texts and current metadata |
| Bundle/PE boundary | tools/build_bundle.py stage/main; check_bundle.py; check_pe_imports.py; packaging/platform-socket-imports.json; stage_microsoft_runtime.py |
| Licensing/supply chain | tools/check_licenses.py allowed_license/check_bundle/check_microsoft; inventory_bundle.py generate; inventory_installer.py generate; check_installer_licenses.py check/check_inventory/check_retained_sources |
| Release upload | .github/workflows/release.yml validate/gates/draft; ci.yml installer_acceptance/installer_licenses/installer_upload; tools/release_assets.py stage/receipt checks and verify_checksum |

Paths in this table are relative to the repository. The static and dynamic gates
are complementary: no-network imports, absent optional network modules, irreversible
audit hook, exact two platform primitive pins, native PE scan and calibrated WFP.
No single layer is presented as proof that arbitrary unreviewed code is safe.

## Run gates locally

Use the isolated setup in docs/dev/build-from-source.md. Normal source commands:

```powershell
uv sync --locked
uv run python tools/fetch_dev_binaries.py
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python tools/check_docs.py
uv run python tools/measure_coverage.py
uv run python tools/check_no_network.py
uv run python tools/check_no_huggingface.py
uv run python tools/check_licenses.py
uv run pytest tests/unit/test_cleanup_adversarial.py tests/unit/test_work_lease.py -q
uv run pytest tests/integration/test_crash_recovery.py tests/integration/test_m6_hardening.py -q
```

Current public engine-v2 fails the enabled Unicode-profile case (ISSUE-026).
Never remove that test, silently replace binaries or call a selected subset full
acceptance. Candidate-engine evidence must name the exact run/hash and distinguish
its temporary validation checkout from committed production pins.

After building the split payload using the pinned packaging environment:

```powershell
uv run python tools/check_bundle.py dist/Dusty
uv run python tools/check_pe_imports.py dist/Dusty/dusty --native dist/Dusty/bin
uv run python -m tools.inventory_bundle dist/Dusty
uv run python tools/check_licenses.py --bundle dist/Dusty --inventory build/packaging/audit/inventory.json
uv run python tools/smoke_packaged_gui.py dist/Dusty
```

Only on the disposable Windows CI runner, as administrator, after full source
gates (never set GITHUB_ACTIONS locally to bypass these guards):

```powershell
./tests/offline/test_wfp_events.ps1
./tools/test_network_isolation.ps1
./tools/test_model_download_isolation.ps1
./tools/test_network_isolation.ps1 -Bundle dist/Dusty
./tools/test_model_download_isolation.ps1 -Bundle dist/Dusty
./tools/build_installer.ps1
uv run python -m tools.inventory_installer
./tests/offline/test_installer_download_events.ps1
./tools/test_installer.ps1
uv run python tools/check_installer_licenses.py
```

The normal CI job audits installed payload bytes, installed PE imports and WFP,
both uninstall choices, exact legacy protections and model reuse. A real upgrade
additionally passes -PreviousInstaller with a checksum-verified earlier gated
build. Frozen .13/.14 evidence remains in M5-report.md; do not alter those drafts.
The synthetic failing-license job must prove installer upload is skipped.
The real-network unit marker runs only in CI with DUSTY_CI_REAL_NETWORK=1.
All source unit network tests use the local TLS server, not a public model host.

## ADR exceptions and accepted boundaries

- 0012: Dusty's own Apache-2.0 relicense and NOTICE, Owner sole-contributor decision.
- 0014: exact PyInstaller bootloader GPL exception, not general GPL approval.
- 0016: approved model catalog and backend-dependent recommendation; no changes in M6.
- 0017: audit hook supersedes the SPEC monkeypatch design, static exceptions remain zero.
- 0018: minimal VAD timestamp patch on the pinned engine; remove only after verified stable upstream fix.
- 0019: standard-library DOCX; python-docx/lxml are test-only and excluded from runtime.
- 0020: Owner-held Visual Studio Community section 4 redistribution basis, pinned VC redist copies, EULA/protective terms and original PDF provenance.
- 0021: only exact python312.dll/Qt6Core.dll hashes and exact WS2_32 function sets; no broad Winsock allowlist.
- 0022: Setup uses separate dusty-fetch, no Inno network downloader.
- 0023: installer-only Inno/Pascal Script/LZMA/JEDI/Delphi exceptions, retained notices/source and revenue-triggered Owner license requirement.
- 0024: approved UTF-8 native process manifest; successful candidate build is not approval/publication or activated production pins.

## Known gaps for the auditor

Owner manual M5 VM and M6 offline checklists remain evidence gaps. Native page
100%/150% review limitations are explicit in M5-report. Physical Surface testing
belongs to M7. Desktop long-recording evidence is historical, not laptop sign-off.
ISSUE-026 is S1 until activation/full production gates; the Qt 0x8001010d native
producer is not proven by a Python stack or HRESULT name alone. Do not suppress it.
AUDIT-NOTES.md records each disposition, evidence and remaining risk. Unknown
content, crash temporaries and protected destinations may intentionally remain;
never sweep user folders to improve a clean-uninstall result.

ISSUE-028 records a normal/extended Windows namespace comparison bypass, found
with predicates only. M6 canonicalizes protection comparisons without shortening
actual long-path I/O. The frozen M5 code does not have that repair; PM approved no backport and
no M5-only distribution. See M6-report.md for the final native gate result.

## Final M6 candidate evidence

CI 40125892713 at fc2c6e5 passed all source, packaged and installed gates;
M6-report.md records counts, exact installer hash and native candidate provenance.
Registered uninstall receipt: one custom confirmation, zero generic, actual
keep-model checkbox action passed. ISSUE-028 normal/extended protection cases
both passed with synthetic bytes/metadata intact. This is historical baseline evidence; newer M6 runtime and installer changes
require the final run recorded in M6-report.md.
This is explicit candidate mode, not production activation: ISSUE-026 remains
S1 and normal engine-v2 CI still fails. No M5 code or frozen draft was changed.

## PM-approved automatic ISSUE-027 capture

privacy/native_diagnostics.py install_capture runs before Qt imports in the real
processing/GUI entry, after the network guard. Cleanup/probe-only helpers return
before capture setup. Capture observes only 0x8001010d; instruction module+offset,
32 native module/offset frames, numeric thread and enumerated app phase. It never
reads exception parameters, CPU-context data, Python locals or user state.
EXCEPTION_CONTINUE_SEARCH always; faulthandler unchanged. Separate append-only
128 KiB diagnostic file, protected/link/unfamiliar/full storage preserved.
Real RaiseException tests prove original OSError dispatch and no canary data.
Packaged CI labels its injected event ci-fixture; this is not a Qt reproduction.
ISSUE-027 remains open S2 per PM. No network or new dependency.

## ISSUE-029 trust-anchor boundary

Only dusty_fetch/tls.py creates the augmented TLS context. Exact four PEM/DER
hashes are code pins; system roots are retained and no root retrieval occurs.
resources/tls/sources.json gives honest CA provenance and data notices. Hostname,
TLS minimum, allowlist, redirect and model-hash checks remain. CI-only
dusty_fetch/tls_canary.py connects to both approved hosts with ONLY bundled roots
and records full chain fingerprints. Unknown root/chain fails. Narrow
check_licenses.check_trust_data permits only the four pinned public certificate
files, never arbitrary code or a broad software-license exception. No TLS module
is imported by dusty. Review fresh-store unit tests and the final canary receipt.

PM approved no M5 backport/distribution: M5 after VM pass, then immediate M6,
first real-use build M7 from main after M6. .13/.14 notes now state test-only.
ADR 0024 is accepted; engine-v3 stays DRAFT, pins isolated on 299fea3. The official
uninstall route is Settings > Apps; both registered command variants and all
created shortcuts are audited. No bare internal-uninstaller entry is supported.

Native diagnostic ownership: an exclusive header identifies app-generated data;
valid_capture checks the bounded fixed event schema. installer_cleanup includes
only that recognized file in removal; unknown/protected/linked content remains.
Tests explicitly cover all three cases. Cleanup entry never holds a capture
handle open; real installed uninstall remains a mandatory native gate.


## Combined PM follow-up review paths

ISSUE-031: app/window.py choose_output is the only ordinary writer of a new
output_dir. _save_settings excludes cached folder snapshots; _apply_settings
restores only at initial preparation and never over an explicit selection.
restore_batch keeps the visible current choice for unfinished jobs. Safety
sanitization may clear an unsafe legacy destination, preserving protection.
The integrated Owner-sequence regression includes real TLS, forced GUI death,
child Job Object termination, partial resume, tamper repair and Setup helpers.
Exact Owner trigger was not observed; stale restore and startup races are
separately demonstrated code paths.

ISSUE-032: wizard QueryDownloadPlan runs installed offline --installer-status,
including VAD hash verification. ApplyDownloadPlan tracks needed files separately
from selected/self-tested files. Generated consent covers every needed subset;
only missing/damaged bytes contribute to transfer totals, while every selected
model and VAD still verify. A verified file changed after consent fails safely
rather than silently expanding network consent. Native lifecycle must reuse all
installed files with fetch blocked. Recheck mixed installed/missing wording on
the clean VM; generated-string tests alone are not a visual review.

Main handoff: m6-docs-v2 47594ecd has byte-identical code/config/native/resources
with frozen m5-installer dcf7f98; histories are parallel copies with merge-base
20cce6b. M6 additionally contains the docs prework, then commits from 5aae540.
Do not blindly drop those prework docs in an onto rebase. After the Owner merges
M5, preserve the pushed M6 snapshot and compare the complete content before/after
any rebase, especially guides, privacy, CONTRIBUTING, ledger and reports. Resolve
milestone/report conflicts to the latest M6 brief and mirrored M5 VM evidence;
retain unrelated main changes. Re-run all gates on the actual rebased head.
No history rewrite, M5 merge or M6 PR was performed during preparation.


## Verified local rebase rehearsal

An ignored clone build/m6-rebase-rehearsal-932949e replayed 64 commits with
`git rebase --onto dcf7f98 20cce6b`. Git long-path support was enabled in that
clone before checkout; no system setting or real-branch change. Known historical
conflicts (127 events, 31 files) were resolved from the preserved original M6
snapshot, which already includes every frozen M5 source/config change. Result
0160516 has dcf7f98 as an ancestor and exactly the same complete tree as 932949e:
`1b91cecf3ad13e5e086da27572352d2f5d46379b`. Full tree diff exit 0, clean status.
No rehearsal commit was pushed. All original history/branches remain untouched.

After the Owner merges M5, first verify main matches that M5 source baseline,
preserve the newest pushed M6 snapshot and repeat on the actual target. Use the
snapshot for known overlaps, including guides/privacy/CONTRIBUTING and the latest
brief/report; preserve unrelated main changes rather than blindly taking a side.
Compare final content and run all gates on the actual rebased head. Rehearsal
success is evidence of a content-preserving route, not an executed main rebase.
