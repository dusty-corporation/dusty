# Contributing to Dusty

Dusty is a Windows app for private, local transcription. Read the
[development overview](docs/how-it-was-built.md), [Privacy](docs/privacy.md),
and the architecture decisions in docs/adr before proposing a change.
Public history contains one reviewed source snapshot per release. Development
reviews occur separately; please discuss a proposed change with the maintainer.

## Set up and check

Use Python 3.12 and the pinned uv environment on Windows. From the repository:

```powershell
uv sync --locked
uv run python tools/fetch_dev_binaries.py
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python tools/check_docs.py
uv run python tools/check_workflow_budget.py
uv run python tools/measure_coverage.py
uv run python tools/check_no_network.py
uv run python tools/check_no_huggingface.py
uv run python tools/check_licenses.py
```

Fetching development assets is an explicit network action. Do not run app probes
against your real profile: set LOCALAPPDATA to a fresh directory inside ignored
build/ before a manual run. Tests already isolate their app data. Never commit
models, binaries, long audio or raw benchmark outputs. See docs/dev for native,
model-conversion, downloader and packaging details. WFP/firewall tests belong on
the disposable CI runner, not a contributor's daily computer.
Start with [Build from source](docs/dev/build-from-source.md). The
[process hardening guide](docs/dev/process-hardening.md) describes the process boundaries.

## Changes and review

- Propose changes to the maintainer for development review. Describe the
  behavior, verification and remaining risks. Development uses feature branches
  and small Conventional Commits. Public main receives reviewed release snapshots
  only; do not push development branches there. Public CI gates each release.
- Keep all app wording in messages.py, in plain English. Use ordinary hyphens,
  not em or en dashes. Preserve keyboard access and light/dark contrast.
- Keep networking in the separate dusty_fetch package. The processing app must
  never import it or networking modules. Do not weaken the static, runtime,
  PE-import, license or dynamic network gates.
- New dependencies and native components need an ADR and PM approval. Retain
  license notices, exact hashes and source provenance. Follow the pinned API
  documentation; do not assume upstream behavior.
- Test actual behavior, including negative cases. Never skip a test to obtain
  green CI. Report non-essential ideas and design concerns to the maintainer.
- Fixtures must be public domain or CC0 with source and extraction boundaries
  documented in tests/fixtures/AUDIO_SOURCES.md. Never submit private recordings.
- Do not log recording names/paths, transcript text or vocabulary hints. Do not
  include sensitive local settings, state or screenshots in issue reports.

Contributions use the project's Apache-2.0 license. Confirm you have the right
to contribute the code and any data. Third-party licenses remain separate.

For a suspected privacy or data-loss defect, stop using confidential material
and give the Owner a minimal public-data reproduction. Do not publish the private
data itself. The Owner controls releases, repository settings and merges.
