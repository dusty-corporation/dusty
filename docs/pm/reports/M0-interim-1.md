# M0 Interim Report - Foundation

## 1. Summary
M0 is blocked. The repository was initialized locally and a partial scaffold, license, project metadata, and minimal Qt entry point were written, but the environment cannot download the prescribed dependencies or write Git metadata. No lockfile, test results, CI run, or Owner window confirmation exists. Work stopped under SPEC §14.3.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| CI green on `main` | not met | No remote or CI run; Git cannot write commits in this sandbox. |
| Each checker fails on a deliberately bad sample | not met | Checkers and tests have not been implemented. |
| Window opens on Owner's machine | not met | Entry point exists, but PySide6 could not be installed or tested. |

## 3. What was built
Copied the existing spec byte-for-byte to `docs/pm/SPEC.md`, its prescribed path. Created the §5.2 directories, MIT `LICENSE`, README stub, changelog, third-party notice stub, `.python-version`, `pyproject.toml`, and a minimal `src/dusty/__main__.py` with an empty `Dusty` window and `--version`. Reviewed and retained the existing `AGENTS.md`. Created the ledger and ISSUE-001.

## 4. Test results
No tests ran. `uv sync --python 3.12` discovered CPython 3.12.11 and created `.venv`, then failed to fetch `pytest-qt` from PyPI after three retries with socket error 10013. `git checkout -b m0-foundation` reported `.git/HEAD.lock: Permission denied`; a subsequent `git status --short --branch` reported `No commits yet on main`.

## 5. Deviations from SPEC
The supplied spec was named `docs/pm/DUSTY_PROJECT_SPEC.md`; a byte-identical `docs/pm/SPEC.md` was created to satisfy the documented source-of-truth path. No design decisions were changed.

## 6. Issues

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| ISSUE-001 | S1 | Open | Sandbox blocks dependency resolution and Git writes. |

## 7. Decisions needed from PM/Owner
1. Provide an execution environment with PyPI access and writable `.git` metadata, or an approved complete offline wheel cache and writable `.git`. Recommend standard PyPI access for the initial lockfile and tests.

## 8. Actions needed from the Owner
1. Make `.git` writable to the implementing environment, then confirm `git -c safe.directory=C:/Users/kdash/whisper_app status --short --branch` runs without a write error during branch creation.
2. Provide PyPI connectivity or an approved offline wheel cache, then rerun `uv sync --python 3.12` and send the complete command result.
3. Configure a GitHub remote when available; the milestone brief permits finishing local work first. Send the remote URL without credentials.

## 9. Risks for the next milestone
M0 policy checks, ADRs, CI, and GUI verification remain unfinished; M1 must not start.

## 10. Time/effort notes
The source spec arrived under a different filename, and the sandbox prevented the first dependency and Git setup steps.
