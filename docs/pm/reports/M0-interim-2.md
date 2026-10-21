# M0 Interim Report - Foundation

## 1. Summary
M0 local implementation is largely committed, but the required `uv run pytest` command failed with a temporary-directory permission error even under approved escalation. The command reported 7 passed and 6 setup errors; no tests were skipped or weakened. Other uv verification commands passed. Work stopped under the Owner's instruction to stop if an approved escalation still fails.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| CI green on `main` | not met | No GitHub remote is configured; workflow committed as `64eca81`. |
| Each checker fails on deliberately bad samples | partial | Negative tests exist and direct pytest passed 13 tests; the required escalated uv pytest run failed during setup for six tests. |
| Window opens on Owner's machine | not met | `--version` works and a Qt window test passed locally; Owner confirmation pending. |

## 3. What was built
The foundation, locked dependencies, `.gitattributes`, ADRs 0001-0014, three policy checks and negative tests, minimal Qt entry point, Windows CI workflow, and repository directories are committed on `m0-foundation`. ISSUE-001 is resolved in its issue file. ISSUE-002 records the new test environment blocker.

## 4. Test results
`uv sync --locked --python 3.12`: success, 60 packages resolved. `uv run ruff check .`: passed. `uv run ruff format --check .`: 11 files formatted. `uv run mypy`: no issues in 8 source files. The three `uv run python tools/check_*.py` commands passed. `uv run python -m dusty --version`: `Dusty 0.0.1`. `uv run pytest`: **7 passed, 6 errors**, all reporting `PermissionError: [WinError 5] Access is denied: 'C:\\Users\\kdash\\AppData\\Local\\Temp\\pytest-of-kdash'`; it also could not write `.pytest_cache`. Earlier direct `.venv\\Scripts\\pytest.exe -q` reported 13 passed. No CI run ID exists.

## 5. Deviations from SPEC
ADR 0014 records the PM-accepted PyInstaller bootloader license exception. No other design changes were made. CI and Owner hardware acceptance remain unverified because no remote exists and the Owner has not confirmed the window.

## 6. Issues

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| ISSUE-001 | S1 | Resolved | Dependency and Git access work through approved escalation. |
| ISSUE-002 | S1 | Open | Escalated pytest cannot access its temporary directory/cache. |

## 7. Decisions needed from PM/Owner
1. Repair the pytest execution environment so the required uv command can run without permission errors. Recommend fixing directory access/identity rather than changing tests.

## 8. Actions needed from the Owner
1. Repair access to `C:\\Users\\kdash\\AppData\\Local\\Temp\\pytest-of-kdash` and the repository `.pytest_cache` for the approved execution identity. Rerun `uv run pytest` and send the full summary.
2. Configure a GitHub remote, push `m0-foundation`, open a PR, wait for Windows CI, and merge to `main` only when green.
3. Run `uv run python -m dusty` on the Owner machine and confirm that an empty window titled “Dusty” opens.

## 9. Risks for the next milestone
M1 must not start until M0 acceptance is resolved and the PM issues a new milestone brief.

## 10. Time/effort notes
Approved escalation resolved initial Git and uv access. The remaining environment error surfaced only during the final required pytest invocation.
