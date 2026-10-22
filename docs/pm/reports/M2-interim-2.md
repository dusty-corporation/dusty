# M2 Interim Report 2 - Runtime guard design conflict

## 1. Summary

Task 1 is complete: the Owner published `engine-v1`, its three asset
digests still match `native/versions.toml`, and the development fetcher
verified the engine, FFmpeg, pinned model manifest, tiny, small.en, and
VAD. The PM corrected the M2 English-only model to `small.en`, closing
ISSUE-005 without changing `models-v1`. Task 2 has a specification
conflict: SPEC 9.2 requires both a static ban on importing `socket`
anywhere in `src/dusty` and a runtime guard in that package that
replaces three `socket` functions. The tested core types, five-model trust
anchor, registry, and five exporters are committed, but the headless
pipeline and later M2 acceptance criteria are not complete.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Published pinned engine assets | met | [Published `engine-v1`](https://github.com/dusty-corporation/dusty/releases/tag/engine-v1) is a prerelease; all three GitHub asset digests match `native/versions.toml`. |
| Approved dev models and CI reuse | met | `tools/fetch_dev_binaries.py` verified tiny, small.en, and VAD from the pinned published manifest; PR #3 checks passed. |
| V1 catalog trust anchor | met as a component | `resources/models.json` contains exactly five approved models plus VAD; test checks every bundled model field and hash against the pinned release manifest. |
| Headless pipeline and integration tests | not met | Core types and exporters exist; engine, queue, privacy, self-test, and dev CLI remain. |
| Offline WFP audit, canary log, VAD, translation, coverage | not met | Later M2 tasks remain; no evidence is claimed. |

## 3. What was built

- `tools/fetch_dev_binaries.py` downloads, hashes, and safely unpacks the
  published engine archives into ignored `build/bin/`, and downloads
  only pinned tiny, small.en, and VAD model files into ignored
  `build/models/`. Existing files are reused only after hash verification.
- CI uses the same fetcher and caches downloaded files under a key
  derived from `native/versions.toml`. Native and FFmpeg source builds
  are now manual workflows, so ordinary PRs do not rebuild them.
- `src/dusty/runtime_paths.py` resolves development overrides and
  packaged binary, resource, and user-model locations.
- `resources/models.json`, `src/dusty/models/`, and tests implement the
  PM-approved model rules, release-hash comparison, and local first-use
  SHA-256 verification.
- `src/dusty/core/` defines job and transcript types. `src/dusty/export/`
  renders TXT, SRT, VTT, JSON, and DOCX with tests for paragraph gaps,
  captions, output metadata, and empty transcripts.
- [ISSUE-006](../issues/ISSUE-006-network-guard-static-check-conflict.md)
  documents the conflicting SPEC 9.2 requirements and decision options.

## 4. Test results

- `uv run python tools/fetch_dev_binaries.py` verified three engine ZIPs,
  the published `models-v1` manifest, `ggml-tiny.bin`,
  `ggml-small.en.bin`, and `ggml-silero-vad.bin` on the Owner desktop.
- `uv run ruff check .` passed; `uv run ruff format --check .` checked
  32 files; `uv run mypy` found no issues in 18 source files;
  `uv run pytest` passed 31/31 tests. All three policy checks passed.
- Draft PR [#3](https://github.com/dusty-corporation/dusty/pull/3): checks
  passed in [run 39722705154](https://github.com/dusty-corporation/dusty/actions/runs/39722705154)
  and [run 39722712734](https://github.com/dusty-corporation/dusty/actions/runs/39722712734).
  These checks cover the committed core, model, and exporter work; they
  do not establish the unimplemented M2 pipeline criteria.

## 5. Deviations from SPEC

- M2 Task 1 uses `small.en` in place of the brief's mistaken `tiny.en`
  per explicit PM decision. The current M2 brief records the correction.
- No guard design deviation has been made. The static checker still
  rejects `socket` imports in the main package.

## 6. Issues

| ID | Severity | Status | Summary |
| --- | --- | --- | --- |
| [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md) | S2 | open | Startup probe and Owner hardware runs are still M2 work. |
| [ISSUE-005](../issues/ISSUE-005-tiny-en-asset-missing.md) | S1 | resolved | PM corrected the dev English-only model to published `small.en`. |
| [ISSUE-006](../issues/ISSUE-006-network-guard-static-check-conflict.md) | S1 | open | Required runtime guard conflicts with the required static socket-import ban. |

## 7. Decisions needed from PM/Owner

1. **Runtime guard design:** approve one explicit SPEC 9.2 resolution.
   I recommend a narrowly scoped checker exception for `import socket`
   in exactly `src/dusty/privacy/network_guard.py`, with negative tests
   that keep the ban for every other main-app module, tests of all three
   monkeypatches, and the required WFP audit. Alternatively, approve a
   Python audit hook that blocks socket operations without importing
   `socket`; that changes SPEC 9.2.3's prescribed mechanism. I will not
   evade the checker with an alias or an unscanned helper.

## 8. Actions needed from the Owner

1. Send [ISSUE-006](../issues/ISSUE-006-network-guard-static-check-conflict.md)
   and decision 1 to the PM. Return the approved guard design and any
   revised static-check rule. No further Owner action is needed for
   `engine-v1` or ISSUE-005.

## 9. Risks for the next milestone

- Until the guard rule is resolved, the app cannot meet both literal
  SPEC 9.2 requirements without weakening the checker or hiding a
  network-module import.
- Engine orchestration, WFP audit, canary logging, VAD comparison,
  Persian translation fixture, and ISSUE-004 startup measurements remain
  unverified. The real Surface Vulkan smoke is still required before M7.

## 10. Time and effort notes

The published model correction was small once the PM chose `small.en`.
The guard conflict emerged when designing the privacy package against
both SPEC 9.2 clauses and the existing M0 policy checker; stopping now
avoids embedding a hidden exception in security-sensitive code.
