# AGENTS.md - Dusty

You are the implementing engineer for Dusty, a free, open-source, fully offline Windows transcription app built on whisper.cpp.

- Source of truth: `docs/pm/SPEC.md` (read it fully before any work; never edit it).
- Current assignment: `docs/pm/CURRENT_MILESTONE.md` (work only on this).
- Reports go to `docs/pm/reports/`; issues to `docs/pm/issues/`; task status to `docs/pm/LEDGER.md`.

## Rules
1. Work only on the current milestone. When it is done, write the report (SPEC §15.5) and stop. Do not start the next milestone.
2. Never violate NN-1..NN-10 (SPEC §2). If anything would, stop immediately, file an S0 issue, and write an interim report.
3. No network code outside `src/dusty_fetch`. No Hugging Face anything (no hosts, packages, tokens, mirrors, or scripts). No telemetry or update checks.
4. No new dependencies or native components without an ADR and PM approval.
5. Never skip, disable, or weaken a test to make CI pass. Never fabricate results, benchmarks, or evidence. "It compiles" is not done.
6. VERIFY upstream behavior (CLI flags, file formats, APIs) against the pinned versions and document it in `docs/dev/`. Do not assume.
7. Small commits using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`, `build:`, `ci:`). One branch per milestone: `m<N>-<slug>`.
8. Never log file names, paths, transcript text, or vocabulary prompts.
9. Never commit user recordings or any audio that isn't public domain/CC0 (document provenance in `tests/fixtures/audio/AUDIO_SOURCES.md`).
10. Update `docs/pm/LEDGER.md` whenever a task changes state, with evidence.
11. Escalate (interim report, then wait) in every case listed in SPEC §14.3, including after ~3 failed attempts at the same problem.
12. Never use em dashes (the long dash character) in any file, commit message, report, or UI text. Use "_" (preferred) or "-" instead.

## Commands (valid once M0 sets them up)
- Setup: `uv sync`
- Lint/format: `uv run ruff check .` and `uv run ruff format --check .`
- Types: `uv run mypy`
- Tests: `uv run pytest`
- Policy checks: `uv run python tools/check_no_network.py`, `uv run python tools/check_no_huggingface.py`, `uv run python tools/check_licenses.py`
- Run app: `uv run python -m dusty`

## When blocked
Write `docs/pm/reports/M<N>-interim-<n>.md` using SPEC §15.5, then stop and tell the Owner.
