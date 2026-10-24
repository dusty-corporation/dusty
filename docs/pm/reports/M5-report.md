# M5 report - Packaging, installer and draft release pipeline

## Summary

Implementation is on `m5-installer`. ISSUE-020 is resolved with green ownership,
packaged, installed WFP and uninstall evidence. The PM page round and Owner's
output-row change are implemented. Final tagged upgrade acceptance is running;
M5 acceptance remains pending the Owner's fresh standard-user VM results.
No PR, merge or published release has been created.

## Owner actions for the morning

1. Use only the repaired draft builds identified in the final release table below.
   Do not use historical .1 through .7 builds for acceptance.
2. AMD SVM is already enabled. Follow [M5-checklist.md](../M5-checklist.md) on
   VirtualBox 7.2.22 with a fresh Windows 11 standard user. Return numbered results.
3. Review the new installer and main-window screenshot bundles on the draft
   [m5-screenshots release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-a1e1f91641e95222b8da).
4. Confirm actual native 100%/150% page scaling, Cancel/X/Escape, and that checked
   Open Dusty now survives Setup exit. Native screenshots do not prove those flows.
5. The VM normally lacks a physical Vulkan GPU. Retain the ThinkPad probe evidence;
   physical GPU inference/retry and the pre-M7 Surface Vulkan smoke remain hardware checks.
6. Keep all releases draft. Publishing and merging remain Owner-only.

## Final gap table

| SPEC M5 task or acceptance item | Status | Evidence / remaining work |
|---|---|---|
| 1. PyInstaller, bin/resources | Done | Separate onedir app/fetch, engine-v2 and minimal FFmpeg, exact PE pins, license/SBOM/notices gates. No models bundled. |
| 2. Generated installer pages, download, self-tests | Partial | Shared catalog/consent, model-free real-GPU/RAM probe, Auto per model plus smallest CPU test, VAD verification, Retry/CPU/Finish without, revised pages implemented. Native cancellation passed in CI 40065869279; fresh VM pending. |
| 3. Upgrade | Partial | Verified hashes and write times preserved with fetch blocked in CI. New two-version tagged evidence pending below. Damaged models show Needs download again. |
| 4. Uninstall | Partial | Both automated variants and transcript sentinel pass for ISSUE-020 repair. Conservative owned-content cleanup preserves unknown/linked/changed files. Native Cancel passed in CI 40065869279; VM both variants pending. |
| 5. Gated draft release | Partial | Read-only prior gated artifact, strict receipt checks, upload-order negative test and five-asset staging implemented. Final repaired tag runs pending. |
| 6. SmartScreen README | Done | Plain unsigned explanation, More info/Run anyway, full SHA comparison using Get-FileHash. |
| Acceptance: tagged CI draft and artifacts | Pending | Final repaired test tags listed below when all gates finish. Historical drafts are not recommended. |
| Acceptance: fresh Windows 11 VM, SPEC 11.6 | Owner needed | Checklist includes expected results, standard user, model tamper, normal/crash interruption, upgrade, both uninstall variants and protected outputs. |
| Acceptance: installer size | Pending | Record final asset bytes and hashes after the gated draft completes. |
| Brief: all native pages light 100%/150% | Partial | 21 new native page PNGs plus README uploaded. Effective 96 DPI on unchanged 175% desktop is disclosed; genuine native scaling remains VM acceptance. |
| Brief: Setup/probe/GUI/fetch WFP | Done for repair | CI 40061186069: Setup 0, GUI/probe 0, native 0, fetch allowed 4, blocked 0. Final tagged receipt pending. |

## Test and CI evidence

- ISSUE-020 final repair `1b62946`: [CI 40061186069](https://github.com/dusty-corporation/dusty/actions/runs/40061186069)
  all jobs green. Source 293 passed, 2 expected skips; separate real-network
  test 1 passed. Required package coverage 94.2%, all packages above 85%.
  Packaged PE/license/GUI/WFP, installed payload/PE/WFP, both uninstall choices,
  model preservation and output sentinel passed.
- Page checkpoint `481535c`: CI 40063816476 all jobs green.
- Cancellation checkpoint `bcad8fd`: CI 40064929172 source/offline/packaged gates
  passed, but installer compile failed with Type mismatch at generated line 716.
  Corrected in `7b8d28b`; CI 40065869279 all jobs green. No failed binary uploaded.
- Output row `a75f1cf`: 29 GUI tests passed, lint and mypy passed. Full source
  coverage: 297 passed, 1 expected skip in 209.36 s, 94.2%. Sandbox TLS/junction denials were rerun with approved
  escalation; tests and assertions remain unchanged.

## Page review round

All wording comes from messages.py. Download replaces consent with a persistent
Downloading heading, uses Next=Download, shows byte totals under the bar and
keeps Back available until starting. Graphics failure offers Retry, processor
retry and Finish without. Success is singular/plural; failed setup is never called
successful. Finish has checked Open Dusty now, current-user launch; desktop
shortcut is checked. Voice detection size comes from the catalog. Uninstall is
compact with a true-size checkbox and Cancel as default. Artwork is backlog.

Native Back -> models -> Tiny selection -> Next was exercised in the safe review
build: consent changed 488.5 MB to 566.2 MB. Progress/failure previews are synthetic
review states and never install or download. ISSUE-021 fixes the real post-copy
Cancel/X path that Inno otherwise ignores; final acceptance is recorded below.

Owner's output row is now Choose folder... followed by Saving to, then TXT/Word,
then Options... and its summary. Equal button widths align both summaries. Long
paths use Qt ElideMiddle and recompute on resize; full path remains the tooltip
and accessible description. No-folder amber and save-next-to disabled states,
actual keyboard order and narrow-window bounds have regression tests.

### Screenshot assets

On the draft m5-screenshots release:

- `m5-main-output-row-a75f1cf-light-dark-100-150.zip`: 16 actual Qt client-area PNGs
  plus README, four destination states in both themes/scales, narrow 800 x 680
  logical window. SHA-256 `84552bcbff635ea4de685e9694bc147b930bfe5483d258aa48aad95092eb0c08`.
  Qt offscreen device-pixel ratios 1 and 1.5, no resized or fabricated UI images.
  PNG/README-only archive gate passed. No profiles/settings in the archive.
- `m5-installer-pages-pm-round-7b8d28b-light.zip`: 21 native PNGs plus README,
  7,725,089 bytes, SHA-256 `27a3731c91478669cc5f13778b8ef432624c404cb2fb2adaf0fccb2905dbe1b0`.
  Gated CI 40065869279. Actual light native controls, explicit synthetic states,
  96 effective DPI on unchanged 175% display; no native monitor-scale claim.
  PNG-only archive gate passed. Historical assets remain untouched.

## Probe and privacy evidence

Owner ThinkPad Iris Xe on 2026-10-23 returned
`{"real_gpu_found":true,"model_file_opened":false}`. The bounded Job Object probe
initializes a real Vulkan device and a 4 KiB buffer without opening a model.
Software devices, failure, crash or timeout select Small; RAM below catalog minimum
warns rather than blocks. Temporary payload extraction timing remains a VM check.

Downloads occur only in dusty-fetch, with HTTPS host/redirect allowlisting and
manifest size/SHA checks. Setup/GUI/probe/native connection events must be zero.
Static no-network has zero exceptions; audit hook, excluded networking modules,
exact pinned platform PE exceptions and dynamic WFP remain enforced.

## Final draft builds and release assets

`v0.5.0-m5.8` / 40066137913 failed true-upgrade inventory: old versioned own
LICENSE/NOTICE remained. No draft or gated installer upload. ISSUE-022 repair
`ca6ff44` adds exact byte/hash-checked obsolete own-license cleanup before copy;
unknown/changed/linked/protected contents preserve and block. Unit tests pass.
`v0.5.0-m5.9` / 40067407725 is the repaired rerun. A second successful repaired
build follows for the Owner's VM upgrade test. Final assets/receipts pending.
Five assets only: unsigned installer, THIRD_PARTY_NOTICES.md, versioned CycloneDX
SBOM, installer-jedi-source.zip, SHA256SUMS.txt. No portable asset.

## Self-review

ISSUE-020 was found adversarially and resolved with the PM-approved ownership
rule. The three original regressions remain enabled. Unique purpose/inventory
markers, byte/hash continuity, unknown-content preservation, reparse refusal and
managed source/output rejection cover startup, jobs, probe, self-test and uninstall.
See [M5-interim-9.md](M5-interim-9.md) for every delete-call safety basis.

Pinned-source review found ISSUE-021: Inno's normal Close path ignores post-copy
pages. The shared controlled stop now ends the child Job, removes its active
partial, preserves verified models and finishes through normal Inno cleanup with
no application launch. A real-prefix cancellation audit and retry are required
for final release staging. Actual button/X testing remains the VM checklist.

No new dependencies or network paths were added. ADR 0019 to 0023 exception
scopes, Microsoft provenance, installer runtime notices/source retention and
license-upload ordering remain enforced. Non-urgent review items are in
AUDIT-NOTES.md. No hardware/VM/failure result is fabricated.

## Questions for the PM

- Review the new page bundles. No new correctness, privacy or licensing decision
  is currently requested; the accepted decisions are implemented.
- M5 acceptance must await the fresh standard-user VM results. Native scale and
  physical GPU checks are explicit remaining evidence, not inferred from CI.

## Branches and limitations

`m5-installer` holds implementation/evidence. `m6-docs-v2` carries the ISSUE-020
repair through `7ec6c59`, with installer/output-row behavior guides updated. The new ISSUE-022
helper will be carried after its gates.
Reference `m5-packaging-spike` (`95dd90b`) and `m6-docs` (`c855b52`) stay untouched.
No M6 acceptance, PR, publication, merge or repository setting change is claimed.

## Time and effort notes

Ownership repair and verifying Inno's post-copy navigation/cancellation required
more work than page rendering. Safe previews, real lifecycle tests and VM
acceptance are kept separate. Final tagged evidence remains in progress.
