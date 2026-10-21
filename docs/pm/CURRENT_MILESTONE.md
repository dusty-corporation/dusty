# Current milestone: M1 - Engine and model pipeline spike (GO / NO-GO GATE)

Proceed per `docs/pm/SPEC.md` section 12 M1. Branch: `m1-engine-spike`, created from the latest `main`. This brief adds PM decisions and clarifications on top of the spec. Where they conflict, this brief wins.

M1 runs in two phases. Phase A is your build work. Phase B is the Owner running benchmarks on real hardware. Between them you write an interim report and stop.

## Housekeeping (do first)
1. Add `desktop.ini` and `Thumbs.db` to `.gitignore`.
2. Record M0 as accepted in the ledger (PR merged, CI green).

## Phase A: build everything the benchmarks need

### A1. Pin versions (`native/versions.toml`)
- whisper.cpp: the latest stable release tag at the time you start, plus its full commit SHA. VERIFY that the tag includes Vulkan support and built-in VAD (`--vad`, `--vad-model`).
- openai/whisper: a pinned commit, used only by the model pipeline.
- Vulkan SDK version used for building, FFmpeg release tag, MinGW-w64 toolchain version.
- Record why each version was chosen in `docs/dev/build-native.md`.

### A2. Native whisper.cpp build in CI (Windows runner)
- Add a workflow (e.g. `.github/workflows/native.yml`, manual dispatch plus a path filter on `native/**`) that builds `whisper-cli.exe` and `whisper-bench.exe` (if present) for CPU and Vulkan.
- Install the pinned Vulkan SDK in CI from LunarG's official download, verified by SHA-256. No unofficial mirrors.
- The binaries must run on a clean Windows 10/11 machine with no developer tools installed. Either link the C runtime statically (`/MT`) or bundle the exact MSVC runtime DLLs the license allows. VERIFY by checking imports with `dumpbin /dependents` (or equivalent) and record the result. The only allowed external DLL is the system `vulkan-1.dll` (from the GPU driver), and only for the Vulkan build.
- Decide single vs split builds (SPEC 5.5) with evidence, and record it as ADR 0015.
- Never build or ship `whisper-server`, `stream`, `talk`, or download scripts.

### A3. FFmpeg (Linux runner, MinGW-w64 cross-compile)
- Per SPEC M1 task 2. Record the full configure line and `-buildconf` output in `docs/dev/ffmpeg-build.md`.
- `-buildconf` must show `--disable-network`, `--disable-gpl`, and `--disable-nonfree`.
- Generate the format fixtures from SPEC 11.2 (same short public-domain clip in every format, plus no-audio, zero-byte, and corrupt files). Prove the minimal build decodes every supported format and correctly fails on the bad ones. Commit the fixtures with provenance in `tests/fixtures/audio/AUDIO_SOURCES.md`.

### A4. Model pipeline (`models.yml`, Linux runner)
Per SPEC 10.5, with these constraints:
- **Disk:** a standard GitHub runner has roughly 14 GB free. Process each model in its own matrix job. Delete the `.pt` after conversion. Never hold all models on one runner.
- **Storage:** do NOT pass model files between jobs as workflow artifacts (they count against the account's Actions storage quota). Each matrix job uploads its finished files directly to the draft `models-v1` release and emits only a small JSON manifest fragment as an artifact. A final job merges the fragments into `models.json`.
- **Reproducibility:** each matrix job converts twice and fails if the hashes differ.
- **Candidates to produce:** tiny, base, small, small.en, medium, large-v3-turbo (f16, q8_0, q5_0), large-v3 (q8_0 and q5_0; f16 will exceed 2 GiB). Plus Silero VAD.
- **VAD:** VERIFY that the Silero package used for conversion contains the model weights locally and fetches nothing from any model hub at install or conversion time. If it does fetch, stop and escalate.
- Fail the job if any file is 2 GiB or larger.
- The whole pipeline log must contain no Hugging Face hosts. Run `tools/check_no_huggingface.py` over the workflow and scripts, and grep the CI log output for the forbidden strings as a pipeline step.

### A5. Verify and document the engine (`docs/dev/engine-cli.md`)
Per SPEC M1 task 4. Run the pinned `whisper-cli` locally on the Owner's desktop with a short public-domain clip and save:
- the verified flag mapping for every row of SPEC 5.4
- a real JSON output sample (`tests/fixtures/engine/sample-output.json`)
- real stderr progress samples for the parser tests
- the exact startup lines that identify the Vulkan device, or show that Vulkan is unavailable
- the prompt (vocabulary hint) token limit, if whisper.cpp documents or enforces one

### A6. Benchmark tooling and accuracy reference
- `tools/bench/run-bench.ps1` (no Python required) and `tools/bench/summarize_bench.py`, per SPEC 11.7.
- **Accuracy matters, not just speed.** Include a public-domain LibriVox recording of about 10 minutes whose source text is public domain (e.g. from Project Gutenberg), with a hand-checked reference transcript committed under `tests/fixtures/audio/bench/`. `summarize_bench.py` computes word error rate (WER) against it with a small self-written word-level edit-distance function. Do not add a WER library dependency. Normalize case, punctuation, and numbers consistently, and document the normalization.
- The Owner will also run each model on one real ~10 minute recording of their own for speed only. The script takes its path as an argument. It must never copy the file, store its name, or record anything but timings, memory, and backend.
- Each run records: model, quantization, backend, threads, audio duration, wall time, RTF, peak memory, and the backend actually used (parsed from engine output, not assumed). One warm-up run per model before measuring.

### A7. Bench kit
- A single folder (zip attached to a draft prerelease named `bench-kit-m1`, not a workflow artifact) containing the native binaries, the minimal FFmpeg, `run-bench.ps1`, the LibriVox reference clip, and a `README.txt` with exact steps.
- The models are too large to bundle. The README tells the Owner which files to download from the `models-v1` draft release and where to put them.
- The kit must run from a plain folder on a machine with no Python, no developer tools, and no admin rights.

### End of Phase A
Write `docs/pm/reports/M1-interim-1.md`. Include CI run links, artifact sizes, the bench kit's download location, and copy-paste instructions for the Owner covering both machines. Then **stop**.

## Phase B: Owner benchmarks (you wait)
The Owner runs the kit on:
- (a) the desktop (Ryzen + RTX 3080 Ti): Vulkan and CPU
- (b) the Surface Laptop 5 (i5-1235U, Iris Xe): Vulkan and CPU, plugged in, Windows power mode "Best performance"

The Owner sends back the CSV and summary files. When the PM tells you to resume, you summarize the results, write the final M1 report with the proposed model catalog (SPEC M1 acceptance), and stop. The PM makes the GO/NO-GO call and picks the catalog.

## Reporting notes
- The final report must include WER and RTF for every candidate on both machines, in one table.
- Bad news goes first. If Vulkan fails on Iris Xe, or no model reaches small-level accuracy at RTF 1.0 or better on the Surface, say so in section 1.
- New native components, workflows, or dependencies beyond what this brief names need an ADR and PM approval. New workflows for A2, A3, A4, and A7 are approved by this brief, but still record them in `docs/dev/`.
- No em or en dashes anywhere (AGENTS.md rule 12).
