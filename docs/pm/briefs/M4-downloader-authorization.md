# M4 downloader-only authorization

PM instruction 2026-10-22: create m4-downloader from m3-gui while the Owner
is away. Correct M3 report steps 6/17 to Passed on this new branch only.
Implement download/verify CLI in dusty_fetch with standard-library HTTPS,
strict verified release-host allowlist, resumable verified .part files,
space/cancellation safety and JSON-lines progress. Test via local HTTPS;
add one CI-only real tiny download, retain zero-exception offline checks,
and prove dusty never imports dusty_fetch. No GUI changes, no changes to
m3-gui, no PR against main. Push small commits and stop with a short interim.
CURRENT_MILESTONE.md is left as the Owner's M3 brief; this direct PM instruction
authorizes only the limited M4 prework on this branch.
