# Task Ledger

| ID | Milestone | Task | Status (todo/doing/blocked/done) | Evidence | Issues |
|----|-----------|------|----------------------------------|----------|--------|
| M0-01 | M0 | Repo structure, license, README, changelog | done | `d409eca`, `116ba37`; `git add --renormalize .` had no line-ending warnings | ISSUE-001 (resolved) |
| M0-02 | M0 | Pinned Python dependencies and lockfile | done | `d409eca`; `uv sync --locked --python 3.12` resolved 60 packages | ISSUE-001 (resolved) |
| M0-03 | M0 | Review AGENTS.md, ledger, ADRs | done | Existing AGENTS.md retained; ADRs 0001–0014 in `d520f47`, `da2ef29` | ISSUE-001 (resolved) |
| M0-04 | M0 | Three policy checks and negative tests | done | `2af2ad2`, `38c8d68`; `uv run pytest`: 13 passed; all three policy commands passed, with negative tests | ISSUE-002 (resolved) |
| M0-05 | M0 | Windows CI workflow | doing | `64eca81`; branch push and CI result pending | — |
| M0-06 | M0 | Empty Qt window and --version | done | `d409eca`; `--version` printed `Dusty 0.0.1`; Owner confirmed window on 2026-10-21 | — |
