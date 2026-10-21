# 0005 - Audio decoding
- Status: Accepted
- Date: 2026-10-21
## Context
Common recording formats require decoding to 16 kHz mono PCM.
## Decision
Build minimal LGPL FFmpeg in CI with network protocols disabled and invoke it with a file/pipe protocol whitelist.
## Consequences
M1 must verify supported formats, build configuration, and license terms.
## Alternatives considered
Separate Python decoders; broader dependency and format uncertainty.
