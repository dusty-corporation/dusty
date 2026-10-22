# M1 benchmark evidence

The desktop is the Owner's Ryzen machine with RTX 3080 Ti. The laptop
proxy is a ThinkPad X1 Carbon with an i7-1365U (10 cores, 12 threads,
2 performance plus 8 efficiency cores), Iris Xe 96EU, and 32 GB RAM.
The PM estimates this proxy is about 20% faster than the target Surface
Laptop 5. The M1 gate uses RTF 0.8 or lower on this proxy for at least
small-level accuracy. A short smoke test on the actual Surface will
follow later and does not block M1. That real-Surface Vulkan smoke test
is required before M7. This hardware substitution limits how strongly
these results predict Surface performance.

`desktop-public/` contains the public-domain LibriVox chapter's timing
CSVs and engine JSON for both backends. `desktop-private/` contains only
timing CSVs and Markdown summaries for the Owner's real recording, with
no recording or transcript. Public JSON model paths were redacted before
commit. `thinkpad-public/` now contains ten public model rows and matching
JSON for each backend, using four threads. Its JSON model paths were also
redacted before commit. One public JSON punctuation character was
normalized to a plain hyphen to meet repository style; token and segment
text were both changed, and the WER word normalization gives the same
score. The revised
[draft benchmark kit](https://github.com/dusty-corporation/dusty/releases/tag/untagged-37ba07ac5cef03ef1fcd)
contains Quick mode and distinct public/private output names. The
original draft kit remains available for comparison.

The latest [draft kit c](https://github.com/dusty-corporation/dusty/releases/tag/untagged-e940287cf69ed749a576)
adds an optional one-model thread sweep with `-Quick -SweepModel <id>
-Threads '4,8,10'`. This is for testing the hybrid 2P+8E laptop; no
thread sweep result is part of the M1 gate table below.

On this proxy, `small-f16` took RTF 0.4048 on CPU and 0.1330 on Vulkan.
`large-v3-turbo-q8_0` took RTF 0.9428 on CPU and 0.2282 on Vulkan.
The higher-accuracy Turbo default therefore depends on working Vulkan;
the proposed CPU-only default must be a smaller model. These RTF values
include one engine process startup per benchmark run.

## WER scoring boundaries

The score uses Project Gutenberg eBook 1597 text only. The exact
reference lines and half-open audio intervals are in
`tests/fixtures/audio/bench/swineherd-scored-spans.json`:

| Span | Audio time | Reference lines | Source portion |
| --- | --- | --- | --- |
| 1 | 00:08.000 to 04:08.000 | 2-74 | Story title through the first melody introduction |
| 2 | 04:16.000 to 05:34.000 | 79-105 | After the first song through the second melody introduction |
| 3 | 05:43.000 to 10:42.000 | 109-197 | After the second song through the final song introduction |

The LibriVox spoken introduction at 00:00-00:08, songs at 04:08-04:16,
05:34-05:43, and 10:42-10:54, and closing words after 10:54 are not
scored. Their earlier reference wording came from tiny-model output.
The source-text portions were retained from Project Gutenberg. The
scorer selects Whisper text tokens by their timestamps within each
interval, scores each interval separately, then divides the total word
edit distance by the total Gutenberg word count. It normalizes NFKC,
case, punctuation, and integers consistently. This excludes every
model-derived reference span and prevents an error crossing an omitted
song boundary from matching text in another span.

The score is transcript agreement with this public-domain story. It is
not a general accuracy guarantee for private recordings or other
languages. RTF is wall time divided by full clip duration, including
engine startup. Private runs have no WER by design.
