# Backlog

- Bundle size: after packaging and licensing decisions, evaluate harmless unused translations and exporter helpers collected by upstream hooks; retain the verified CPU variants and required runtime behavior.

Record optional improvements, optimizations, and work outside V1 here instead of implementing them during the current milestone. Each item has one line of context. Inclusion does not approve a dependency, architecture change, or prohibited feature. Required acceptance work remains in `LEDGER.md`.

## Optimizations and optional improvements

- Remove the native VAD patch: when whisper.cpp PR 4068 or an equivalent timestamp fix reaches a stable release, verify it, upgrade the pin, rerun native/VAD regressions, and drop our patch (ADR 0018).
- Vulkan pipeline caching: defer unless future measured workloads justify it; ThinkPad probe resolved ISSUE-004 with no significant recurring overhead.
- Persistent engine per batch: no current need after ISSUE-004 resolution; any future change needs PM approval to change ADR 0004 and preserve cancellation and crash isolation.
- Exact vocabulary token counting: consider replacing the documented approximate prompt warning if an approved tokenizer becomes available.
- Additional model variants: reconsider models cut by ADR 0016 only with fresh accuracy and performance evidence and PM approval.
- CI asset-cache refresh: include the selected-model set in the immutable cache key so future dev-model additions can be cached; download hash verification already runs every time.
- Extended UI load profiling: measure very large queues and long transcript parsing during M6 hardening; M3's automated 200 ms gate uses a real public-fixture batch.

- Refresh pinned GitHub Actions during M6 maintenance: CI warns that the pinned Node 20 actions are forced onto Node 24; verify supported replacements without changing current M3 scope.

- Explicit enterprise proxy support: defer pending a PM-approved host/credential policy; the isolated downloader currently connects directly.

## After V1 (SPEC section 3.2)

- Speaker diarization: V2 feature; V1 retains only the specified interface stub.
- Arbitrary language-to-language translation: V2 feature; V1 uses Whisper's Translate to English task only.
- Transcript editor: defer editing transcripts inside the app to V2.
- Audio recording: defer recording inside the app to V2.
- Live transcription: defer streaming or real-time transcription to V2 or later.
- Code signing: evaluate after V1; V1 documents the unsigned installer experience.
- macOS and Linux builds: defer platform delivery while preserving the specified portable core.
- Fully offline installer: defer bundling model files into the installer until after V1.
- Microsoft Store and winget distribution: defer additional distribution channels until after V1.

## Not planned under current requirements

- CUDA backend: proprietary runtime redistribution conflicts with NN-5; backlog inclusion does not authorize it.
- Automatic updates or update checks: conflicts with NN-4; retain explicit manual updates.
