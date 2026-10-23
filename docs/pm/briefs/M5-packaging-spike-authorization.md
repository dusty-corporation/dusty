# M5 packaging spike authorization

The PM authorized packaging-only prework on 2026-10-22, on
`m5-packaging-spike` based on `m4-downloader`. The Owner's current M3 brief
remains unchanged. This authorization covers SPEC 9.2.2 and M5 task 1 only.

Build windowed Dusty and console dusty-fetch with PyInstaller onedir, verify
the shared folder layout, bundle pinned engine-v2 CPU/Vulkan, minimal FFmpeg
and resources, without model weights. Exclude Qt networking and WebEngine.
Add Windows packaged self-test with the existing calibrated WFP audit.
Inventory actual files, size, twenty largest files and warnings; generate draft
notices and CycloneDX SBOM, and audit the bundled licenses. List unapproved
components instead of changing dependencies or license policy.

Small commits and normal pushes on the spike branch only. No installer, no
changes to the earlier branches, no PR against main. Stop with an interim report.
