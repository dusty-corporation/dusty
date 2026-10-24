# Current milestone: M5 - Packaging, installer, release pipeline

Proceed per `docs/pm/SPEC.md` section 12 M5, sections 10.4 and 11.6, and the accepted ADRs (0014, 0019 to 0023). This brief adds PM requirements on top of the spec. Where they conflict, this brief wins. First archive the M4 brief to `docs/pm/briefs/M4-brief.md`.

## Branch setup (do first)
- M4 is merged to `main` (squash, 87a1304). `m5-packaging-spike` and `m6-docs` predate that squash.
- Create `m5-installer` from the current `main`. Port the M5-only work from `m5-packaging-spike` onto it (installer, packaging, license and payload gates, workflows, ADRs, issues, M5 reports and checklist). Do not carry over anything M4 already merged. Prefer a clean port over a conflicted rebase.
- Leave `m5-packaging-spike` and `m6-docs` untouched as references. Deleting branches is Owner-only. The docs come back after M5 merges.

## Step 1: gap analysis
Before building, add a table to the top of the final report: each SPEC M5 task (1 to 6) and acceptance item, its status on `m5-installer` after the port (done, partial, missing), and the evidence. Then finish everything that is partial or missing.

## PM requirements

### Installer pages and wording
- License page: Dusty's Apache-2.0 license, the third-party notices, and the Microsoft Visual C++ runtime license terms (ADR 0020, Distributable Code section 4.b). Confirm all three are reachable from the license page.
- Choose model page: the same names, "Best for" text, sizes and accuracy note as the Model Manager, read from `messages.py` or generated from the same source. No second copy of the wording.
- Pre-selection: base it on a real Vulkan device check with the bundled engine, not on a GPU name list. The Surface Laptop 5 (Iris Xe) must get Large v3 Turbo pre-selected, as the ThinkPad benchmarks justify. Machines without a usable Vulkan device get Small. If a real device check is impossible without a model file, pre-select Small everywhere, and report it as a UX decision for the PM.
- Download step: the same consent sentence as the Model Manager ("Download <names> from github.com (<size>)?"), shown on the page, not as a popup. Voice detection is always included.

### Failure handling
- If the download, verification or self-test fails, the installer says so in plain words and offers Retry.
- PM decision: also offer "Finish without a model". The install completes, and Dusty opens to its existing "recommended model is not installed yet" prompt. The installer must not report success for a download or self-test that failed.
- No internet: a plain message (not a raw error code), with Retry and Finish without a model.
- Cancelling during the installer download removes the partial file, like a normal cancel in the Model Manager.

### Upgrade and uninstall
- Upgrade keeps models and skips downloading any that verify. A model that fails to verify is shown as needing download again.
- The uninstaller has a checkbox "Also remove downloaded models (X GB)", checked by default, with the real size. It never touches the user's transcript folders. Anything left behind must be exactly what the user chose to keep.

### Release pipeline
- `release.yml` on tags `v*`: build or reuse the pinned native artifacts by hash, PyInstaller, Inno Setup, `THIRD_PARTY_NOTICES.md`, CycloneDX SBOM `dusty-<version>-sbom.json`, `SHA256SUMS.txt`, the offline/network test against the installed app on the runner, and a DRAFT GitHub Release holding everything. The upload must come after every gate passes (keep the ISSUE-019 regression test).
- This brief authorizes you to push test tags matching `v0.5.0-m5.N` (N = 1, 2, ...) to exercise `release.yml`. No other tags. The releases they create stay draft. Never publish, edit out of draft, or delete tags or releases (AGENTS rule 13).
- Report the installer size and the full list of release assets with hashes.

### README
Add the "Windows SmartScreen warning" section (SPEC M5 task 6) in plain words for a non-technical reader: why the warning appears (unsigned, free, open source), "More info" then "Run anyway", and how to check the installer against `SHA256SUMS.txt` with one PowerShell command (`Get-FileHash`).

### Owner VM checklist
Update `docs/pm/M5-checklist.md` to final. It covers SPEC 11.6 on a fresh Windows 11 VM with a standard (non-admin) user, numbered steps, and an expected result for each. Start with how to set up a free VM: Hyper-V if the Owner's Windows edition supports it, otherwise VirtualBox, with the official Windows 11 ISO left unactivated. Include the SmartScreen step, the tampered model test, the interrupted download test, the upgrade test (install an earlier `v0.5.0-m5.N` draft build, then a later one) and both uninstall variants. Aim for about 45 minutes, not counting downloads.

### Carry-over nit
`tools/render_models.py` (and any other screenshot renderer) put a `state/settings.json` into the M4 screenshot zip. Screenshot zips contain PNGs and the README only. Add a check.

## Privacy and network (must hold)
- The installer process itself makes no network connections. Downloads happen only through the bundled `dusty-fetch` (ADR 0022). Extend the installed-app WFP test to cover the installer download step: installer and GUI 0 connection events, `dusty-fetch` allowed. Report all counts.
- PE import gate, static no-network check (zero exceptions), license gates and the audit hook stay as they are.

## Out of scope
Code signing, winget, Microsoft Store. Enterprise proxy (backlog). Catalog changes. M6 docs beyond the README section above.

## Reporting
Interim reports only for decisions affecting correctness, privacy, licensing or the user experience. The final `docs/pm/reports/M5-report.md` has the gap table, SPEC M5 acceptance evidence, installer screenshots of every page in light theme at 100% and 150% (draft `m5-screenshots` release, PNGs only), WFP results, the release asset list with hashes, the installer size, test and CI results, and "Owner actions" (the VM checklist). Then stop. Do not open a PR against `main` until the PM accepts the report.
