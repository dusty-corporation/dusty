# 0018 - Native VAD timestamp mapping correction

- Status: Accepted by PM
- Date: 2026-10-22

## Context

ISSUE-007 shows that the pinned engine interpolates segment boundaries across
removed silence and writes full JSON token offsets on the compressed timeline.
The PM directed an upstream search before patching. GitHub's release API still
lists v1.9.5 as latest stable. The compare from v1.9.5 to master contains no VAD
timestamp fix. Issue 4046 and PR 4068 remain open; the PR addresses CLI token
accessors but is not a stable release and does not settle our segment-gap case.

Sources checked on 2026-10-22:

- https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.5
- https://github.com/ggml-org/whisper.cpp/compare/v1.9.5...master
- https://github.com/ggml-org/whisper.cpp/issues/4046
- https://github.com/ggml-org/whisper.cpp/pull/4068

## Decision

Keep v1.9.5 and apply the minimal tracked patch
`native/patches/0001-vad-timestamp-mapping.patch`. Segment starts in synthetic
gaps snap to the next speech start; segment ends snap to the previous speech
end. Token accessors constrain mapped times to the enclosing text segment,
and the full JSON writer uses those accessors, including merged UTF-8 tokens.
Invalid negative token times remain invalid. Non-VAD behavior is unchanged.

CI verifies the patch hash and applies it to the exact pinned commit. Preserve
CPU dispatch and GGML_NATIVE=OFF guards. Validate the 600-second speech/silence
fixture's segment and reconstructed word times inside the known 0-10.5 and
300-310.5 second speech windows, with at most 0.5 second tolerance. Check both
boundaries of each segment and every word interval. Retain the total-word and
outside-span checks and report the measured changes.

Prepare new immutable CPU and Vulkan packages in draft engine-v2. The Owner
publishes it. Published engine-v1 is never modified. Existing FFmpeg is reused
without changes and retains its verified digest.

## Consequences

The patch stays small enough to propose upstream, but Dusty must maintain it
until an upstream stable release passes the same regression. The patched
packages need fresh hashes, import checks, JFK smoke tests, desktop startup
measurements, and timestamp regressions before publication.

## Alternatives considered

- A newer stable upstream tag: preferred by PM, but none contains the fix yet.
- An unmerged PR: insufficient evidence and incomplete segment-gap coverage.
- Reconstructing times from stderr in Dusty: rejected by PM.
- Disabling VAD or relaxing the regression: not accepted.
