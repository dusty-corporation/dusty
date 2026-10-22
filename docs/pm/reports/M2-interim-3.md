# M2 Interim 3 - Startup probe ready for Owner

## 1. Summary

The native startup probe and standalone download kit are ready. Owner measurements
on the ThinkPad and desktop are pending, so ISSUE-004 remains open. The Owner's
WIP checkpoint was clean and in sync, and the probe changes were pushed as
`3ea08c5`. Per the latest Owner instruction, this handoff stops after the probe;
exporter hardening, WFP CI, VAD checks, and coverage can continue while waiting.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Five CPU and five Vulkan runs without Python | met | Repository and standalone kit runs exited 0; local summary in benchmarks/m2 |
| Published binary and model pins verified | met | Setup fetched engine-v1 and models-v1; archive, extracted file, and tiny hashes verified |
| Actual Vulkan and timing checks | met | Vulkan banner required; missing required timings or nonzero exit fails |
| Owner ThinkPad and desktop measurements | not met | Exact commands below; awaiting results |
| Full M2 acceptance | partial | Pipeline WIP preserved; WFP, VAD, translation and final integration evidence remain |

## 3. What was built

`startup-probe.ps1` checks hashes, parses timings without exposing raw text,
checks actual backend selection, reports CPU variant, and times out a hung run.
`setup-startup-probe.ps1` obtains pinned binaries and tiny via `gh`.
`package-startup-probe.ps1` creates a small kit with scripts and public audio.
Instructions and timing limitations are in `docs/dev/startup-probe.md`.

## 4. Test results

- `git status`, `git log --oneline -5`, and approved `git pull --ff-only` confirmed
  clean `m2-core-pipeline` at Owner checkpoint `9df2013`.
- Repository probe: ten successful runs. Standalone kit setup downloaded and
  verified its published inputs, then all ten probe runs succeeded.
- Standalone Vulkan run 1: 13.935 s; runs 2-5: 0.558-0.579 s. CPU: 0.561-0.745 s.
  See `docs/pm/benchmarks/m2/startup-probe-local.md`; root cause is not established.
- `uv run mypy`: passed, 39 source files.
- Prior checkpoint tests: 50 passed; standard-library coverage measured 91.6%
  overall across strict packages. These have not been rerun for this script-only
  handoff; final M2 evidence is still pending.
- Draft asset: `startup-probe-m2.zip`, 318360 bytes; verified by `gh release
  download`, with GitHub digest and local SHA-256 both
  `5f52d4c0a967c96c69bea955e0c4a817ff2042e1e1b01f9fac551a6190cc5f91`.
- No new CI acceptance claim is made in this interim report.

## 5. Deviations from SPEC

ADR 0017 records the PM-approved audit hook that supersedes SPEC 9.2.3's
monkeypatch design. No new dependency or native component was added.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-004 | S2 | Open | Owner startup measurements pending |
| ISSUE-005 | S1 | Resolved | PM corrected English-only model to small.en |
| ISSUE-006 | S1 | Resolved | PM approved audit hook with zero static exceptions |

## 7. Decisions needed from PM/Owner

No design decision yet. If repeated Owner Vulkan runs still exceed 10 seconds,
propose an ADR with measured evidence before changing ADR 0004.

## 8. Actions needed from the Owner

In PowerShell 7 on the ThinkPad, from a folder where you want to keep the kit:

```powershell
gh auth status
gh release download startup-probe-m2 --repo dusty-corporation/dusty --pattern startup-probe-m2.zip --dir .
Expand-Archive -LiteralPath .\startup-probe-m2.zip -DestinationPath .
Set-Location .\startup-probe-m2
pwsh -NoProfile -File .\tools\bench\setup-startup-probe.ps1
pwsh -NoProfile -File .\tools\bench\startup-probe.ps1 | Tee-Object -FilePath ("thinkpad-startup-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".txt")
"EXIT CODE: $LASTEXITCODE"
```

Use an authenticated Owner account to access the draft. If auth status fails,
run `gh auth login` first. No clone, Python, compiler, or Vulkan SDK is needed.

On the desktop:

```powershell
Set-Location C:\Users\kdash\whisper_app
git checkout m2-core-pipeline
git pull --ff-only
pwsh -NoProfile -File .\tools\bench\setup-startup-probe.ps1
pwsh -NoProfile -File .\tools\bench\startup-probe.ps1 | Tee-Object -FilePath ("build\desktop-startup-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".txt")
"EXIT CODE: $LASTEXITCODE"
```

Allow about 1-5 minutes for ten runs, plus a roughly 100 MB setup download.
Keep both machines plugged in and do not change power mode or graphics drivers
during the test. Send the header, all ten timing rows, exit code, and machine
label. On failure send the exact error. Do not send audio or transcript text.

## 9. Risks for the next milestone

ISSUE-004 remains unresolved until independent hardware evidence arrives.
The real Surface Vulkan smoke test remains an Owner-owned pre-M7 requirement.

## 10. Time/effort notes

Sandbox Git and uv access needed approved escalation. GitHub required the full
commit SHA for the draft target; retrying with the full SHA succeeded. No
permission escalation was denied, and no source history was rewritten.
