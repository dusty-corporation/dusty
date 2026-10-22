# ISSUE-011 - Valid AMR rejected when duration is unknown

- Severity: S1
- Milestone: M3
- Status: In progress

## Root cause

Owner reproduced jfk.amr alone on the ThinkPad. Pinned FFprobe exits 0 and
finds an audio stream but omits stream/format duration. Pinned FFmpeg decodes
it successfully (exit 0). App preflight converted missing duration to float,
raised DecoderError and never reached decoding. M1 tested native decoding,
not the later Python preflight assumption; previous pipeline tests missed AMR.

## Fix and regression

Accept unknown source duration as zero (display remains --), decode normally,
then probe the known PCM WAV for engine/progress duration. No native rebuild
or pin change is needed. A real coordinator regression runs WAV and AMR with
the same stem, verifies both outputs/content and asks only on a subsequent run.
Full suite and CI pending.
