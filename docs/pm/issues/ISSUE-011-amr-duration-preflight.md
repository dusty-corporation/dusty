# ISSUE-011 - Valid AMR rejected when duration is unknown

- Severity: S1
- Milestone: M3
- Status: Resolved

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
Actual-window add/start also verifies unknown duration displays -- and the
transcript completes. Final local suite: 106 passed; PR 39854200159 and push
39854194307 passed with 105 tests and one unavailable-Vulkan skip. Coverage
94.2%; both WFP runs recorded zero connections.

## Reproduction, expected and actual

Environment: Owner ThinkPad i7-1365U / Iris Xe / Tiny / Vulkan; independently
reproduced with the pinned engine-v2 FFmpeg on the development desktop.
Add the public jfk.amr fixture alone with a fresh output folder. Expected:
unknown duration may display --, but valid AMR transcribes. Actual before fix:
preflight raised DecoderError before FFmpeg decode was called.

Native verification: `ffprobe -v error -select_streams a:0 -show_entries
stream=codec_type,duration:format=duration -of json <public AMR>` returned
an audio stream, no duration and exit 0. A normal file/pipe-only mono 16 kHz
PCM decode returned exit 0. `ffmpeg -decoders` lists amrnb and amrwb;
`ffmpeg -demuxers` lists amr. No native component or hash pin changed.

## Resolution

Fixed in d58e629 with real coordinator and Qt app regressions. The unknown
source duration is accepted and the decoded WAV supplies the engine duration.
Owner confirmation of the corrected install is check 4 in M3-retest.md;
automated resolution does not claim that re-test already passed.
