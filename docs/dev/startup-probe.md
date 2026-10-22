# M2 startup probe

The kit contains PowerShell scripts and the 11-second public-domain JFK fixture.
Setup uses authenticated `gh` to download published `engine-v1` CPU and Vulkan
archives and the `models-v1` tiny model, then verifies their pinned SHA-256 hashes.
No Python, compiler, Vulkan SDK, repository clone, or FFmpeg is needed. The
machine needs PowerShell 7, GitHub CLI authentication, and its graphics driver.

The probe runs five separate CPU processes followed by five separate Vulkan
processes, with four threads, tiny, and VAD off. There is no warmup before run 1.
It rejects missing timing fields, a nonzero exit code, or a Vulkan run that did
not select Vulkan. Each process has a 180-second timeout. Raw engine text and
paths are discarded. Only numeric timing rows and the CPU variant are printed.

`first_progress_sec` is elapsed process time to the first progress callback; on
this short clip that callback may arrive near completion. It is not an isolated
shader-compilation measurement. `load_ms`, `encode_ms`, `decode_ms`, and
`engine_total_ms` come from the pinned engine's timing output; `wall_sec` also
includes process startup and shutdown. A zero decode value is valid for this
engine's timing categories. Compare run 1 with runs 2-5 for each backend.

Use `-BinDir build/engine-v2` to validate candidate binaries while keeping the
same pinned model and audio fixture. Omitting it uses `build/bin` as before.

The engine archives include runtime CPU dispatch for x64, SSE4.2, Sandy Bridge,
Haswell, Skylake-X, Cannon Lake, Cascade Lake, Ice Lake, and Alder Lake. The
`cpu_variant` field reports the `ggml-cpu-<variant>.dll` selected in the startup
log. The Vulkan row is printed only after `using Vulkan<N> backend` was observed.

## ThinkPad without a clone

In PowerShell 7, from the directory where you want to keep the kit:

```powershell
gh auth status
gh release download startup-probe-m2 --repo dusty-corporation/dusty --pattern startup-probe-m2.zip --dir .
Expand-Archive -LiteralPath .\startup-probe-m2.zip -DestinationPath .
Set-Location .\startup-probe-m2
pwsh -NoProfile -File .\tools\bench\setup-startup-probe.ps1
pwsh -NoProfile -File .\tools\bench\startup-probe.ps1 | Tee-Object -FilePath ("thinkpad-startup-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".txt")
"EXIT CODE: $LASTEXITCODE"
```

The draft release requires an authenticated account with access to the
repository. If `gh auth status` fails, run `gh auth login` first.

## Desktop with the existing checkout

```powershell
Set-Location C:\Users\kdash\whisper_app
git checkout m2-core-pipeline
git pull --ff-only
pwsh -NoProfile -File .\tools\bench\setup-startup-probe.ps1
pwsh -NoProfile -File .\tools\bench\startup-probe.ps1 | Tee-Object -FilePath ("build\desktop-startup-" + (Get-Date -Format yyyyMMdd-HHmmss) + ".txt")
"EXIT CODE: $LASTEXITCODE"
```

Keep both machines plugged in. Do not update graphics drivers or change power
mode during the run. Allow about 1-5 minutes for the ten runs, plus setup's
roughly 100 MB download. Send the header, all ten timing rows, exit code, and
machine label. If it fails, send the error exactly as printed. No recording or
transcript is needed. Do not rerun first merely to improve the numbers.
