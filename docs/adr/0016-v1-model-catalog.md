# 0016 - V1 model catalog and backend-dependent defaults

- Status: Accepted by PM
- Date: 2026-10-22

## Context

The PM issued a conditional GO at the M1 gate. The two-machine CPU and Vulkan
benchmark evidence and source-text-only WER scores are in
the archived two-machine benchmark evidence. A real Surface Laptop 5 Vulkan smoke test is
still required before M7. The published `models-v1` release retains all M1
candidates; the installed app needs a smaller, deliberate V1 catalog.

## Decision

The bundled `resources/models.json` trust anchor contains exactly these five
transcription models, plus Silero VAD:

| Model ID | Role |
| --- | --- |
| `large-v3-turbo-q8_0` | Recommended when the Vulkan probe succeeds on an integrated or discrete GPU. Transcribe only. |
| `small` | Recommended when only CPU is available. Multilingual and translation capable. |
| `medium` | Recommended for Translate to English, with the best observed M1 accuracy. |
| `small.en` | Optional English-only model. |
| `tiny` | Optional for weak or old machines. |

The model picker recommends `large-v3-turbo-q8_0` after a successful Vulkan
probe, otherwise `small`. Selecting Translate recommends `medium`. Turbo and
`.en` models cannot Translate. On CPU-only backends, `medium` and
`large-v3-turbo-q8_0` carry this warning: "Without a compatible graphics
processor this model will likely take longer than the recording itself."
The manifest stores conservative CPU and GPU speed classes, so selection logic
does not hard-code model names for this warning.

The bundled manifest copies hashes from the published `models-v1` manifest.
Verification against that release manifest is covered by a test. Models not in
this catalog remain in the release for possible future versions but are not
selectable in V1.

## Consequences

The default depends on a runtime Vulkan probe. CPU-only users get a smaller
translation-capable default. The app must prevent unsupported Translate
selections and show the CPU speed warning before processing. The maintainer must
confirm Vulkan on the real Surface before M7.

## Alternatives considered

`large-v3-q8_0`, `large-v3-q5_0`, Turbo f16 and q5_0, and `base` were cut
from V1. Large-v3 had inconsistent M1 WER, about 7 to 8.5% in several runs,
and slow CPU performance; `medium` covered translation with better measured
accuracy. The cut models remain published in `models-v1` and may be reviewed
again with broader evidence.

Later acceptance amendment: ADR 0025 records the accepted residual Surface
hardware risk and supersedes the earlier mandatory Surface check above.
