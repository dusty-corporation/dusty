# M2 Interim 4 - Pinned engine VAD timestamp defect

## 1. Summary

M2 is blocked by ISSUE-007: the pinned engine assigns the second speech passage
near 300 seconds a segment start at 213.390 seconds when VAD is enabled.
The defect is confirmed in the native timestamp mapping, so timestamped outputs
cannot be accepted yet. The exporter CRLF correction and five-format goldens
are pushed as `b0f8959`; all nine exporter tests pass. The Owner's existing
desktop probe runs are accepted as desktop evidence, with only ThinkPad
results pending. Work stops under SPEC 14.3 for a PM mapping decision, rather
than waiting for the ThinkPad.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Five export formats, Unicode and caption line limits | partial | Nine tests pass, including goldens; native VAD timestamps remain incorrect |
| VAD-on/off comparison | partial | Both modes completed; long-gap timestamp regression fails |
| Desktop startup probe | met | Owner confirmed existing desktop measurements count |
| ThinkPad startup findings | not met | Owner run pending; independent work was authorized |
| Dynamic WFP network isolation | not met | Not implemented before upstream escalation |
| Persian Translate fixture | not met | Suitable licensed source candidate found; excerpt not selected |
| Coverage acceptance | partial | Last checkpoint measurement 91.6% overall; final measurement still required |

## 3. What was built

Caption writers now use CRLF within wrapped cues and produce a valid empty VTT
header. JSON gets the app version from the package. Golden files cover TXT,
SRT, VTT, JSON, and DOCX semantics with Persian text and metadata checks.
The new ten-minute VAD regression runs both modes before asserting and retains
its failure. No native patch or application-side mapping workaround was added.

## 4. Test results

- `uv run pytest tests/unit/test_exports.py`: 9 passed.
- Focused Ruff lint and format checks: passed for exporters and VAD regression.
- `uv run pytest tests/integration/test_vad_silence.py -s`: 1 failed.
  VAD on: 44 words, 2 segments, 4.750 s. VAD off: 62 words, 20 segments,
  8.391 s. The retained failure is `22 <= 5` for words assigned outside
  reference speech spans; this is not a proven hallucinated-word count.
- Native VAD mapping diagnostics confirmed that a processed boundary at
  8.56 s falls in the synthetic gap at 8.49-8.59 s, corresponding to the
  original gap at 10.56-300.32 s. Linear interpolation yields 213.39 s.
- Pinned upstream checkout HEAD matches
  `d1be6fde11ac6e0407606b4e42fe72d34add8037`.
- Numeric results are in `docs/pm/benchmarks/m2/vad-check.md`. No raw recording
  or generated engine JSON was committed. Final CI and coverage are pending;
  the new failing regression will remain enabled.

## 5. Deviations from SPEC

No workaround has been approved. SPEC 14.3 requires escalation because the
pinned native behavior needs a mapping design or native patch. VAD remains
enabled by default. ADR 0017 remains the PM-approved runtime guard decision.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-004 | S2 | Open | Desktop accepted; ThinkPad startup evidence pending |
| ISSUE-007 | S1 | Open | Native VAD timestamp interpolation assigns speech to removed silence |

## 7. Decisions needed from PM/Owner

1. Approve a timestamp correction strategy. Recommended: patch the pinned
   native engine's segment-boundary mapping and full JSON token mapping, then
   prepare a new immutable engine release with updated hash pins. Preserve
   published `engine-v1`. Alternative: reconstruct timing in Dusty from the
   numeric VAD trace and compressed token offsets, with more parser complexity
   and reliance on stderr internals. Full JSON tokens currently use compressed
   times, so using them directly is insufficient.

## 8. Actions needed from the Owner

Send ISSUE-007 and this report to the PM for the mapping decision. Continue
the already provided ThinkPad probe when convenient; no desktop rerun is needed.
No new hardware reproduction is required for ISSUE-007.

After the decision, remaining work includes the mapping fix and regression,
WFP CI, Persian translation, final integration checks, and coverage. The
[LibriVox Rubaiyat recording](https://librivox.org/the-rubaiyat-of-omar-khayyam-version-2-by-omar-khayyam/)
provides a Persian/Farsi source candidate with an explicit public-domain
statement; clip selection has not been completed.

## 9. Risks for the next milestone

Wrong segment times affect SRT, VTT, JSON, and timestamped DOCX. M2 cannot
be accepted with this regression failing. The real Surface Vulkan smoke test
remains a required Owner check before M7.

## 10. Time/effort notes

The long-gap fixture exposed behavior not exercised by M1's contiguous speech
checks. The VAD-off run and numeric source mapping were completed for diagnosis;
the test threshold was not relaxed or disabled.
