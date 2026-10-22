# M1 Report - Engine and model pipeline spike

## 1. Summary

The target Surface Laptop 5 was unavailable, so M1 has no direct Surface Vulkan result. The PM approved a ThinkPad X1 Carbon proxy estimated to be about 20% faster, with a stricter RTF gate of 0.8; its Vulkan results clear that gate, while CPU-only Turbo q8_0 reaches RTF 0.9428 and requires a smaller default. The engine, minimal FFmpeg, reproducible model pipeline, offline benchmark kit, and source-text-only WER scoring work, and all current PR #2 checks pass. A real-Surface Vulkan smoke test is required before M7, and the PM still owns the GO/NO-GO decision and final model catalog.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Reproducible conversion; no prohibited model-host access; assets below 2 GiB | met | [Model run 39691863874](https://github.com/dusty-corporation/dusty/actions/runs/39691863874) converted each model twice with matching hashes; log scan found zero prohibited hosts; largest file is 1,656,538,283 bytes. |
| FFmpeg decodes supported formats with networking disabled | met | [FFmpeg run 39718973892](https://github.com/dusty-corporation/dusty/actions/runs/39718973892); 17 supported format fixtures, Unicode and long paths passed; three invalid inputs failed as expected; `docs/dev/ffmpeg-build.md` records `-buildconf`. |
| CPU and Vulkan engine portability | partial | [Native run 39718973902](https://github.com/dusty-corporation/dusty/actions/runs/39718973902) passed both builds; Owner desktop retest exited 0 with Vulkan and Haswell CPU dispatch; ThinkPad public runs used both actual backends. Real Surface remains untested. |
| RTF for every candidate on two machines and both backends | met with PM-approved proxy | All ten candidates have desktop CPU/Vulkan and ThinkPad CPU/Vulkan public measurements in `docs/pm/benchmarks/m1/`; full table below. |
| Laptop accuracy and speed gate | met on proxy, Surface pending | ThinkPad `small-f16` CPU RTF 0.4048, Vulkan 0.1330; `large-v3-turbo-q8_0` Vulkan 0.2282. All are below proxy threshold 0.8; Turbo q8_0 CPU is 0.9428. WER uses only Gutenberg source spans. |
| Desktop Turbo Vulkan RTF at most 0.15 | met | Desktop public Turbo q8_0 RTF 0.0181; q5_0 0.0172; f16 0.0189. |
| Proposed model catalog | met as proposal | Backend-dependent defaults and optional models below; PM approval pending. |

Public benchmark RTF and WER are paired in each cell. Desktop used eight threads; ThinkPad used four. RTF includes one engine process startup per measured run. WER is scored over the same source-text portions of the 660-second public clip, so it is a single-clip comparison, not a general accuracy guarantee.

| Model | Desktop CPU RTF / WER | Desktop Vulkan RTF / WER | ThinkPad CPU RTF / WER | ThinkPad Vulkan RTF / WER |
| --- | ---: | ---: | ---: | ---: |
| base-f16 | 0.0398 / 0.0484 | 0.0179 / 0.0511 | 0.1672 / 0.0484 | 0.0662 / 0.0525 |
| large-v3-q5_0 | 0.7105 / 0.0825 | 0.0498 / 0.0702 | 2.0491 / 0.0825 | 0.3918 / 0.0763 |
| large-v3-q8_0 | 0.5586 / 0.0245 | 0.0617 / 0.0852 | 1.4680 / 0.0245 | 0.4933 / 0.0273 |
| large-v3-turbo-f16 | 0.3539 / 0.0225 | 0.0189 / 0.0211 | 1.5495 / 0.0225 | 0.2760 / 0.0239 |
| large-v3-turbo-q5_0 | 0.4011 / 0.0211 | 0.0172 / 0.0239 | 1.2944 / 0.0211 | 0.1865 / 0.0211 |
| large-v3-turbo-q8_0 | 0.3104 / 0.0259 | 0.0181 / 0.0245 | 0.9428 / 0.0259 | 0.2282 / 0.0123 |
| medium-f16 | 0.3373 / 0.0116 | 0.0350 / 0.0130 | 1.2370 / 0.0116 | 0.2474 / 0.0157 |
| small-f16 | 0.1285 / 0.0375 | 0.0212 / 0.0307 | 0.4048 / 0.0375 | 0.1330 / 0.0409 |
| small.en-f16 | 0.1253 / 0.0164 | 0.0212 / 0.0211 | 0.3862 / 0.0164 | 0.1365 / 0.0184 |
| tiny-f16 | 0.0245 / 0.0675 | 0.0150 / 0.0695 | 0.0875 / 0.0675 | 0.0731 / 0.0593 |

The WER reference contains only Project Gutenberg eBook 1597 lines in these half-open audio intervals: 00:08.000-04:08.000 (lines 2-74), 04:16.000-05:34.000 (79-105), and 05:43.000-10:42.000 (109-197). The LibriVox introduction, songs, and closing words are excluded because their earlier reference wording came from tiny-model output. `tests/fixtures/audio/bench/swineherd-scored-spans.json` records the exact boundaries and text. The scorer selects timestamped words within each interval, normalizes case, punctuation, Unicode, and integers, and sums edit counts across spans. No human listening pass was required by the PM. The private desktop recording produced timing and memory summaries only, with no transcript or WER; its small-f16 RTF was 0.1373 CPU and 0.0257 Vulkan, and Turbo q8_0 was 0.3301 CPU and 0.0204 Vulkan.

## 3. What was built

- Pinned native CPU and Vulkan builds with runtime CPU dispatch, GGML_NATIVE=OFF regression check, backend DLL import checks, and verified CLI behavior: `native/`, `.github/workflows/native.yml`, `docs/dev/build-native.md`, `docs/dev/engine-cli.md`, and [ADR 0015](../../adr/0015-native-cpu-dispatch-and-backend-layout.md).
- Minimal LGPL FFmpeg and FFprobe with format fixtures: `native/build_ffmpeg.sh`, `.github/workflows/ffmpeg.yml`, `tests/fixtures/audio/formats/`, and `docs/dev/ffmpeg-build.md`.
- Ten model candidates plus Silero VAD, double-conversion hash verification, and a draft `models-v1` release: `modelpipeline/`, `.github/workflows/models.yml`, and its manifest.
- Native-only benchmark kit, public/private output separation, overwrite refusal, Quick mode, an optional one-model thread sweep, and Gutenberg-only WER scoring: `tools/bench/`, `tests/fixtures/audio/bench/`, and `docs/pm/benchmarks/m1/`. The latest [draft `bench-kit-m1c`](https://github.com/dusty-corporation/dusty/releases/tag/untagged-e940287cf69ed749a576) is 46,255,430 bytes, SHA-256 `774ec9535ccb21e8392990b192cd2ca4a8eb096f357121a025ab2b4f14c2d251`; prior drafts remain intact.

## 4. Test results

- Local: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest` passed (17/17 tests). `uv run python tools/check_no_network.py`, `uv run python tools/check_no_huggingface.py`, and `uv run python tools/check_licenses.py` passed. `git diff --check` passed.
- PR [#2](https://github.com/dusty-corporation/dusty/pull/2): both general checks passed in [39718968447](https://github.com/dusty-corporation/dusty/actions/runs/39718968447) and [39718973895](https://github.com/dusty-corporation/dusty/actions/runs/39718973895); FFmpeg passed in [39718973892](https://github.com/dusty-corporation/dusty/actions/runs/39718973892); CPU and Vulkan native jobs passed in [39718973902](https://github.com/dusty-corporation/dusty/actions/runs/39718973902). Model conversion passed separately in run 39691863874.
- Benchmarks: 40 public runs with matching engine JSON, ten per machine and backend; 20 desktop private timing rows with no transcript. The Owner's corrected desktop Vulkan binary loaded `ggml-vulkan.dll` and `ggml-cpu-haswell.dll`, transcribed the public fixture, and exited 0. A local extracted-kit 4/8/10-thread sweep test produced three CPU and three Vulkan rows using a short public fixture; those rows are software test evidence, not hardware gate data.

## 5. Deviations from SPEC

- The PM substituted a ThinkPad X1 Carbon (i7-1365U, 2P+8E, Iris Xe 96EU, 32 GB) for the unavailable Surface Laptop 5 (i5-1235U, 16 GB), estimated it to be about 20% faster, and set proxy RTF at most 0.8. Real-Surface Vulkan verification is deferred to a required pre-M7 smoke test.
- The benchmark WER excludes all model-derived reference spans rather than treating those passages as ground truth. The scored spans come directly from Project Gutenberg text.
- Models are separate downloads from the draft `models-v1` release to keep the benchmark kit small, as the M1 brief requires.

## 6. Issues

| ID | Severity | Status | Summary |
| --- | --- | --- | --- |
| [ISSUE-003](../issues/ISSUE-003-native-illegal-instruction.md) | S1 | resolved | CI-native AVX-512 caused an illegal instruction on Ryzen; portable runtime dispatch passed Owner retest. |
| [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md) | S2 | open | Iris Xe appears to incur a large per-run cost; isolate startup, pipeline, model load, and inference in M2. |

## 7. Decisions needed from PM/Owner

1. **Gate:** choose GO, conditional GO, or NO-GO. I recommend conditional GO to M2: the PM-approved proxy clears RTF 0.8 with small-f16 on both backends and Turbo q8_0 on Vulkan, while desktop Turbo Vulkan clears 0.15. The condition is the required real-Surface Vulkan smoke test before M7; failure there needs a new gate review.
2. **Catalog and defaults:** I recommend `large-v3-turbo-q8_0` as **Recommended when Vulkan works** (874,188,075 bytes; proxy Vulkan RTF 0.2282, WER 0.0123) and `small-f16` as **Recommended on CPU-only** (487,601,967 bytes; proxy CPU RTF 0.4048, WER 0.0375; multilingual and translation capable). Suggested optional choices are `tiny-f16` and `base-f16` for low resource use, `small.en-f16` for English-only use, `medium-f16` for translation and higher observed WER accuracy, `large-v3-turbo-q5_0` for a smaller Turbo download, and `large-v3-q8_0` for a full Large-v3 translation option. I would leave Turbo f16 and Large-v3 q5_0 out of the initial catalog because this clip showed no clear value over their quantized alternatives. The desktop Vulkan Large-v3 q8_0 WER of 0.0852 differs sharply from CPU 0.0245 and ThinkPad Vulkan 0.0273, so keep it an advanced option pending broader accuracy checks. Turbo does not support translation; the UI must disable that task for either Turbo choice.

## 8. Actions needed from the Owner

1. Send this report to the PM for the gate and catalog decisions; keep PR #2 open for that review. The Owner alone merges after approval.
2. Before M7, run a short public-domain clip on the real Surface with the portable Vulkan engine and proposed GPU default, confirm the startup log says `using Vulkan0 backend`, and send the exit code plus RTF. If Vulkan fails or the expected small-level RTF gate does not hold, return to the PM for review.
3. Optional now: on the ThinkPad, use draft `bench-kit-m1c` and run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Machine thinkpad -Quick -SweepModel small-f16 -Threads '4,8,10' -PublicReference` from the extracted kit folder, then send only the generated public CSV and summary. This explores the 2P+8E thread count; it does not block the M1 decision.

## 9. Risks for the next milestone

- The proxy has more RAM and is estimated to be faster than the Surface. Actual Surface Vulkan support, memory behavior, and RTF remain unmeasured.
- [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md): ThinkPad Vulkan tiny and small wall times were 48.268 and 87.760 seconds, versus desktop Vulkan 9.877 and 14.004 seconds. Separate processes for short files could pay this cost repeatedly. M2 should time process start, Vulkan pipeline creation, model load, and inference separately before considering a pipeline cache or a persistent process; any ADR 0004 change needs PM approval.
- WER comes from one English public story. Differences among models and backends may change on other voices, languages, or long recordings; no private WER was recorded.

## 10. Time and effort notes

The first CI native binary targeted AVX-512 and crashed on the Owner desktop, requiring portable CPU dispatch and an independent rerun. The public reference mixed Gutenberg text with tiny-model output, so accurate scoring required timestamped source-only spans. Windows PowerShell argument binding also required the thread sweep to parse a comma-separated string explicitly, and the runner needed separate public/private filenames with overwrite protection.
