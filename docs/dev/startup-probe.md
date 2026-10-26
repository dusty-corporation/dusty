# Reproducing the startup probe

From a public source checkout, fetch the hash-pinned engine-v3 packages and
public models, then run the probe with the tiny model and JFK fixture:

```powershell
uv sync --locked
uv run python tools/fetch_dev_binaries.py
pwsh -NoProfile -File .\tools\bench\startup-probe.ps1
"EXIT CODE: $LASTEXITCODE"
```

The probe runs five separate CPU processes followed by five Vulkan processes,
with four threads and voice detection off. Each process has a 180-second timeout.
A Vulkan row requires the startup log to confirm Vulkan was selected. Raw text
and local paths are discarded; only numeric timings and CPU variants are shown.

Compare the first run with runs 2-5. Wall time includes startup and shutdown;
the first progress callback is not an isolated shader-compilation measurement.
The supported CPU dispatch variants and engine hashes are documented in
engine-v3.md and pinned in native/versions.toml. A software Vulkan driver is not
accepted as a usable graphics device by the installer's separate model-free probe.

Historical no-clone probe kits remain in the private engineering archive. They
are not public release assets and their old setup script is not an input here.
Keep power settings and graphics drivers unchanged during a measurement and
report the header, all timing rows and exit code, without recording contents.
