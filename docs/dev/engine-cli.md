# Pinned whisper-cli behavior for M1

Version: whisper.cpp `v1.9.5`, commit
`d1be6fde11ac6e0407606b4e42fe72d34add8037`. The option spellings
below were read from the CI-built `whisper-cli.exe --help` and checked
against the pinned source. The JFK run used the draft release's
`ggml-tiny.bin` converted by the M1 pipeline.

| SPEC 5.4 concept | Verified option |
| --- | --- |
| Model | `-m <path>` or `--model <path>` |
| Input | `-f <wav>` or `--file <wav>` |
| Language | `-l <code>` or `--language <code>`; `auto` is accepted |
| Translate | `-tr` or `--translate` |
| Threads | `-t <n>` or `--threads <n>` |
| Vocabulary hint | `--prompt <text>` |
| Full JSON | `-ojf -of <output-stem>` |
| Stderr progress | `-pp` or `--print-progress` |
| Disable GPU | `-ng` or `--no-gpu` |
| VAD | `--vad -vm <path>` or `--vad --vad-model <path>` |
| Limit console logging | `-np` or `--no-prints` |

The CLI help states that `--prompt` accepts at most `n_text_ctx/2`
tokens. The tiny model reported `n_text_ctx = 448`, so its limit is 224
tokens; other models can differ. Pass the complete hint as one argument
without a shell.

The real full JSON output is
`tests/fixtures/engine/sample-output.json`. Its top-level members are
`systeminfo`, `model`, `params`, `result`, and `transcription`. Each
transcription segment contains timestamps, offsets, text, and tokens.

The CPU test command combined `-pp -np -ojf`. It printed
`whisper_print_progress_callback: progress = 100%` on stderr, proving
that `-np` does not suppress progress. It also printed the public-domain
transcript on stdout. Therefore `-np` does not suppress result text;
the app runner must discard stdout and parse the JSON file. Never put
stdout or the full stderr stream in app logs, because they can contain
transcript text or user paths. A redacted progress sample is in
`tests/fixtures/engine/progress-stderr.txt`.

The first Vulkan CI binary was built with AVX-512 and exited with
`0xc000001d` on the maintainer desktop. ISSUE-003 records that regression.
The replacement from CI run 39692634372 succeeded locally. Its startup
lines identifying the desktop GPU and loaded variants were:

```text
ggml_vulkan: Found 1 Vulkan devices:
ggml_vulkan: 0 = NVIDIA GeForce RTX 3080 Ti (NVIDIA) | uma: 0 | fp16: 1 | bf16: 1 | fp4: 0 | warp size: 32 | shared memory: 49152 | int dot: 1 | matrix cores: NV_coopmat2
load_backend: loaded Vulkan backend from <kit>\bin\vulkan\ggml-vulkan.dll
load_backend: loaded CPU backend from <kit>\bin\vulkan\ggml-cpu-haswell.dll
whisper_backend_init_gpu: using Vulkan0 backend
```

The CPU package reported `load_backend: loaded CPU backend from
<kit>\bin\cpu\ggml-cpu-haswell.dll` and
`whisper_backend_init_gpu: no GPU found`. A `use gpu = 1` initialization
line alone does not prove GPU use, because even the CPU-only package
prints it before falling back to CPU. Parse the final backend line.

The pinned Silero model from the draft release was tested with
`--vad --vad-model`. The command exited 0 and reported `VAD is enabled`,
`model type: silero-16k`, and `model version: 6.2.3`.

## M2 long-gap VAD caveat

The 2026-10-22 silence-fixture check found that the pinned v1.9.5 segment
timestamp mapper linearly interpolates through synthetic VAD gaps. A boundary
between speech near 10.56 s and 300.32 s mapped to 213.39 s. Full JSON token
offsets remain on the compressed timeline, so they cannot be substituted
directly. See the timestamp patch and its regression tests for the original
failure. ADR 0018's approved native patch corrects this in the active engine-v3;
desktop CPU and Vulkan segment/word checks pass within 0.5 s. Historical unpatched engine-v1 is not a production dependency.
