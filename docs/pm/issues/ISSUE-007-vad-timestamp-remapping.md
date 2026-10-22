# ISSUE-007 - VAD timestamp remapping spans removed silence

- Severity: S1
- Milestone: M2
- Status: In progress
- Environment: Owner desktop, pinned whisper.cpp v1.9.5 commit
  `d1be6fde11ac6e0407606b4e42fe72d34add8037`, CPU tiny, Silero VAD 6.2.3,
  four threads, public mostly-silence-10min fixture

## Steps to reproduce

Run `uv run pytest tests/integration/test_vad_silence.py -s` with the verified
development assets. The 600-second fixture contains public speech at 0 and
300 seconds. The test runs both VAD modes and retains the timestamp assertion.

## Expected

With VAD enabled, the second speech passage should have timestamps near
300-311 seconds. Captions should not cover the removed silent interval.
The test allows at most 80 total words and five words assigned outside the
speech windows `[0, 13]` and `[298, 314]` seconds.

## Actual

VAD emits two JSON segments, with offsets 0.320-213.390 and 213.390-310.520
seconds. Each contains 22 words. The second segment is therefore assigned
outside its reference speech window, and the regression fails `22 <= 5`.
This count measures misplaced segment words, not proven hallucinated words.
VAD-off completes and is retained as a comparison.

## Evidence

`docs/pm/benchmarks/m2/vad-check.md` records numeric results. The pinned source
is available locally in `build/upstream-whisper`, whose HEAD matches the pin.
Upstream references:

- [VAD mapping table and inserted silence](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/src/whisper.cpp#L6895)
- [Linear segment timestamp mapping](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/src/whisper.cpp#L8120)
- [CLI JSON segment and token timestamp writers](https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/examples/cli/cli.cpp#L740)

## Root cause

The engine concatenates detected speech and inserts short synthetic gaps.
Its segment getter maps timestamps by linear interpolation, including across
those synthetic gaps. The numeric VAD trace places the last early speech
interval at original 8.16-10.56 s, processed 5.99-8.39 s, and the next interval
at original 300.32-302.27 s, processed 8.59-10.54 s. The mapping table includes
the synthetic gap at processed 8.49-8.59 s for original 10.56-300.32 s.
The segment boundary at processed 8.56 s consequently maps to approximately
213.39 s. A start and end boundary within that gap need different treatment.

The full JSON token offsets are written directly from token data on the
compressed timeline. They are not a ready replacement for the segment offsets.
M1's short contiguous-speech checks did not exercise a long removed gap; the
required M2 silence fixture revealed it before acceptance.

## Fix / proposed fix

PM approved the native patch path after an upstream search, rejected stderr
reconstruction, and requires a new draft engine-v2 release. ADR 0018 records
the decision. No newer stable tag exists as of the 2026-10-22 API review;
related upstream PR 4068 remains open. The patch and strengthened segment/word
regression are prepared; native build and runtime verification are pending.

Recommend a PM-approved patch of the pinned native engine to map segment
starts/ends and full JSON token times correctly at VAD gaps, followed by a new
immutable engine release and hash pins. Do not replace published engine-v1.
An application-side mapper using numeric VAD boundaries is an alternative,
but adds reliance on diagnostic stderr and more reconstruction logic.
No workaround or native change has been implemented. VAD remains on by default.

## Regression test added

`tests/integration/test_vad_silence.py` retains the failing long-gap timestamp
check and runs the VAD-off comparison before asserting. No test is skipped,
marked xfail, or relaxed. PM guidance is required under SPEC 14.3.
