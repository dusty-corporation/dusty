# M0 Report - Foundation

## 1. Summary
M0's local foundation is implemented on `m0-foundation`: the locked Python environment, minimal Qt window, policy checks with negative tests, ADRs, and Windows CI workflow are in place. The Owner confirmed on 2026-10-21 that `uv run python -m dusty` opens an empty window titled “Dusty.” The PM-revised SPEC was committed unchanged, and the new rule against long dash characters is applied throughout authored repository files. M0 is **not yet accepted under SPEC §13.2** because revised branch CI has not been verified green and the PR has not been merged to `main`.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| CI green on `main` | not met | `ci.yml` is committed in `6fe71a9`; the PR is open per Owner, but no passing CI run ID or merge confirmation exists yet. |
| Each checker fails on a deliberately bad sample | met locally | `tests/unit/test_policy_checks.py` covers prohibited imports, model-host references, and a GPL-only package; `uv run pytest` passed 13 tests. |
| `uv run python -m dusty` opens the window on the Owner's machine | met | Owner confirmed an empty “Dusty” window on 2026-10-21; `uv run python -m dusty --version` printed `Dusty 0.0.1`. |

## 3. What was built
The repository has the M0 package and directory scaffold, MIT license, README, changelog, third-party notice stub, `.gitattributes`, pinned `pyproject.toml` and `uv.lock`, and dependency record. `src/dusty/__main__.py` opens the Qt shell and supports `--version`. The three checkers and their tests are in `tools/` and `tests/unit/`; `.github/workflows/ci.yml` runs the M0 gates on Windows. ADRs 0001-0013 record SPEC §4 decisions; PM-accepted ADR 0014 records the exact PyInstaller bootloader license exception. The PM's replacement `docs/pm/SPEC.md` was committed as-is in `39bf2ae`, and `AGENTS.md` now includes rule 12.

## 4. Test results
On Windows with CPython 3.12.11: `uv sync --locked --python 3.12` resolved 60 packages; `uv run ruff check .` passed; `uv run ruff format --check .` reported 11 files formatted; `uv run mypy` found no issues in 8 source files; `uv run pytest` passed 13 tests in 0.28 s. `uv run python tools/check_no_network.py`, `uv run python tools/check_no_huggingface.py`, and `uv run python tools/check_licenses.py` all passed. `git check-attr eol` confirmed LF for source, config, lockfile, and docs, and CRLF for `.ps1`, `.iss`, and `.iss.template`. The authored-file search command and output were:

```text
rg -n '[\x{2013}\x{2014}]' --hidden -g '!.git/**' -g '!.venv/**' -g '!.pytest-tmp/**' -g '!.pytest_cache/**' .
No output (exit code 1: no matches).
```

No coverage number or CI run ID is available.

## 5. Deviations from SPEC
ADR 0014 is the PM-approved narrow exception for the PyInstaller bootloader; plain GPL remains forbidden. The license checker currently audits the locked runtime Python dependency tree and recognizes the exact bootloader exception; M5 must audit all packaged native components. Later-milestone generated assets and implementation files, including the self-test audio and model manifest, are not fabricated in M0. The remote workflow is pending Owner PR and CI steps.

## 6. Issues

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| ISSUE-001 | S1 | Resolved | Git and dependency access work through approved escalation. |
| ISSUE-002 | S1 | Resolved | Owner repaired pytest directory ownership; repository temp and cache configuration now passes the standard command. |

## 7. Decisions needed from PM/Owner
1. None for local implementation. Owner must complete the CI and merge acceptance steps before M0 can be marked accepted.

## 8. Actions needed from the Owner
1. Watch the open PR's Windows CI workflow for the revised branch; send the run URL/ID and result. If green, squash-merge the PR to `main` and send the merge commit. Do not advance to M1 until the PM updates `CURRENT_MILESTONE.md`.

## 9. Risks for the next milestone
M1 will need pinned native versions, real model and self-test assets, and independent verification of upstream CLI/build behavior. The release license audit must cover native and packaged components in addition to the M0 runtime Python check.

## 10. Time/effort notes
Permission ownership of pytest's former temp/cache paths caused the only test environment failure; the Owner repaired it, and the standard test command now passes. Git and uv writes required approved escalation in this sandbox.
