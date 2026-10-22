# M1 benchmark evidence

The desktop is the Owner's Ryzen machine with RTX 3080 Ti. The laptop
proxy is a ThinkPad X1 Carbon with an i7-1365U (10 cores, 12 threads,
2 performance plus 8 efficiency cores), Iris Xe 96EU, and 32 GB RAM.
The PM estimates this proxy is about 20% faster than the target Surface
Laptop 5. The M1 gate uses RTF 0.8 or lower on this proxy for at least
small-level accuracy. A short smoke test on the actual Surface will
follow later and does not block M1. This hardware substitution limits
how strongly these results predict Surface performance.

`desktop-public/` contains the public-domain LibriVox chapter's timing
CSVs and engine JSON for both backends. `desktop-private/` contains only
timing CSVs and Markdown summaries for the Owner's real recording, with
no recording or transcript. Public JSON model paths were redacted before
commit. ThinkPad files will be added as they arrive.

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
