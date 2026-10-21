# Current milestone: M0 — Foundation

Proceed per `docs/pm/SPEC.md` §12 M0.

Notes from the PM:
- `AGENTS.md` already exists at the repo root (provided by the PM). For M0 task 3, review it against SPEC §15.1, keep it, and only extend it if something is missing. Do not regenerate it.
- Initialize git if the repo isn't initialized yet (default branch `main`). Do the M0 work on branch `m0-foundation` and merge to `main` via PR once CI is green. If no GitHub remote is configured yet, stop after local work is complete and list the remote setup steps in the report under "Actions needed from the Owner."
- Use Python 3.12 via uv. Record every pinned version you choose in `docs/dev/dependencies.md`.
- When M0 is complete, write `docs/pm/reports/M0-report.md` and stop. Do not begin M1.
