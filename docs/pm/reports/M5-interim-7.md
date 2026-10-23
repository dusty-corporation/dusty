# M5 interim 7 - License resolution and gated installer acceptance

## Owner actions

1. Run the clean, standard-user Windows 11 VM checklist in docs/pm/M5-checklist.md: terms, SmartScreen/hash, no UAC, shortcuts, offline reboot/transcription, cancellation/failure/retry, upgrade and both uninstall choices.
2. Review draft user guides on m6-docs. No further license decision or artifact containment is pending for ISSUE-018/019.
3. No merge, release publication or repository-setting change is requested. The unsigned installer is a CI artifact only.

## 1. Summary

PM's installer-runtime exception is implemented under ADR 0023, with unchanged processing-app allowlist. ISSUE-018 is resolved; ISSUE-019 is resolved and reclassified as process S1 after Owner deletion of artifact 12488875272 (read-only verification: HTTP 404). The installer upload now explicitly depends on passing installer license and installed acceptance gates, overall success, and prior source/offline/regression jobs. A real negative CI job deliberately fails a synthetic gate and proves upload is skipped; a unit test ties its condition to production.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Actual pinned runtime units and notices | met | Setup.e32/SetupLdr.e32, reviewed source hashes, runtime-input receipts, original JEDI source/full MPL in installer |
| Installer-only exceptions | met | Exact name/license pairs; negative tests reject the same pairs in app context |
| Failure prevents installer upload | met | Live negative CI case and production-expression regression |
| Full source/quality/policies | met | Local 197 passed/1 CI-only skip, 94.5% strict coverage; CI evidence below |
| Installer license / installed payload / WFP | met | Green CI 39985711346, 221 installed files checked, calibrated processing events 0 |
| Latest M5 carried into m6-docs | met | Normal merges, only docs differ; no history rewrite |
| Clean VM and hardware acceptance | pending Owner | Checklist remains open, no replacement with elevated-runner results |

## 3. What changed

- ADR 0023 permits the unmodified Inno runtime's Pascal Script, LZMA/public-domain code, actual JEDI units and Delphi compiled RTL/VCL only in installer context. Original attribution and full applicable notices remain separate from Dusty's own terms.
- Source/build verification selects Setup.e32, the 32-bit loader, twelve directly referenced Pascal Script units, the LZMA/7z C objects, MD5/SHA1/SHA256 wrappers, and exactly NewUxTheme/NewUxTheme.TmSchema. No custom-style packs, IDE/compiler or standalone Delphi libraries are shipped under this exception.
- Both exact JEDI source files are distributed inside installer-jedi-source.zip with complete MPL/notices and upstream links. No Dusty changes to these units. The gate rejects changed source, notices, selected runtime or bootstrap provenance. The compiled application uses the upstream runtime; we do not rebuild Inno or claim a Delphi development license.
- Pinned tag is-6_7_3 has annotated tag object c7af86b4b2fd03371185df2b09a1dca8d472ab70, peeled commit 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf. Earlier records calling the tag-object ID a commit were corrected in current provenance/docs. Every reviewed source file verifies from the actual immutable commit; no version or compiler binary changed.
- Installed-file identity checks compare every app payload file plus installer notices/source archive, allowing only generated Inno uninstall records beyond that inventory.

Detailed verification: docs/dev/installer-runtime-inventory.md and packaging/licenses/inno/runtime-source.json. Source/build attribution is explicit; it is not a recovered linker map or reproducible rebuild claim.

## 4. Test results

Local final source: `uv run python tools/measure_coverage.py` -> 197 passed, 1 CI-only skip in 179.59 s. Coverage: core 93.7%, export 98.6%, models 95.2%, queue 93.0%, privacy 96.2%; total 94.5%. Ruff, format (124 files), mypy (69 sources) and all three source policy checks pass.

Local rebuilt bundle: 216 files / 161987504 bytes at that checkpoint; 64 PE checks, app license and packaged GUI smoke pass. Subsequent changes are retained notice/provenance data; final CI inventory below identifies the actual artifact.

[CI 39985711346](https://github.com/dusty-corporation/dusty/actions/runs/39985711346) at fa5fbcb is fully green: checks, offline, installer-upload-regression and packaging-spike. Source tests: **196 passed, 2 expected skips in 198.53 s**; separate real-network Tiny integration: **1 passed**. Installer license check passed with no findings. Installed-file identity passed for **221 files**; all **64 processing PEs**, app licenses and packaged GUI smoke passed.

WFP calibrated controls passed. Source processing/self-test/headless/GUI: **0** connection events. Source Model Manager: GUI **0**, fetch allowed **4**, blocked **0**. Packaged self-test: **0**. Packaged Model Manager: GUI **0**, fetch allowed **4**, blocked **0**. Installed self-test using installer-downloaded models: **0**.

Silent per-user install, bundled Tiny/VAD download, installed self-test, upgrade with downloader blocked and unchanged verified model hashes/mtimes, keep-models uninstall, remove-models uninstall and unchanged user-output sentinel all passed. No Owner desktop install was run.

Actual CI app payload: **216 files, 161989319 bytes**. Unsigned installer: **34618916 bytes**, SHA-256 `4ea17b60157593ff989c06e9d6d8e745b8e25ba61f0bb77478706ee58e1a2720`. [CI-only installer artifact 12516525534](https://github.com/dusty-corporation/dusty/actions/runs/39985711346/artifacts/12516525534), compressed 34206853 bytes. It was uploaded only after all gates passed, never to a release. Audit metadata: artifact 12516480610, m5-installer-draft-audit, includes full inventories, notices, SBOM, runtime receipts and acceptance summary.

Original upstream runtime input hashes recorded in that receipt:

| Input | SHA-256 |
|---|---|
| Setup.e32 | a80d75ba8d8c336050c37f7707de8bb017cc93597329e0ea18d474156b3e0da5 |
| SetupLdr.e32 | 5475964893adbb33ccc420ad4d88bbdff27dfaaca7580cd6058ea2798893490d |

Report/ledger commits add documentation only. Final branch-head CI is checked again before handoff; no skipped or in-progress run is treated as passing.

Failed attempts are retained, not hidden: an overlapping targeted pytest invocation collided with the active .pytest-tmp, producing 3 setup errors (WinError 32) and one GUI resume failure in the affected full run. The serial rerun passed unchanged tests. A direct-generator import-path regression was caught locally, fixed and covered by a subprocess CLI test. CI 39984075122 failed source fetching with HTTP 404 because a tag-object SHA was used as a commit; the peeled-commit correction verifies all original source hashes. None of these failures was waived or a test weakened.

Dash verification: `git grep -n -I -e "$([char]0x2014)" -e "$([char]0x2013)" -- .` -> no output, exit 1 (no matches). SPEC and CURRENT_MILESTONE.md unchanged.

## 5. Deviations

ADR 0023's PM-approved installer-only amendment is the licensing exception. ADR 0022 still uses bundled dusty-fetch for downloads. Explicit PM authorization covers the M5/M6 prework despite the preserved current M4 brief. Installer binaries remain CI artifacts; no release is created or published.

## 6. Issues

| Issue | Status | Resolution |
|---|---|---|
| ISSUE-018, S1 | Resolved | Scoped PM exception, verified runtime units and retained notices/source |
| ISSUE-019, process S1 | Resolved | Owner removed artifact; upload requires full license gate plus regression proving failure blocks upload |

Historical incident report M5-interim-6.md remains an audit record; this report supersedes its stop/containment instructions.

## 7. Decisions needed

None for these license/process findings. Normal PM/Owner installer acceptance remains separate from this engineering verification.

## 8. Owner steps

Retrieve the tested unsigned review artifact with `gh run download 39985711346 --repo dusty-corporation/dusty --name m5-installer-draft-unsigned --dir build/owner-m5-review`. Compare the exact executable's Get-FileHash SHA256 with its SHA256SUMS.txt, then copy to the clean VM. Do not install into the development profile for the acceptance test. Follow the M5 checklist and send pass/fail plus plain errors, not private recordings or local state.

## 9. Remaining risks

Clean-machine standard-user UI, interruption/retry, SmartScreen and real hardware still need Owner checks. No final M5 or M6 milestone acceptance is claimed. M6 docs remain a draft. The previous desktop endurance summary remains in docs/pm/benchmarks/m6/desktop-long-recording.md; raw audio/JSON was not committed. Real Surface Vulkan smoke remains required before M7.

## 10. Effort notes

The fixes preserve the actual boundary: installer-specific licensing never permits those components in Dusty's processing app. Explicit CI outcomes and the synthetic failing-gate case now protect the upload sequence that failed previously. Both branches are pushed, with no PR, merge into main, release publication or force push.
