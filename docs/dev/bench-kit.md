# M1 benchmark kit

`tools/bench/package-kit.ps1` combines the successful native and FFmpeg
CI artifacts, `models.json`, the PowerShell runner, and public-domain
reference audio into one folder and zip. The ten candidate model files
are separate downloads from the draft `models-v1` release. The kit needs
only Windows PowerShell and the bundled executables; no Python,
administrator account, or developer tools are needed on the target PC.

The draft `bench-kit-m1` prerelease contains `bench-kit-m1.zip`:

- Size: 46,253,549 bytes.
- SHA-256: `19e5764c1848bfb944d930bbc614bf560b40ed788ebaa852fde88d3f8fce4da1`.
- Draft page: https://github.com/dusty-corporation/dusty/releases/tag/untagged-722cb32b55a84963e631 .

The Phase B revision is a separate draft prerelease,
[`bench-kit-m1b`](https://github.com/dusty-corporation/dusty/releases/tag/untagged-37ba07ac5cef03ef1fcd).
Its `bench-kit-m1b.zip` is 46,254,971 bytes with SHA-256
`16f94ad209be637ae41e1dda61b619d68e4b32a2bf2e8010ad848e64efaad1cc`.
The old draft remains intact. An extracted copy of the new zip completed
a public tiny-model CPU smoke test from a plain folder. A separate local
Quick-mode test covered four selected models and both backends using a
short public fixture and a temporary test manifest; those test results
are not Phase B measurements.

The revised runner names summaries with `public` or `private`, plus
`quick` for Quick mode, and checks planned output names before a run. It
refuses to overwrite CSV, Markdown, or public JSON. `-Quick` runs tiny,
small, Large-v3-Turbo q5_0, and Large-v3 q5_0 on CPU and Vulkan in one
call. Public JSON has the local model path redacted before it is saved.

The optional focused thread sweep is packaged in a third draft,
[`bench-kit-m1c`](https://github.com/dusty-corporation/dusty/releases/tag/untagged-e940287cf69ed749a576).
Its zip is 46,255,430 bytes with SHA-256
`774ec9535ccb21e8392990b192cd2ca4a8eb096f357121a025ab2b4f14c2d251`.
`-Quick -SweepModel small-f16 -Threads '4,8,10'` runs that one model at
three thread counts on CPU and Vulkan. Windows PowerShell's `-File`
argument binding treated the previous integer-array form `4,8,10` as
one value, so the runner now parses the comma-separated text itself.
The local sweep smoke test produced three rows per backend. These used
a short public fixture and a temporary test manifest, so they are not
Owner hardware evidence. All three draft kit releases remain drafts.

An extracted copy was tested in a plain folder with only the tiny model
copied into `models/` and a temporary one-model manifest. The bundled
CPU binary completed a public 660-second reference run, wrote CSV,
Markdown, and public JSON, and `summarize_bench.py` read the output.
This smoke test does not establish benchmark results for all models or
the Surface; those are Phase B measurements.

The script requires 16 kHz mono PCM s16le WAV. The private recording is
converted in the Owner's private folder with bundled FFmpeg, and its path
is passed as an argument. The runner never copies the recording or writes
its path, filename, or transcript to its result files. Public runs save
JSON only for the public-domain benchmark chapter. The runner parses the
actual engine backend and CPU variant from startup output and stops if it
cannot identify the backend.

`summarize_bench.py` computes word error rate with word-level Levenshtein
distance divided by reference word count. It normalizes Unicode NFKC,
case-folds, removes punctuation, and expands integer tokens from 0 to
9999 into English words. The Phase B score uses only the Project
Gutenberg source-text spans specified in
`tests/fixtures/audio/bench/swineherd-scored-spans.json`. It excludes
the spoken introduction, song sections, and outro, whose former
reference wording came from tiny-model output. The scorer selects
timestamped text tokens within each span and sums per-span edit counts.
