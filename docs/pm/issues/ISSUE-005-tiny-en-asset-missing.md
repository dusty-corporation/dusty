# ISSUE-005 - M2 requires an unpublished tiny.en model

- Severity: S1
- Milestone: M2
- Status: Open
- Environment: Published `models-v1` GitHub release and M2 Task 1

## Steps to reproduce

List the assets in the published `models-v1` release. Compare them with
M2 Task 1's requirement to download `tiny`, `tiny.en`, and VAD models.

## Expected

The published release includes a verified `tiny.en` asset and manifest
entry, so the M2 fetch script can download and verify all three models.

## Actual

The release contains `ggml-tiny.bin` and `ggml-silero-vad.bin`, but no
`ggml-tiny.en.bin` or `tiny.en` manifest entry. M1's approved candidate
list did not include `tiny.en`. Its English-only candidate was `small.en`.

## Evidence

`gh release view models-v1 --json isDraft,assets` returned `isDraft:false`
and the asset list with tiny, small.en, and VAD, but no tiny.en. The M1
model manifest and the published manifest reflect that candidate list.

## Root cause

The M2 brief introduced a model that the M1 conversion pipeline was not
asked to produce. M1 tests proved the M1 candidate set, not the later M2
download set. The mismatch appeared when Task 1 compared the published
release asset list against its required model names.

## Fix / proposed fix

PM decision required: either revise Task 1 to use the already published
`small.en` model for English-only integration tests, or approve producing
and adding `tiny.en` with a verified manifest entry. Editing a published
release is Owner-only under AGENTS rule 13; the implementing engineer
cannot make that change. No unverified substitute is acceptable.

## Regression test added

Pending PM decision. The eventual fetch script must test that every
required model is present in the pinned release manifest and verify its
downloaded SHA-256 before use.
