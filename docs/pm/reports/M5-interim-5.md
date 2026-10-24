# M5 Interim 5 - M4 sync and installer prework

## 1. Summary

The split app bundle is synchronized with M4 and passes PE, license, GUI and
both WFP gates. An unsigned per-user installer now compiles, but its binary
upload is deliberately blocked by ISSUE-017: the InnoSetup license is absent
from the redistribution allowlist despite Inno being the approved tool.
Only installer audit metadata is uploaded. No installer was run on the Owner's
computer, and no release or PR was created.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| M4 retained in split bundle | met | 39915503372 app steps pass; actual Model Manager downloads through sibling fetch. |
| PE, licenses, GUI smoke | met | 64 exact-pin PE checks; app inventory/SBOM/license gate and real Qt startup/close pass. |
| Packaged offline WFP | met | Zero processing connections; positive control calibrated. |
| Packaged download WFP | met | GUI 0, fetch allowed 4, blocked 0; consent and both asset hashes verified. |
| Inno script and compiler | met for prework | 6.7.3 bootstrap SHA and engine banner, installed/source license identity and PE32 guard pass; unsigned compilation succeeds. |
| Installer redistribution policy | not met | InnoSetup rejected by the same allowed_license function; proposed ADR 0023 requires PM approval. |
| Install/upgrade/uninstall acceptance | not met | Standard-user VM and installed-app WFP checks remain M5 work, not established by compilation. |

## 3. What was built

- Generated model catalog/size selection, required VAD, full Apache LICENSE,
  NOTICE and Microsoft runtime EULA agreement, per-user lowest-privilege layout
  and shortcuts. No models are bundled.
- ADR 0022 records the PM's bundled-fetch choice. Existing verified models skip
  HTTP; downloaded models verify again before the offline self-test. Failure
  stays on the retry page; incomplete completion returns code 10.
- Job Object containment for installer children and an uninstall model checkbox.
  Offline cleanup removes only recognizable data, preserves unknown content,
  recordings and output folders, and refuses corrupt or linked protection data.
- Pinned CI compiler, unsigned hash/size metadata, policy hold and audit artifact;
  SmartScreen/hash guidance and the Owner's M5 acceptance checklist.

## 4. Test results

- M4-rebased M5 baseline: 179 local passes/1 CI-only skip; 94.4% coverage.
  Full green CI 39910562031 at 5ca1180.
- Installer draft full local run before final ownership regressions: 186 passes,
  1 CI-only skip, 184.24 s; strict coverage 94.5%.
- Final focused installer suite: 10 passed. Ruff, format (117 files), mypy
  (66 source files plus generator) and all three app policy checks pass.
- 39915503372 at 3d312fd compiled the installer, then failed the installer-only
  license gate as intended. App gates passed. Its source checks separately
  reported one 229.671 ms Qt event-loop gap against the unchanged 200 ms limit:
  1 failed, 186 passed, 2 skipped; no threshold was relaxed or test disabled.
  The preceding 39914143568 source checks passed. Final code verification is
  39916465602 at 0adc037; its result is recorded below.

### Final code verification

At 0adc037, local full suite: **189 passed, 1 CI-only skip in 174.00 s**;
94.5% strict coverage. CI **39916465602**: **188 passed, 2 expected skips in
274.44 s**, plus the separately passing real-network integration. The original
200 ms responsiveness gate passed unchanged. Source checks and offline jobs
are green. Every packaged app gate and compiler step passed; the sole failure
is the explicit InnoSetup license-policy hold, and installer binary upload was skipped.

The final app review artifact is m4-review-bundle in that run, artifact
12484769263. It contains 207 files/161,936,952 bytes. Final compiled installer
measurement: 34,593,012 bytes, SHA-256
`a63903ef8020bc4e469365fb36aa88b5ae68e518124dbde0acf0882a2da0b632`.
Only its metadata was uploaded in m5-installer-draft-audit. App WFP again
records zero processing/GUI events and four allowed/zero blocked fetch events.

### Measurements from 39915503372

- App bundle: 207 files, 161,936,686 bytes (154.43 MiB). The two additional
  files since the 205-file M4-sync baseline are Inno source license/provenance
  text; no PE was added. The 64-PE gate still passes.
- Compiled installer: 34,586,726 bytes, unsigned, no models;
  SHA-256 `8f7d644fe54570e16a4ee841f96060348b91d33f52a5cfe39266188c522bdc45`.
  It was not uploaded. Artifact m5-installer-draft-audit contains only terms,
  input hashes, measurement/hash metadata and the license finding.
- The existing CycloneDX SBOM covers the app bundle. Installer-wide embedded
  component inventory/SBOM remains required before installer distribution;
  Inno approval must not silently approve unrelated compiler-bundled components.

## 5. Deviations from SPEC

ADR 0022 supersedes Inno's built-in model HTTP downloader under the PM's
explicit decision. Existing Apache/CRT/stdlib DOCX/platform-pin approvals
remain unchanged. The Inno license exception is proposed, not accepted.
This prework uses artifact-only CI, not the future tag/release workflow.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-017 | S1 | Open | Explicit InnoSetup policy clearance and complete installer component inventory are required before binary distribution. |

No actual privacy/network/license violation observed. No unallowlisted installer
was distributed; our run 39914802080 was cancelled before compile/upload, not deleted.

## 7. Decisions needed from PM/Owner

1. Approve proposed ADR 0023 as a narrow InnoSetup exception for the pinned
   installer runtime and exact retained terms (recommended), or choose another
   installer and replace ADR 0008. Do not relabel the license as BSD/Zlib.

## 8. Owner actions for the morning

1. Review ISSUE-017/ADR 0023 first. Binary upload remains gated until that policy
   decision and the remaining installer-wide inventory are complete.
2. Use M4-report.md for the short ThinkPad Model Manager review; the allowed
   m4-review-bundle artifact is independent of the held installer.
3. After an installable draft is cleared, perform docs/pm/M5-checklist.md on a
   fresh standard-user Windows 11 VM: license, defaults, download failure/retry,
   cancellation/termination/resume, self-test failure, shortcuts, upgrade reuse,
   both uninstall choices and installed-app WFP. No clean-machine result is claimed.

## 9. Risks for the next milestone

Inno ABI/cancellation and conservative cleanup need independent and VM review.
Unknown/overlapping app data is preserved with a notice rather than risking
user files. Installer-wide SBOM, installed-app WFP and draft release automation
remain M5 release work; the current app SBOM is not an installer-wide audit.

## 10. Time/effort notes

Pinned-version verification found ISCC's launcher version is 0.0.0.0, an Inno
section-parser edge case and the changed CreateCustomForm API since 6.6.
These were fixed with upstream/compiler evidence, without changing architecture,
dependencies or acceptance thresholds. No engineering-hour estimate is asserted.
