# M2 Interim 5 - engine-v2 ready for Owner publication

## 1. Summary

Draft engine-v2 is ready for the Owner to publish; all five uploaded assets
were downloaded again and their digests match the pinned candidate hashes.
No newer stable upstream fix exists, so the approved minimal native patch is
tracked and applied by CI under ADR 0018. Both native builds and desktop
JFK, segment/word timing, and startup checks passed. Independent WFP CI passed
with zero processing connections, and local strict-package coverage exceeds
85% in every package. M2 remains incomplete: publication/activation, Persian
translation, ThinkPad findings, and remaining final acceptance work are pending.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Search upstream releases, commits and issues | met | v1.9.5 latest stable; no post-tag VAD fix; issue 4046 and PR 4068 open; ADR 0018 |
| Minimal tracked native correction | met | Patch 0001, 6399 bytes, hash pinned; no stderr reconstruction |
| Both builds, imports, CPU variants and safe CMake | met | Native run 39804070663, both jobs succeeded |
| Desktop JFK and VAD segment/word checks | met | Both backends passed; strict 0.5 s reference tolerance |
| Desktop startup regression | met | Five CPU and five actual Vulkan runs passed |
| New immutable draft and candidate hash pins | met | engine-v2 verified; engine-v1 unchanged |
| Dynamic WFP harness | met | Run 39804656510 offline job succeeded on published engine-v1; rerun after v2 activation |
| Strict-package coverage | met locally | 57 full-suite tests passed; each required package above 85% |
| Full M2 acceptance | partial | Publication, active CI, translation and remaining integration evidence pending |

## 3. What was built

- `native/patches/0001-vad-timestamp-mapping.patch`: segment boundaries snap
  to the appropriate speech boundary at removed gaps; JSON uses VAD-aware
  token accessors, constrained to the enclosing segment. Invalid timestamps
  remain invalid. CI checks the patch digest before applying it.
- Native build checks all nine CPU dispatch DLLs and prints the full GGML
  cache. CPU CI runs JFK and the ten-minute timing regression.
- The regression excludes reserved control tokens, reconstructs real words,
  and checks segment and word intervals. At least 40 words and both speech
  passages are required, alongside the retained word-budget check.
- `ci.yml` now has an independent firewall/WFP job and enforces 85% per strict
  package through the standard-library coverage runner.
- Native zips include the upstream MIT notice and only whisper-cli plus DLLs.
  FFmpeg is the unchanged pinned engine-v1 package. No model files changed.

## 4. Test results

Native build: [run 39804070663](https://github.com/dusty-corporation/dusty/actions/runs/39804070663).
Both jobs printed GGML_NATIVE=OFF, GGML_BACKEND_DL=ON and
GGML_CPU_ALL_VARIANTS=ON, passed all import checks, and packaged the nine
required variants. CPU native CI: JFK and VAD regression both passed.

Desktop commands used `DUSTY_BIN_DIR=build/engine-v2`:

- `uv run python tools/measure_coverage.py`: 57 passed; core 100.0%, export
  98.5%, models 94.4%, queue 86.4%, privacy 94.9%, overall 91.9%.
- Vulkan JFK/VAD focused suite: 2 passed. Final real-word/control-token
  checks were then rerun separately on CPU and Vulkan; both passed.
- Lint, format, mypy (39 files), and all three policy checks passed.
- Startup probe with `-BinDir build/engine-v2`: CPU 0.560-0.668 s, Vulkan
  0.534-0.644 s, all ten exit 0 with Haswell dispatch and actual Vulkan
  selection where requested. The cache was warm; no cold-start improvement
  is claimed.

The VAD-on outside-span count is **22 before, 0 after**. VAD-on still produces
44 total words, with zero word timestamp violations on either corrected
backend. VAD-off produces 62 words and 18 outside-span words. Thus the earlier
22-word anomaly was a timing error, not evidence of extra hallucinated text.
The spoken reference end is 10.5 s, not the 11 s container boundary; this
annotation error was corrected after the first Vulkan check, retaining the
0.5 s tolerance. Full numeric evidence is in
`docs/pm/benchmarks/m2/engine-v2-desktop.md`.

WFP: [run 39804656510](https://github.com/dusty-corporation/dusty/actions/runs/39804656510),
job 119914520478 passed the required blocked-connection positive control,
guarded self-test and batch, zero matching 5156/5157 events, and cleanup.
That run's general checks failed inherited import formatting, subsequently
corrected. Current PR CI runs 39807837159 and 39807825164 were still running
at handoff. They fetch active engine-v1; the VAD regression remains enabled
and is expected to reject the old timing behavior until publication/activation.
No green full-PR claim is made.

## 5. Deviations from SPEC

ADR 0018 records the PM-approved patch fallback because no newer stable fix
exists. The rejected application-side reconstruction option was not used.
`engine_release_candidate` holds verified engine-v2 hashes while active
`engine_release` stays on published engine-v1 until Owner publication.
This avoids making unauthenticated setup depend on draft assets.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-004 | S2 | Open | Desktop evidence recorded; ThinkPad baseline pending |
| ISSUE-007 | S1 | In progress | Fix validated in draft engine-v2; publication/activation pending |

## 7. Decisions needed from PM/Owner

No new technical decision is required for engine-v2. The release is ready
for the Owner-only publication action approved by the PM.

## 8. Actions needed from the Owner

Open the [verified draft engine-v2](https://github.com/dusty-corporation/dusty/releases/tag/untagged-8b5c8a94aa6dd2125a27)
and publish it as a prerelease, not latest. Leave engine-v1 unchanged. Send
confirmation when published; then promote the candidate hashes to the active
engine release, fetch publicly, and rerun PR CI including WFP on engine-v2.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| whisper-cpu.zip | 5126592 | `a8c0630616b70a00e40b9534f594cd525885cd10ef45e492aa82378ea9a325b6` |
| whisper-vulkan.zip | 19266294 | `2a4aeae6789391c7cc2fa8bbe01648e0d36c499ca1233cbdcf58d127c47fc6a0` |
| minimal-ffmpeg.zip | 4310689 | `d687eb1e7403b6ab9c444118c055ac99521ea34782f52538787690d1e53da40c` |

The draft also includes the patch and SHA256SUMS.txt. GitHub asset digests
and re-downloaded local hashes matched for all five assets.

ThinkPad results may arrive independently. No further desktop measurement is
requested. Translation research continued, but an exact Persian excerpt and
published reference pairing have not been accepted; see
`docs/dev/translation-fixture-notes.md`. No unverified fixture was committed.

## 9. Risks for the next milestone

Do not accept M2 while active CI still uses the old timestamp behavior.
Persian Translate, remaining integration scenarios, and final M2 reporting
still need completion. The real Surface Vulkan smoke test remains required
before M7. The native patch needs maintenance until an upstream stable tag
passes the same regression.

## 10. Time/effort notes

The native builds ran while WFP and coverage work progressed. The approved
publication checkpoint is now reached; work stops here as instructed. No
published release was edited, and all development remained in whisper_app.
