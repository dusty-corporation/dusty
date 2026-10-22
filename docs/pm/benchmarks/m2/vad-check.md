# M2 VAD check - timestamp failure

Date: 2026-10-22. Owner desktop, pinned CPU engine v1.9.5, tiny, four threads,
600-second public fixture with speech near 0 and 300 seconds.
Command: `uv run pytest tests/integration/test_vad_silence.py -s`.

Thresholds selected before the first run: at most 80 VAD-on words, and at most
five words assigned to segments starting outside `[0, 13]` and `[298, 314]`
seconds. This allows boundary tolerance without accepting speech in long silence.

| VAD | Process seconds | Segments | Total words | Words assigned outside reference spans |
|---|---:|---:|---:|---:|
| On | 4.750 | 2 | 44 | 22 |
| Off | 8.391 | 20 | 62 | 18 |

Result: FAILED. The VAD-on total-word budget passes, but its segment timeline
fails. Its segments are 0.320-213.390 s and 213.390-310.520 s, with 22 words
each. Therefore the outside-span count cannot be interpreted as a count of
hallucinated text. VAD reduces total words and elapsed processing in this run,
but output timestamps require correction before M2 acceptance.

ISSUE-007 records the verified mapping cause and the required PM decision.
Raw WAV and engine JSON remain in ignored test work directories; only these
numeric summaries are committed.
