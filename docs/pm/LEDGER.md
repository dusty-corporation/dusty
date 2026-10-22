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
| M1-A6 | M1 | Bench tooling and accuracy reference | done | Source-text-only spans in `swineherd-scored-spans.json`; 20 desktop public runs scored; four scorer tests passed | - |
| M1-A7 | M1 | Bench kit draft prerelease | done | Drafts `bench-kit-m1` and `bench-kit-m1b`; new kit 46,254,971 bytes, SHA-256 `16f94ad209be637ae41e1dda61b619d68e4b32a2bf2e8010ad848e64efaad1cc` | - |
| M1-B1 | M1 | Proxy hardware and gate decision | done | PM approved ThinkPad i7-1365U/Iris Xe 96EU proxy, estimated 20% faster than Surface, RTF target 0.8; `docs/pm/benchmarks/m1/README.md` | - |
| M1-B2 | M1 | Correct WER scoring and preserve desktop results | done | `be02def`, `11031b9`; 20 public JSON files scored on three Gutenberg-only spans; private files contain timing only | - |
| M1-B3 | M1 | Distinct result names and Quick mode | done | `fa17ee9`; public/private smoke tests and overwrite rejection passed; local Quick check ran both backends | - |
| M1-B4 | M1 | Record Iris Xe startup concern | done | `docs/pm/issues/ISSUE-004-iris-xe-startup-cost.md`; M2 investigation proposed | ISSUE-004 (open) |
| M1-B5 | M1 | Revised draft bench kit | done | `bench-kit-m1b` uploaded as draft and verified; original draft retained | - |
| M1-B6 | M1 | ThinkPad results and final gate report | done | 10 CPU and 10 Vulkan public runs at four threads, 20 matching JSON files; Gutenberg-only WER computed for all; `docs/pm/reports/M1-report.md`; PR #2 checks passed at runs 39718968447, 39718973895, 39718973892, and 39718973902 | - |
| M1-B7 | M1 | Focused Quick thread sweep | done | `b1f3ac0`; local 4, 8, 10 thread smoke test produced three rows each on CPU and Vulkan; draft `bench-kit-m1c` verified | - |
