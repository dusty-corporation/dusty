# M6 desktop endurance measurement, 2026-10-23

Both runs completed before the ISSUE-019 stop. This is desktop prework, not the
SPEC's laptop endurance acceptance or an accuracy benchmark.

| Model | Actual backend | Audio seconds | Wall seconds | RTF | Sampled peak tree RAM bytes | Peak work bytes | Exit | Work files/directories after |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Small, f16 | CPU | 7920.1875 | 1060.9096 | 0.133950 | 2612928512 | 253446078 | 0 | 0 / 0 |
| Large v3 Turbo, q8_0 | Vulkan | 7920.1875 | 268.3786 | 0.033885 | 2119102464 | 264681781 | 0 | 0 / 0 |

Hardware: AMD Ryzen 7 5800X3D, 34266533888 bytes system RAM, NVIDIA GeForce
RTX 3080 Ti. Each saved job is Done with no failure and the requested backend
recorded as backend_used. No CPU fallback is reported for the Vulkan case.

Command: `pwsh -NoProfile -File tools/bench/long-recording.ps1`.
The existing frozen review bundle was copied into ignored build/m6-long-recording/
before the run. The shared packaged coordinator performed decoding, model
verification, VAD, transcription and Text export. Source provenance and repetition
method are in tests/fixtures/AUDIO_SOURCES.md. Twelve repeats of the public-domain
LibriVox Swineherd fixture produce 2 h 12 min 0.1875 s of audio. Repetition tests
duration/resource behavior, not unique subject matter or transcription quality.

Both cases use eight threads, automatic language detection, VAD on and Text export.
Each case uses a separate repository-local LOCALAPPDATA profile and output folder.
Models were hash-checked against the bundled catalog before copying and verified
again by the app. The harness samples descendant process working sets and work
file sizes about once per second plus CIM overhead. RAM peaks include GUI and
children, but not GPU VRAM; shared pages may be counted in more than one process.
These are sampled peaks and can miss shorter spikes. Wall time includes startup,
verification, decode, VAD, export and cleanup; separate concurrent development
checks were running. This is not a controlled performance comparison.

Raw filtered summaries and generated audio/transcripts remain ignored under
build/m6-long-recording/. No long audio, raw benchmark JSON or transcript is
committed. No draft asset upload was started after the S0 stop. Both work trees
were independently enumerated after completion: zero files and zero directories.

Frozen dusty.exe SHA-256:
21ac632219332126ce4c2e9d12c91f1acdf4a2062334a7d4b26a7daeb42f6bd3.
Generated input WAV SHA-256:
8455996fe6970d43828600d976712ab4b37c40b22863d4fa0031f4bc47921de3.
The bundle was the existing local review build, not a newly installed final
installer. Its frozen executable hash identifies what ran; no assertion is made
that it was rebuilt from the final installer-only commits.


## M6 evidence provenance

Restored without changing measurements from reference branch
m5-packaging-spike 95dd90b98fe26e9aa5ff2d12628d21b176e5be72. This is historical
2026-10-23 prework, not a new M6 candidate run. The raw input and frozen app hashes
above identify what ran. No long recording or raw benchmark output is committed.
Physical laptop endurance and Owner offline/reboot sign-off remain separate.
