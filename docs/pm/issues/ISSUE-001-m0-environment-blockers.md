# ISSUE-001 — M0 environment blocks dependency setup and Git commits
- Severity: S1
- Milestone: M0
- Status: Resolved
- Environment: Windows sandbox, uv 0.8.18, CPython 3.12.11 discovered by uv, Git 2.56.0

## Steps to reproduce
1. In the repository, run `uv sync --python 3.12` with a writable workspace `UV_CACHE_DIR`.
2. Run `git -c safe.directory=C:/Users/kdash/whisper_app checkout -b m0-foundation`.

## Expected
Dependencies resolve into a committed `uv.lock`, and Git creates the milestone branch and commits.

## Actual
`uv sync` cannot connect to PyPI (Windows socket error 10013). Git reports permission denied creating `.git/HEAD.lock`; `git status` still reports `main` with no commits.

## Evidence
The exact command output is summarized in the interim report. No private file names, recordings, transcript text, or prompts were involved.

## Root cause
The current execution sandbox denies outbound network access and grants read-only access to `.git`. M0 requires dependency resolution, local verification, and Git writes. Tests did not catch this because no test environment could be installed yet.

## Fix / proposed fix
The Owner initialized Git and enabled approved escalation for dependency and Git operations. `uv sync --python 3.12` resolved 60 packages and installed 59; `uv.lock` was generated. An escalated `git add` succeeded on `m0-foundation`. In this permission mode, access through approved escalation is the intended path.

## Resolution
Resolved on 2026-10-21 after the dependency installation and Git index write succeeded. M0 work resumed on `m0-foundation`.

## Regression test added
No code regression test applies to sandbox permissions. M0 verification commands now exercise the installed environment.
