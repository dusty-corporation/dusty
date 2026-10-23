# M5 interim 6 - Installer acceptance, documentation and S0 stop

## Owner actions for the morning

1. **Contain ISSUE-019:** remove only `m5-installer-draft-unsigned`, artifact
   **12488875272**, from [run 39922816919](https://github.com/dusty-corporation/dusty/actions/runs/39922816919/artifacts/12488875272).
   It was uploaded before the full static-license inventory. Deletion is
   Owner-only; the engineer has not attempted it. Do not distribute that installer.
2. Review [ISSUE-018](../issues/ISSUE-018-installer-static-license-inventory.md):
   Pascal Script attribution terms, public-domain code, the old LZMA linking
   exception, JEDI MPL/LGPL terms and Delphi RTL/VCL provenance need narrow
   installer-specific review. ADR 0023 approves only the InnoSetup wrapper.
3. Authorize resumption after the S0 review. Rerun final source/installed-payload
   gates and CI after resolving the static licenses. Latest runs were cancelled
   for containment, not treated as passing. Installer upload remains blocked.
4. After clearance, use [M5-checklist.md](../M5-checklist.md) for the clean,
   standard-user Windows 11 VM checks. No new hardware result is assumed.
5. Review the draft user guides on `m6-docs`. It needs the latest M5 follow-ups
   carried forward after resumption. No PR, merge or published release is requested.

## 1. Summary

Work stopped for a real NN-5 policy violation: the first wrapper-approval
checkpoint caused CI to upload an installer before its separately licensed static
components were inventoried. Later runs correctly block installer upload, but
the earlier artifact remains and requires Owner removal. Before discovery,
silent install, model download, installed self-test/WFP, upgrade and both
uninstall modes passed in CI; documentation and both desktop endurance runs
also completed. M5 and M6 are not accepted or complete.

Branch contents:

- `m5-packaging-spike`: ADR 0023 approval and ISSUE-017 closure, installer-wide
  inventory/SBOM/notices and fail-closed license gate, silent acceptance harness,
  installed-file identity check, endurance harness/provenance and this report.
- `m6-docs`: pushed at a206740 from M5 20998ef; user guides, privacy,
  CONTRIBUTING and README only. No app code authored on this branch.
- `m4-downloader`, `main`: unchanged during this session. No PR opened.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Exact wrapper exception and notices | met | ADR 0023 Accepted by PM; InnoSetup allowed only in explicit installer context; app gate still rejects it |
| Installer-wide inventory/license gate | partial, blocks distribution | Actual app files plus six wrapper/static component records, validated CycloneDX 1.6; five static-license findings and unresolved Delphi provenance |
| Silent per-user install and Tiny/VAD download | met on runner | 39924971496 acceptance summary; explicit terms/download flags, PrivilegesRequired=lowest |
| Installed self-test under calibrated WFP | met on runner | Positive control present, installed processing connection events 0 |
| Upgrade preserving models without download | met on runner | Downloader blocked by firewall; verified hashes and mtimes unchanged |
| Uninstall keep/remove models; outputs untouched | met on runner | Both choices passed; external output sentinel unchanged |
| Installed full-file identity gate | partial | Negative drift/extra-file test passes; added after completed lifecycle run, final CI cancelled for S0 |
| M6 docs prework | draft written | 11 documents checked for links/dash rule; exact SPEC 9.6 HIPAA paragraph asserted |
| Desktop >=2 h packaged processing | met for prework | Small CPU and Turbo Vulkan Done/exit 0, both work trees empty |
| Clean Windows 11 VM/manual acceptance | not met | Owner checklist prepared; elevated CI runner is not a standard-user VM |

## 3. What was built

`tools/inventory_installer.py` extends the actual payload inventory and SBOM with
the wrapper and source-identified static units; full source URLs and hashes are
in `packaging/licenses/inno/components.json`. `check_installer_licenses.py` checks
notices, exact records, compiled image identity and the app inventory. It does
not relabel unknown licenses as InnoSetup. `check_installed_payload.py` inventories
installed files and rejects changed/missing/extra payload files, allowing only
the explicit wrapper notice and generated uninsNNN runtime records.

The installer requires `/ACCEPTTERMS=yes /ALLOWDOWNLOAD=yes` for silent deployment
and explicit `/REMOVEMODELS=yes|no` for silent uninstall. `/SUPPRESSMSGBOXES`
alone never grants consent. The pinned Inno source documents silent event
behavior; post-install silent failure cannot report success. The lifecycle test
reads the registered per-user uninstall command and validates its directory.
The first harness assumed unins000.exe; verified CI later used unins000 then
unins001 after reinstall. No Owner desktop installation was performed.

M6 guides cover install/hash/SmartScreen, first run, folders, plain model choices,
vocabulary hints, troubleshooting, FAQ and exact HIPAA wording. Privacy now
describes local settings, paths/hints in unfinished state, corrupt backups,
temporary audio/JSON, models/partials, redacted logs, separate downloads and
deletion limits. No sensitive user recording was used.

## 4. Test results

- Local full source suite at installer inventory checkpoint: **190 passed,
  1 CI-only skip in 227.92 s**, strict coverage **94.5%** (core 93.7%, export
  98.6%, models 95.2%, queue 93.0%, privacy 96.2%). Log:
  `build/m5-overnight-source-tests.log`. Ruff, format (119 files), mypy
  (67 sources) and all three source policy checks passed.
- [39924971496](https://github.com/dusty-corporation/dusty/actions/runs/39924971496)
  at 126aedb: **189 passed, 2 expected skips in 283.87 s**; separate public Tiny
  integration 1 passed. Checks and offline jobs pass. Packaging compiles and
  completes lifecycle acceptance, then fails only the intended installer license
  gate. Installer binary upload is skipped. Audit: m5-installer-draft-audit.
- That app payload: **213 files, 161951722 bytes**. All **64 processing PEs**
  pass the exact platform gate; app license gate and packaged GUI smoke pass.
- WFP source processing: **0**; source download: GUI **0**, fetch allowed **4**,
  blocked **0**. Packaged self-test **0**; packaged download: GUI **0**, fetch
  allowed **4**, blocked **0**. Installed self-test **0**, calibrated control true.
- New installed-payload and static-inventory negative tests: **2 passed**;
  ruff and mypy (68 sources) pass. Final whole-suite rerun was stopped for S0;
  no final-head full-suite/green-CI claim is made.
- Requested cancellation of runs 39925428852 and 39925218957. Attempt to cancel
  39924971496 returned `Cannot cancel a workflow run that is completed`.
  Its completed evidence is retained. No runs/artifacts were deleted by the agent.

Incident installer: 34591385 bytes, SHA-256
`f70f1ede9923d605f3ec1b3d072a1f4ed7c9e3d4da3c7fb2111fb05af64ec14d`.
Later gated installer in 39924971496: 34590744 bytes, SHA-256
`e599c6aa507fe53ab4b7a0409ee6cd88f42c1212386c8b67dde69bf2bf97e74e`.
Only the former has the unapproved installer artifact identified above.

### Desktop endurance

Full method and limits: [desktop-long-recording.md](../benchmarks/m6/desktop-long-recording.md).
Repeated public-domain LibriVox input: **7920.1875 s**, eight threads, VAD on,
automatic language, Text export through the existing frozen shared coordinator.

| Model / actual backend | Wall seconds | RTF | Sampled tree RAM bytes | Work bytes peak | After |
|---|---:|---:|---:|---:|---|
| Small / CPU | 1060.9096 | 0.133950 | 2612928512 | 253446078 | Done, exit 0, work empty |
| Turbo q8_0 / Vulkan | 268.3786 | 0.033885 | 2119102464 | 264681781 | Done, exit 0, work empty |

Desktop: Ryzen 7 5800X3D, about 32 GiB RAM, RTX 3080 Ti. Sampled RAM is process
working set, not VRAM or an exact instantaneous maximum. Raw JSON/audio/outputs
stay ignored in build/m6-long-recording; no raw asset upload after the S0 stop.

Repository dash search before incident-doc commit:
`git grep -n -I -e "$([char]0x2014)" -e "$([char]0x2013)" -- .`
Output: none. Exit: 1 (no matches). New incident/report documents were also
checked as text before committing. SPEC and the Owner brief were not edited.

## 5. Deviations from SPEC

Explicit PM authorization permits M5 installer and M6 docs/endurance prework while
the stored brief still names M4. ADR 0022 uses bundled dusty-fetch rather than
Inno HTTP; ADR 0023 permits exactly the wrapper's InnoSetup license. M6 endurance
was run on this desktop as requested; it does not replace laptop/hardware gates.
Source-level installer static attribution is documented, not presented as binary
symbol proof. No extra static-license exception was invented.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-017 | S1 | Resolved by PM | Exact wrapper approval, retained notice, Owner purchase commitment if revenue threshold exceeded |
| ISSUE-018 | S1 | Open | Separate installer-static licenses/provenance require review |
| ISSUE-019 | S0 | Open, work stopped | Wrapper gate enabled upload before complete inventory |

## 7. Decisions needed

PM review of ISSUE-018 and the ISSUE-019 incident is required before resumption.
Do not broaden the app allowlist or treat CI-only distribution as exempt.

## 8. Owner actions

Use the morning list at the top. After clearance, the six-step clean Windows 11
checklist covers hash/SmartScreen/no UAC, full terms, model/default/shortcuts,
offline reboot/transcription, interruption/failure/retry, upgrade and uninstall.
Send pass/fail and plain errors, not confidential content.

## 9. Risks

The earlier artifact remains until Owner removal. Full final-head CI and the new
installed-payload gate still need verification after resumption. M6 is draft
documentation, not completed hardening. The real Surface Vulkan smoke remains
a required pre-M7 check. The Persian reference fixture remains Owner-verified:
https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3
interval **[107, 122) s**, exactly **00:01:47.000 to 00:02:02.000** in the original
recording, confirmed by listening as a complete Farsi quatrain on 2026-10-22.

## 10. Effort notes

The installer license boundary was broader than the wrapper identifier. Applying
its approval before completing the inventory was my sequencing error. The later
gate catches the additional terms, but does not undo the earlier upload. Work is
stopped under AGENTS rule 2; the incident-report commit suppresses automatic CI
only to preserve that stop, with no passing test result asserted.
