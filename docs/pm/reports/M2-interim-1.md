# M2 Interim Report 1 - Engine draft ready; model asset decision needed

## 1. Summary

The `engine-v1` release is prepared as a draft with verified CPU, Vulkan,
and FFmpeg archives, but the Owner must publish it before unauthenticated
CI can download the binaries. The published `models-v1` release lacks the
`tiny.en` model required by M2 Task 1; M1 produced `small.en` instead.
This blocks completion of the development fetch script and its CI use
until the PM chooses a model source. The M1 conditional GO and accepted V1
catalog are recorded in ADR 0016 and the ledger; the real Surface Vulkan
smoke remains an Owner-owned pre-M7 requirement.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| M1 conditional GO and V1 catalog | met | `docs/adr/0016-v1-model-catalog.md`; `PRE-M7-SURFACE` ledger row |
| Historical brief archive | met | M0 and M1 archive blobs exactly match their Git source blobs; M2 brief committed unchanged in `699f2fb` |
| Draft `engine-v1` with pinned CPU, Vulkan, and FFmpeg | met | [Draft release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-971f0687d745df6c0919); SHA-256 pins in `native/versions.toml` |
| Published model assets for M2 dev fetch | not met | `models-v1` is published but has no `tiny.en` asset or manifest entry; ISSUE-005 |
| Dev fetch script, CI cache, and headless pipeline | pending | These follow Owner publication and the model decision. No M2 pipeline result is claimed. |

## 3. What was built

- Archived the M0 brief from merge commit `3bb0f7e` and the M1 brief from
  `main` in `docs/pm/briefs/`. Their Git blob hashes match the originals.
- Added AGENTS rule 14 for generated output size, ADR 0016 for the
  PM-approved V1 catalog, and a ledger item for the required Surface smoke.
- Downloaded the successful M1 native artifacts from run 39718973902 and
  FFmpeg artifact from run 39718973892. Both runs used source commit
  `29f9ca75b05c168c6d89e14d784319c2489c38d6`.
- Repackaged only runtime executables and DLLs, plus FFmpeg `buildconf.txt`,
  into the three `engine-v1` draft assets. `docs/dev/binary-assets.md`
  records provenance, hashes, and planned dev and packaged path resolution.
- Filed [ISSUE-005](../issues/ISSUE-005-tiny-en-asset-missing.md) for the
  missing published `tiny.en` model.

## 4. Test results

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `whisper-cpu.zip` | 5,212,204 | `bb98378bfe200f503fdeff5aed8aa9e7c043a3e32f6d274b3ae4fb8ebdcb120c` |
| `whisper-vulkan.zip` | 19,351,908 | `1c6892dea290e4c16b3a1e109ac5950e018fa89ce2a27c679f638009f4921f76` |
| `minimal-ffmpeg.zip` | 4,310,689 | `d687eb1e7403b6ab9c444118c055ac99521ea34782f52538787690d1e53da40c` |

Local SHA-256 values match GitHub's uploaded asset digests. `gh release
view engine-v1 --json isDraft,isPrerelease,assets` confirmed `isDraft:true`,
`isPrerelease:true`, and all three uploaded assets. `uv run python -c
"import tomllib; p=tomllib.load(open('native/versions.toml','rb'));
print(p['engine_release']['tag'], len(p['engine_release']['whisper_cpu_zip_sha256']))"`
printed `engine-v1 64`. `git diff --check` found no whitespace errors;
the long-dash search found no matches in changed text files. No M2 CI or
headless pipeline test has run yet.

## 5. Deviations from SPEC

- The M2 brief requires an interim Owner publication gate after the engine
  draft. Work pauses here as instructed.
- The published M1 candidate set lacks M2's requested `tiny.en` model.
  No alternate or unverified model was substituted.

## 6. Issues

| ID | Severity | Status | Summary |
| --- | --- | --- | --- |
| [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md) | S2 | open | M2 startup probe and Owner hardware runs pending. |
| [ISSUE-005](../issues/ISSUE-005-tiny-en-asset-missing.md) | S1 | open | Published `models-v1` has no `tiny.en`, which Task 1 requires. |

## 7. Decisions needed from PM/Owner

1. **M2 dev model set:** the PM should choose either (A) use the existing
   published `small.en` model instead of `tiny.en` for English-only tests,
   or (B) approve producing `tiny.en` and a verified manifest update.
   I recommend A because `small.en` is already published and verified;
   tests that need a fast model can use multilingual `tiny`. B requires
   additional conversion and an Owner-only published release change.

## 8. Actions needed from the Owner

1. Review the [draft `engine-v1` release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-971f0687d745df6c0919)
   and publish it as a prerelease, without marking it latest. The brief
   assigns publishing to the Owner. Confirm when it is public so CI can
   download the pinned assets without credentials. `models-v1` is already
   published and needs no second publication.
2. Send ISSUE-005 and decision 1 to the PM. Return the PM's choice of
   `small.en` or a newly approved `tiny.en` conversion and release plan.
   The implementing engineer must not edit a published release.

## 9. Risks for the next milestone

- Until the model decision, the M2 fetch script cannot truthfully satisfy
  the specified tiny, tiny.en, and VAD download set.
- The real Surface Vulkan result remains unknown, though it does not
  block M2-M6 under the PM's conditional GO.

## 10. Time and effort notes

GitHub rejected the abbreviated release target commit with HTTP 422;
using the full M1 merge SHA succeeded. The published model asset list
revealed the M1-to-M2 naming mismatch before the fetch script or CI used
an unverified substitute.
