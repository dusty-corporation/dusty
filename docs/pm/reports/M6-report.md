# M6 Report - Hardening and documentation

## 1. Summary

The requested M6 code, documentation and PM follow-ups are implemented on
m6-hardening; final validation is recorded below. Production engine pins still
select engine-v2, so M6 is not ready for acceptance or distribution until the
Owner publishes engine-v3, the PM confirms activation, and normal CI passes.
Engine-v3 is a verified draft, its pin switch is isolated, and M5 draft PR #6
is open without changing the frozen M5 code or installer assets. Physical
checklists and laptop endurance remain Owner actions; ISSUE-027 stays open S2
with passive capture as approved by the PM.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| User/privacy/developer/contributing documentation | met | docs/user, docs/privacy.md, docs/dev, CONTRIBUTING, README, exact SPEC 9.6 FAQ wording and docs consistency tests. Accepted screenshot sources only. |
| Every audit note fixed or given a V1 disposition | met with PM exception | AUDIT-NOTES.md; public registry API, path/ownership/work leases and disk handling tests. ISSUE-027 explicitly remains open S2 with automatic capture. |
| V1 polish | met | Graphics-failure bar matches bytes; no artwork, catalog, dependencies or speculative features added. |
| Adverse automated paths | met for candidate | Unicode/sync paths, long filenames, forced death/resume, cancel without partial outputs, disk exhaustion, canary logging and protected cleanup remain enabled. |
| Packaged/installed privacy, PE, licenses and uninstall | met for candidate | Calibrated WFP, pinned PE imports, installer-wide notices/SBOM, both uninstall choices and output sentinels. |
| Actual Windows account with spaces/non-ASCII | partial | Synthetic profile/model/output paths plus real Unicode install directory covered; actual account checklist pending. |
| Manual offline/reboot on desktop and ThinkPad | partial | M5 VM offline CPU pass is recorded; M6-checklist.md requires separate real-device M6 sign-offs. Surface belongs to M7. |
| At least 2 h laptop endurance | partial | Desktop prework complete; exact installed ThinkPad instructions and matching input hash prepared, no laptop result invented. |
| Zero open S0/S1 | not met | ISSUE-026 needs published/activated engine-v3 and normal production-pin CI. No current S0. ISSUE-029 implementation/evidence below. |
| Independent audit packet | met | AUDIT-PACKET.md architecture, threat model, named mutation/network/process/license paths, commands, accepted exceptions and limits. |

## 3. What was built

- Safety: serialized public registry invalidation; work leases; conservative owned
  cleanup; rooted/traversal/extended-path protection; disk-full handling; truthful
  partial-removal failures; no sweeps in user output folders.
- Successful Setup preserves a valid selected verified model, otherwise selects
  the tested recommended/first model. Failed tests never become successful and
  never silently remove existing models. About is separate from privacy and opens
  bundled local notices. Settings > Apps invokes one custom uninstall confirmation.
- ISSUE-027: privacy/native_diagnostics.py observes only 0x8001010d before Qt.
  Module basenames/offsets, bounded native frames, numeric thread and enumerated
  phase only; no exception parameters, paths, prompts or transcripts. Every
  callback continues normal dispatch; faulthandler remains unchanged. A bounded
  owned-header log is removed only when its exact schema is recognized.
- ISSUE-029: dusty_fetch/tls.py adds four hash/fingerprint-pinned CA roots to the
  Windows system roots, shared by Setup and Model Manager. Hostnames, TLS 1.2
  minimum, two-host redirects, size/SHA-256 and cancellation rules are unchanged.
  No new dependency or Microsoft automatic root retrieval. Live-chain canary
  uses bundled roots alone. Full catalog rows are initialized before the deferred
  bounded graphics check; Next stays disabled while Checking this computer...
- ISSUE-031: Choose folder is the only ordinary new-folder writer. Recovery and
  late preparation cannot replace it; ordinary settings saves preserve the disk
  choice. The integrated real TLS/GUI test replays download, cancel/close,
  forced death/partial resume, tamper/repair and failed/successful Setup helpers.
  Stale recovery/startup mechanisms are proven; the exact Owner trigger is not.
- ISSUE-032: Setup hashes installed models and Voice detection before consent.
  Only needed files appear in download names/byte totals; all selected files
  still verify and test. Lists use A, B and C. All-installed says already
  downloaded / Check and test, without a misleading transfer amount.

## 4. Test results

Final code **932949e**, validated by
[CI 40134555055](https://github.com/dusty-corporation/dusty/actions/runs/40134555055),
all four jobs successful. Later changes are documentation/ledger/changelog only.
This explicitly stages the exact approved native candidate in a disposable CI
checkout; committed production pins remain engine-v2.

| Gate | Result |
|---|---|
| Full source suite | 423 passed, 2 expected skips, 375.92 s; separate explicit Tiny integration 1 passed, 1.63 s. Skips: opt-in public network case and absent physical Vulkan GPU. |
| Strict coverage | 1192/1246 = 95.7%; core 93.7%, export 98.6%, models 97.4%, queue 94.7%, privacy 95.6%; all exceed 85%. |
| Static/docs/policy | Ruff, format (159 files), mypy (86 sources), docs and three policy checks pass. |
| Live bundled-only CA canary | Both hosts' default chains pass. GitHub RSA/ECC pass; release-assets RSA passes, optional TLS 1.2 ECC not served. Certificate failures are never ignored. |
| Source / packaged Model Manager WFP | Each GUI 0; fetch allowed 4, blocked 0; verification and blocked-event calibration pass. |
| Packaged / installed processing WFP | Each connection_events=0; self-test, model-free probe, sensitive-log canary and native_diagnostic_capture pass. No real GPU on runner. |
| Setup full transfer WFP | Installer 0, GUI 0, native 0; fetch allowed 4, blocked 0; model-free probe and calibration pass. |
| Setup cancellation WFP | Installer/GUI/native 0; fetch allowed 2, blocked 0; normal partial removal and subsequent retry pass. |
| PE / licenses / installed inventory | 64 PE files at each stage, zero findings; narrow exact platform pins; bundle and installer-wide license/SBOM/notices gates pass; 227 installed files match. |
| Reuse and cleanup | Fetch blocked during reinstall; models' hashes/mtimes preserved. Both uninstall choices, protected normal/extended/legacy destinations, and output sentinels pass. |
| Actual uninstall entries/UI | UninstallString and QuietUninstallString use approved arguments; exactly 2 app shortcuts, 0 bare uninstall entries; custom confirmation 1, generic 0; actual keep-models checkbox action passes. |
| Upload regression | Deliberately failing synthetic license gate prevents upload. Final installer uploads only after actual acceptance/license gates pass. |

This M6 lifecycle has two_distinct_versions=false: same-version reinstall, not
another true upgrade pair. Frozen M5 CI and the Owner separately passed .13 to .14.
Bundle: 222 files, 162,050,002 bytes; no models. Gated unsigned installer:
Dusty-0.0.1-draft-unsigned.exe, **34,714,668 bytes**, independently downloaded and
verified against SHA256SUMS:
`219e90a9fc6f3db86773bd830d4f134965c22fabf46cbca787a04e65f05def4f`.
Artifacts: m5-installer-draft-unsigned, m5-installer-draft-audit,
packaging-spike-audit, m4-download-audit, m4-review-bundle and gated
m5-installer-page-review. These are CI artifacts, not newly published releases.


Focused local checks: 34 installer generation/support tests passed in 2.52 s;
39 Model Manager tests passed in 52.50 s with approved loopback access, including
real forced GUI termination, child death, stopped partial growth and the complete
folder-preservation sequence. Ruff, formatting, mypy, docs and all three policy
checks pass. The first restricted local full run was interrupted after test
failures; it is not a passing result. The escalated local full suite finished with 420 passed, one skipped and the
one unchanged production engine-v2 Unicode failure (214.36 s, ISSUE-026).

Historical baseline 40125892713 passed all candidate gates before these follow-ups;
40131277479 passed source/offline and packaged privacy/PE/license gates but failed
first silent install. Visible-page probe deferral also blocked unattended wizard
navigation; silent Setup now retains its explicit selection and the production
probe is separately exercised by calibrated WFP. CI-only Inno logs were added.
40132812499 then passed full source/live roots, packaged gates, initial Setup
WFP (0 processing events, fetch 4 allowed/0 blocked), blocked-fetch reuse and
227-file installed inventory, but the new WScript shortcut reader returned zero
Unicode targets. Repository-local reproduction and real Unicode IShellLinkW
fixtures fixed the CI reader; required shortcut count and bare-route rejection
remain enforced. The byte meter also excludes initial damaged-file verification.
No gate, regression, faulthandler output or license policy was weakened.
`git grep -n -I -P '[\x{2013}\x{2014}]' -- .` produced no output, exit 1.
Frozen M5 source/config/native diff against 062d1f1 is empty, exit 0.

Desktop prework, 2026-10-23 (not a final installed-build or laptop result):

| Model/backend | Audio s | Wall s | RTF | Sampled tree RAM B | Peak work B | Exit / work left |
|---|---:|---:|---:|---:|---:|---|
| Small CPU | 7920.1875 | 1060.9096 | 0.133950 | 2612928512 | 253446078 | 0 / empty |
| Turbo q8_0 Vulkan | 7920.1875 | 268.3786 | 0.033885 | 2119102464 | 264681781 | 0 / empty |

Details and sampling limits: benchmarks/m6/desktop-long-recording.md. PowerShell
preparation independently reproduced the exact input hash
8455996fe6970d43828600d976712ab4b37c40b22863d4fa0031f4bc47921de3.
No long audio, transcripts or raw benchmark JSON are committed.

## 5. Approved decisions and deviations

- ADR 0024 accepted: link-time UTF-8/long-path manifest on the same pinned engine,
  not a system locale change or runtime binary modification. Native run
  40110881732 at d0abc304942255a1d30d741fff0ca98c2c1cdf45 built both packages
  with GGML_NATIVE=OFF and CPU variants. Exact gated packages prepared as engine-v3.
- [engine-v3 draft](https://github.com/dusty-corporation/dusty/releases/tag/untagged-6e484bbe817284177f7f):
  both packages, unchanged minimal FFmpeg, licenses, patch, manifest, CMake caches,
  build provenance, FFmpeg configuration and SHA256SUMS; 12 assets independently
  downloaded and verified. CPU SHA b47ec54df7ecb09b341bb7abc5f0f461f746f4bfe72b4873d5843340b9cef910;
  Vulkan SHA 0e8f26c55c4abd7b708af1106027c2d75ed2d4592f103e10263f08e0c8d523c7.
  Exact candidate archives retain the build-tool bench executable; installed
  payload still excludes it. engine-v2 is unchanged.
- m6-engine-v3-pins 299fea3, based on 9535199, changes only production native pins.
  It is pushed and unmerged. Current M6 remains engine-v2; candidate success is
  not normal production-pin CI success.
- PM approved no M5 backport/distribution: M5 merges first, M6 immediately after;
  first real-use build is M7 from main after M6. M5-report and .13/.14 draft notes
  say Not for distribution. Frozen code/assets were not changed.
- Windows Settings > Apps is the approved uninstall route; all registered
  variants and shortcuts are audited. No bare uninstaller shortcut is supported.
- ThinkPad substitutes for unavailable Surface endurance; Surface remains M7.
  Audit risks/dispositions and installer/runtime license exceptions remain
  explicit in AUDIT-PACKET.md and ADRs 0014, 0017, 0019-0024.
- Certificate provenance is exact: USERTrust ECC/RSA bytes came from pre-existing
  trusted Windows entries with official CA reference URLs, not a claimed download
  from those URLs. ISRG X1/X2 came from official verified HTTPS. Approval review
  rejected HTTP/crt.sh retrievals and neither ran; safer local-store/HTTPS
  acquisition completed. See docs/dev/tls-roots.md and resources/tls/sources.json.

## 6. Issues

| Issue | Severity | Status | Evidence |
|---|---|---|---|
| ISSUE-026 | S1 | Activation pending | Unicode regression stays enabled; exact candidate passes, production engine-v2 does not. |
| ISSUE-027 | S2 | Open, PM approved | Passive automatic capture is tested; historical native Qt producer remains unknown. Synthetic fixture is not a real recurrence. |
| ISSUE-028 | S0 boundary finding | Resolved on M6 | Ordinary/extended path protections and native refusal tests; no Owner data touched. No M5 backport per PM. |
| ISSUE-029 | S1 | Resolved on M6; VM recheck pending | System-plus-pinned roots, absent-root success/untrusted rejection/integrity and live chains; cold-snapshot Owner recheck pending. |
| ISSUE-031 | S2 | Resolved on M6 | Explicit-only folder persistence and integrated real recovery/model/Setup regression. |
| ISSUE-032 | S2 | Resolved on M6; visual recheck pending | Needed-only consent/progress; all 63 subsets and VAD hash-state tests; native reuse gate and mixed-state VM recheck. |

## 7. Questions for the PM

No unanswered implementation decision remains. Confirm engine-v3 publication
before integrating the prepared pins, then review normal CI and the remaining
Owner evidence for acceptance. ISSUE-027 remains open S2 as already directed;
no guessed root cause or request to suppress it.

## 8. Owner actions

1. Publish the already verified engine-v3 DRAFT as a prerelease, not latest:

   ```powershell
   gh release edit engine-v3 --repo dusty-corporation/dusty --draft=false --prerelease --latest=false
   ```

   Send PM publication confirmation. Only then integrate m6-engine-v3-pins and
   rerun every normal gate; no engineer publication or premature pin merge occurred.
2. Review [DRAFT PR #6](https://github.com/dusty-corporation/dusty/pull/6),
   M5_installer_and_release_pipeline. It remains draft/unmerged. M5 VM evidence
   now includes SmartScreen, no UAC, three license views, CPU recommendation,
   offline reboot TXT/DOCX, true .13 to .14 preservation, cancel/kill/resume,
   tamper repair and failure/retry/Finish without. Cold-store download required
   the disclosed workaround. Manual keep-models was not exercised, not a defect.
   Follow the PM's M5-then-M6 merge plan; do not distribute M5-only builds.
3. Use M6-checklist.md's clean-snapshot recheck: cold-store download with no IWR
   warmup, full probing list/disabled Next, only-needed names/bytes and Check and
   test, explicit folder preservation across the reported sequence, model handoff,
   and actually UNCHECKED keep-models uninstall with exactly one confirmation.
   Test-only candidate retrieval on the host (then use the existing read-only
   VM share protocol; do not put GitHub credentials into the guest):

   ```powershell
   gh run download 40134555055 --repo dusty-corporation/dusty --name m5-installer-draft-unsigned --dir build/m6-review-40134555055
   $setup = @(Get-ChildItem build/m6-review-40134555055 -Recurse -Filter Dusty-0.0.1-draft-unsigned.exe)
   if ($setup.Count -ne 1) { throw 'Expected one candidate installer' }
   if ((Get-FileHash -LiteralPath $setup[0].FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne '219e90a9fc6f3db86773bd830d4f134965c22fabf46cbca787a04e65f05def4f') { throw 'Installer hash mismatch' }
   ```
4. Complete desktop and ThinkPad M6 offline/reboot checklists (about 20 minutes
   each), actual account path coverage, then the separate installed ThinkPad
   Turbo Vulkan and Small CPU endurance runs. Exact fetch/rebuild/hash and
   measurement commands are in M6-checklist.md; Surface belongs to M7. Return
   build/hash, numbered outcomes and redacted measurements, never private data.

## 9. Rebase preparation and remaining risks

M6 prework base 47594ecd has byte-identical source/config/native/resources to
frozen m5-installer dcf7f98. Histories are parallel with merge-base 20cce6b, so a
blind onto rebase dropping all prework would lose the guides/CONTRIBUTING/privacy
base. M5 report/checklist are aligned on both branches; M6's brief, ledger and
guides must be retained. After the Owner merges M5, preserve the pushed M6
snapshot, resolve history/documentation conflicts against it, compare final
source content, and rerun all gates on the actual rebased head. A non-mutating merge-tree preview exposed historical conflicts. A subsequent
ignored-clone rehearsal replayed 64 commits onto frozen M5 dcf7f98, resolving
127 conflict events/31 files from the preserved M6 snapshot. Rehearsal 0160516
has M5 as an ancestor and the exact complete tree of original 932949e:
1b91cecf3ad13e5e086da27572352d2f5d46379b; full diff exit 0 and clean status.
This verifies a content-preserving route. No real branch rebase, force push or
M5 merge occurred; repeat against actual main and the newest M6 snapshot only
after the Owner merges M5, then require full gates again.

Candidate native gates are not publication, actual fresh-account evidence,
physical GPU/endurance acceptance or final independent audit. Same-version M6
reinstall evidence must not be presented as another true two-version upgrade;
the Owner and frozen M5 CI separately tested .13 to .14. Conservative unknown
file retention and same-user mutation limits remain documented audit risks.

## 10. Effort notes

Windows native argument encoding, owned cleanup and native wizard transitions
required real cross-process tests. The cold-root failure exposed a gap masked
by developer trust stores, and folder recovery exposed stale settings snapshots.
Work stays within M6; no later milestone, M6 PR, publication or branch/tag/run
removal was started. This report is the handoff and work stops here.
