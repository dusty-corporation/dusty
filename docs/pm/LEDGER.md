# Task Ledger

| ID | Milestone | Task | Status (todo/doing/blocked/done) | Evidence | Issues |
|----|-----------|------|----------------------------------|----------|--------|
| M0-01 | M0 | Repo structure, license, README, changelog | done | `6324f8c`, `90def49`; `git add --renormalize .` had no line-ending warnings | ISSUE-001 (resolved) |
| M0-02 | M0 | Pinned Python dependencies and lockfile | done | `6324f8c`; `uv sync --locked --python 3.12` resolved 60 packages | ISSUE-001 (resolved) |
| M0-03 | M0 | Review AGENTS.md, ledger, ADRs | done | AGENTS.md retained and updated; ADRs 0001-0014 in `bb03965`, `dee07bf`; PM spec revision `39bf2ae` | ISSUE-001 (resolved) |
| M0-04 | M0 | Three policy checks and negative tests | done | `9754c7e`, `25c9915`; `uv run pytest`: 13 passed; all three policy commands passed, with negative tests | ISSUE-002 (resolved) |
| M0-05 | M0 | Windows CI workflow | done | Owner confirmed PR #1 merged with green CI; merge commit `3bb0f7e` on `main` | - |
| M0-06 | M0 | Empty Qt window and --version | done | `6324f8c`; `--version` printed `Dusty 0.0.1`; Owner confirmed window on 2026-10-21 | - |
| M1-HK | M1 | Housekeeping | done | `9a65509`, `d0f1407`; M0 accepted per Owner | - |
| M1-A1 | M1 | Pin and verify versions | done | `native/versions.toml`, `docs/dev/build-native.md`; pinned upstream source and SDK checks | - |
| M1-A2 | M1 | Native whisper.cpp CI build | done | CI runs 39692634372 and PR #2 run 39694259471 passed; Owner's independent Vulkan and Haswell desktop retest exited 0 | ISSUE-003 (resolved) |
| M1-A3 | M1 | Minimal FFmpeg and fixtures | done | CI runs 39693880471 and PR #2 run 39694259434 passed; 17 formats plus Unicode and long path passed, three invalid inputs rejected | - |
| M1-A4 | M1 | Model conversion pipeline | done | CI run 39691863874; ten candidates, VAD, and manifest uploaded to draft `models-v1` | - |
| M1-A5 | M1 | Verify engine flags and output | done | Desktop CPU, Vulkan, VAD, JSON, progress, and prompt limit documented in `docs/dev/engine-cli.md` | - |
| M1-A6 | M1 | Bench tooling and accuracy reference | doing | Extracted kit tiny-model public test passed; private metric-only smoke test passed; final human listening check pending | - |
| M1-A7 | M1 | Bench kit draft prerelease | done | Draft `bench-kit-m1` uploaded, 46,253,549 bytes, SHA-256 `19e5764c1848bfb944d930bbc614bf560b40ed788ebaa852fde88d3f8fce4da1` | - |
