# ISSUE-002 - Escalated pytest cannot access temporary directory
- Severity: S1
- Milestone: M0
- Status: Resolved
- Environment: Windows sandbox, CPython 3.12.11, pytest 8.4.2, pytest-qt 4.5.0

## Steps to reproduce
Run `uv run pytest` from the repository with approved escalation.

## Expected
The 13 M0 tests complete without permission errors.

## Actual
Test setup fails for six tests with `PermissionError: [WinError 5] Access is denied: 'C:\\Users\\kdash\\AppData\\Local\\Temp\\pytest-of-kdash'`. Pytest also warns that it cannot write `.pytest_cache`. Result: 7 passed, 6 errors.

## Evidence
The escalated command output is summarized in `docs/pm/reports/M0-interim-2.md`. A previous direct `.venv\\Scripts\\pytest.exe -q` run passed 13 tests, but the required uv command does not currently pass.

## Root cause
The Codex sandbox identity owned `%LOCALAPPDATA%\Temp\pytest-of-kdash` and the repository `.pytest_cache`, causing an identity/ACL mismatch when pytest ran under approved escalation. The Owner took ownership and removed both directories as administrator. This was an environment-level setup failure before six tests could run.

## Fix / proposed fix
The Owner repaired ownership and removed the conflicting directories. Pytest now configures `--basetemp=.pytest-tmp` and `cache_dir = ".pytest_cache"` in `pyproject.toml`; both paths are ignored by Git. The Owner ran `uv run pytest --basetemp=.pytest-tmp -p no:cacheprovider` and reported 13/13 passing. The standard `uv run pytest` command also passed: 13 tests in 0.27 s.

## Resolution
Resolved by the Owner on 2026-10-21. The Owner also confirmed that `uv run python -m dusty` opens an empty window titled “Dusty.”

## Regression test added
The standard `uv run pytest` command using the configured in-repo directories passed all 13 tests. No test was skipped or weakened.
