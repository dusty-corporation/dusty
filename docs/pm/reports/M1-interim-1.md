# M1 Interim Report 1 - Phase A engine and benchmark kit

## 1. Summary

Phase A produced portable CPU and Vulkan whisper.cpp packages, minimal LGPL FFmpeg, ten reproducible model candidates plus Silero VAD, verified engine samples, and a draft offline benchmark kit. PR #2 checks are green. The Owner independently reran the corrected Vulkan binary on the Ryzen desktop: it loaded the Haswell CPU variant and Vulkan backend, transcribed the JFK fixture, and exited 0. The public accuracy reference still needs a final human listening check; its WER must be treated as provisional. Surface and full candidate measurements are Phase B work for the Owner.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Pinned engine, FFmpeg, and model sources | met | `native/versions.toml`, `docs/dev/build-native.md` |
| Portable CPU and Vulkan builds | met on desktop; Surface pending | [Native run 39692634372](https://github.com/dusty-corporation/dusty/actions/runs/39692634372), [PR run 39694259471](https://github.com/dusty-corporation/dusty/actions/runs/39694259471), Owner retest exit 0 |
| Minimal FFmpeg decodes supported fixtures and rejects invalid input | met | [PR run 39694259434](https://github.com/dusty-corporation/dusty/actions/runs/39694259434), `docs/dev/ffmpeg-build.md` |
| Reproducible conversion, files below 2 GiB, no prohibited model hosts | met | [Model run 39691863874](https://github.com/dusty-corporation/dusty/actions/runs/39691863874), draft `models-v1`, full CI log scan with zero matches |
| Verified CLI flags, output, progress, VAD, and backend lines | met | `docs/dev/engine-cli.md`, `tests/fixtures/engine/` |
| Benchmark kit and accuracy reference | partial | Draft kit passed an extracted-folder tiny-model run; reference final listening check pending |
| Both-machine RTF and WER | pending Phase B | Owner measurements required |

## 3. What was built

- `native/build_whisper.ps1` and `native.yml`: separate CPU and Vulkan packages with `GGML_NATIVE=OFF`, backend DLL loading, nine CPU variants, printed CMake options, and import checks. [ADR 0015](../../adr/0015-native-cpu-dispatch-and-backend-layout.md) records the layout.
- `native/build_ffmpeg.sh` and `ffmpeg.yml`: static MinGW-w64 FFmpeg and FFprobe with network, GPL, and nonfree features disabled. Public JFK fixtures cover 17 formats, Unicode and long paths, and three invalid inputs.
- `models.yml` and `modelpipeline/`: ten candidate models, Silero VAD, double conversion hashes, size checks, and direct upload to draft `models-v1` with `models.json`.
- `tools/bench/`: PowerShell runner, packager, and a self-written WER summarizer. The runner warms each model, measures RTF and peak memory, and parses the actual backend and CPU variant. Private runs save metrics only.
- [Draft bench kit](https://github.com/dusty-corporation/dusty/releases/tag/untagged-722cb32b55a84963e631): `bench-kit-m1.zip`, 46,253,549 bytes, SHA-256 `19e5764c1848bfb944d930bbc614bf560b40ed788ebaa852fde88d3f8fce4da1`. It contains binaries, FFmpeg, scripts, a 660-second public reference clip, and instructions. Models are separate draft downloads.

## 4. Test results

- PR [#2](https://github.com/dusty-corporation/dusty/pull/2) is draft. Its two general CI checks, FFmpeg check, and CPU and Vulkan native checks all passed. Native run ID: 39694259471. FFmpeg run ID: 39694259434. General CI run IDs: 39694252773 and 39694259418.
- Local: Ruff check and format passed; mypy passed; pytest 15/15 passed; network, model-host, and license policy checks passed.
- Native CI artifact sizes: CPU 5,377,339 bytes; Vulkan 19,590,586 bytes. FFmpeg CI artifact: 4,415,522 bytes; extracted `ffmpeg.exe` 4,992,512 bytes and `ffprobe.exe` 4,799,488 bytes.
- Model draft assets: ten transcription models and Silero VAD. Largest candidate is `ggml-large-v3-q8_0.bin` at 1,656,538,283 bytes, below 2 GiB. The complete 5,472,012-byte model CI log had zero matches for the repository's prohibited model-host pattern.
- An extracted kit with only the tiny model ran the 660-second public chapter on desktop CPU, selected `haswell`, and generated CSV, Markdown, and public JSON. Its provisional tiny-model result was RTF 0.0373 and WER 0.0723. A separate private-mode smoke test generated metrics only. Neither is a full Phase B benchmark.

## 5. Deviations from SPEC

- The M1 brief splits work into Phase A and Owner-run Phase B, so full benchmark acceptance is deferred to Phase B.
- The model files are separate draft release downloads instead of being bundled in the kit, per the M1 brief's size constraint.
- The public benchmark source text was aligned against the recording's introduction, ending, and song sections using a timestamped tiny-model transcript. A human listening pass remains; accuracy figures are provisional until then.

## 6. Issues

| ID | Severity | Status | Summary |
| --- | --- | --- | --- |
| [ISSUE-003](../issues/ISSUE-003-native-illegal-instruction.md) | S1 | resolved | CI-native AVX-512 caused illegal instruction on Ryzen; runtime CPU dispatch build passed the Owner retest. |

## 7. Decisions needed from PM/Owner

1. Confirm or correct the public reference by listening to the included chapter while reading `audio/swineherd-reference.txt`. Recommendation: correct discrepancies before treating WER as a gate result.
2. After Phase B, the PM decides GO or NO-GO and chooses the model catalog using the complete RTF and WER table. No catalog decision is proposed yet.

## 8. Actions needed from the Owner

Download the two draft releases while signed in. On the desktop, from a folder where `gh` is authenticated:

```powershell
gh release download bench-kit-m1 --repo dusty-corporation/dusty --pattern bench-kit-m1.zip
Expand-Archive .\bench-kit-m1.zip -DestinationPath .\m1-kit
cd .\m1-kit\bench-kit-m1
gh release download models-v1 --repo dusty-corporation/dusty --pattern 'ggml-*.bin' --dir .\models
```

The kit's `README.txt` lists the ten required candidates. The download pattern also retrieves the small Silero file, which the speed benchmark ignores. Run the two public desktop tests:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend cpu -Machine desktop -Threads 8 -PublicReference
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend vulkan -Machine desktop -Threads 8 -PublicReference
```

Keep the private recording outside the kit. Convert it to 16 kHz mono PCM s16le WAV in that private folder using the README's bundled FFmpeg command. Replace the example path in these two commands with the local private WAV path; no private transcript is saved:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath 'C:\private\bench-input.wav' -Backend cpu -Machine desktop -Threads 8
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath 'C:\private\bench-input.wav' -Backend vulkan -Machine desktop -Threads 8
```

Copy the complete kit folder, including `models/`, to the Surface Laptop 5. Plug it in, select Windows power mode **Best performance**, open PowerShell in the copied kit folder, and run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend cpu -Machine surface -Threads 4 -PublicReference
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend vulkan -Machine surface -Threads 4 -PublicReference
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath 'C:\private\bench-input.wav' -Backend cpu -Machine surface -Threads 4
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath 'C:\private\bench-input.wav' -Backend vulkan -Machine surface -Threads 4
```

Send back each machine's `results/` CSV, Markdown, and `public-*.json` files, plus any errors. Do not send the private recording or its WAV. Please also report any reference transcript corrections after listening.

## 9. Risks for the next phase

- Iris Xe Vulkan has not been tested on the Surface. The script records the actual backend and stops if it cannot identify one.
- Public WER is provisional pending the human reference check. Full candidate results on both machines are required for the gate.
- Draft release assets require authenticated access and must remain drafts until the Owner chooses otherwise.

## 10. Time and effort notes

The initial CI-native CPU target followed the runner's AVX-512 capability. Correcting that required the portable dispatch layout, a new CI cache regression check, and an Owner retest. The FFmpeg cross-build needed pinned toolchain and Windows target corrections. The model pipeline processed candidates in separate jobs to stay within runner disk limits.
