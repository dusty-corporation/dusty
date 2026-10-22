# Current milestone: M2 - Headless core pipeline

Proceed per `docs/pm/SPEC.md` section 12 M2. Branch: `m2-core-pipeline`, created from the latest `main`. This brief records the PM's M1 gate decision and adds requirements on top of the spec. Where they conflict, this brief wins.

## M1 gate decision (record first)
- **Conditional GO.** Condition: a real Surface Laptop 5 Vulkan smoke test before M7. Add it to the ledger as an open pre-M7 item owned by the Owner. It does not block M2 to M6.
- Write **ADR 0016 "V1 model catalog and backend-dependent defaults"** (Status: Accepted by PM) with the catalog and rules below, citing `docs/pm/reports/M1-report.md` as evidence.

### V1 catalog
| id | Role |
|---|---|
| large-v3-turbo-q8_0 | Recommended when Vulkan works (integrated or discrete GPU). Transcribe only, no translate. |
| small | Recommended on CPU-only machines. Multilingual, translate capable. |
| medium | Recommended for Translate to English. Best observed accuracy in M1. |
| small.en | Optional. English only. |
| tiny | Optional. Weak or very old machines. |

Cut from V1: large-v3-q8_0, large-v3-q5_0, large-v3-turbo f16 and q5_0, base. Large-v3 was cut because its M1 accuracy was inconsistent (7 to 8.5% WER in several runs, likely hallucination), it is very slow without a GPU, and medium covers translation with better measured accuracy. All cut models stay in the `models-v1` release but not in the bundled manifest, so a later version can add them back.

### Rules (implement in `dusty/models`, unit tested)
1. **Default model:** if the Vulkan probe succeeded, recommend `large-v3-turbo-q8_0`. Otherwise recommend `small`.
2. **Task rules:** Turbo and `.en` models cannot Translate (SPEC 6.5). When the user selects Translate, recommend `medium`.
3. **Slow-model warning:** on a CPU-only backend, `medium` and `large-v3-turbo-q8_0` carry a warning flag ("Without a compatible graphics processor this model will likely take longer than the recording itself."). Store a conservative per-model CPU and GPU speed class in the manifest rather than hard-coding names in logic.
4. `resources/models.json` (bundled trust anchor) lists exactly the V1 catalog plus Silero VAD, with hashes copied from the published `models-v1` manifest. Add a test that every bundled entry matches the release manifest.

## Owner actions the PM has approved (Owner performs them, not you)
- **Publish `models-v1`** (it stops being a draft, not marked latest). The model files are final and verified. Published assets let CI, dev setup, and later the installer download them without credentials.
- **Publish an `engine-v1` release** that you prepare as a draft (see Task 1). The Owner publishes it after you report it ready.

## Tasks

### 1. Pinned engine binaries for dev and CI
- Prepare a draft release `engine-v1` with the CPU and Vulkan whisper-cli packages and the minimal FFmpeg package from the M1 workflows (same pinned versions). Record each zip's SHA-256 in `native/versions.toml`.
- Add `tools/fetch_dev_binaries.py`: downloads `engine-v1` assets and the `tiny`, `small.en`, and VAD models from `models-v1`, verifies every SHA-256, and unpacks into `build/bin/` and `build/models/` (gitignored). PM correction for ISSUE-005: M1 produced `small.en`, not `tiny.en`; do not modify `models-v1`. It is dev tooling, not shipped, so network access is allowed there. `check_no_network.py` must still pass because it scans only `src/dusty`.
- CI uses the same script, with caching keyed on the hashes. No per-PR rebuild of whisper.cpp or FFmpeg.
- Dusty locates binaries via `DUSTY_BIN_DIR` / `DUSTY_MODELS_DIR` in dev and tests, and via the bundled layout in packaged builds (M5). Write this resolution order in `docs/dev/`.
- Stop after preparing the draft and ask the Owner to publish both releases. Then continue.

### 2. The pipeline (SPEC 5.3 to 5.7, 7, 9)
Implement per SPEC M2: `core/`, `engine/` (FFmpeg runner, whisper-cli runner, Windows Job Objects, progress parsing from the M1 stderr samples, Vulkan probe and per-file CPU fallback), `models/`, `export/` (all five formats), `queue/` (coordinator, persistence, collision policies, restart recovery), `privacy/` (network guard, log redaction, sync-folder detection), `selftest.py`, and `python -m dusty.devcli`.
- VAD on by default, using the Silero model, via the flags verified in `docs/dev/engine-cli.md`.
- Vocabulary hints are passed as one argument, never logged. Enforce the prompt token limit you documented in M1 with a soft warning.

### 3. ISSUE-004 (Iris Xe per-run startup cost)
- Make the engine runner record per-file timings (process start to first progress, model load, encode, decode, total) using whisper-cli's own timing output, logged as numbers only.
- Add `tools/bench/startup-probe.ps1` (no Python): runs `tiny` on the short JFK fixture five times in a row, CPU and Vulkan, printing the timing breakdown per run. It shows whether the cost is a first-run driver shader compile (fast after run 1) or paid every run.
- Ask the Owner to run it on the ThinkPad and the desktop (put it in your report's Owner actions with exact commands).
- If the cost persists after the first run and exceeds 10 seconds per file, propose a fix as an ADR (e.g. Vulkan pipeline cache directory, or a batch mode that keeps one engine process alive across files) for PM approval. Do not change ADR 0004 without approval.

### 4. VAD check
- Integration test: the `mostly-silence-10min` fixture with VAD on must produce little or no hallucinated text (set and document a threshold). Run it with VAD off too and record the difference.

### 5. Translation test fixture
- The SPEC calls for a Persian clip for the Translate integration test. Use a public-domain Persian LibriVox recording if one exists (document provenance in `AUDIO_SOURCES.md`). If none is suitable, stop and escalate. Do not use any source with unclear licensing.

### 6. Network isolation and offline tests (SPEC 11.5)
- Implement the automated firewall plus WFP-audit test on the Windows CI runner against `python -m dusty --self-test` and a `--headless-batch` run. Any connection event for python.exe (when running Dusty), whisper-cli.exe, or ffmpeg.exe fails the test (S0).
- The test must run on every PR from now on.

## Rules added this milestone
- **Repository size:** do not commit large generated outputs (raw benchmark JSON, model files, binaries, long audio). Raw benchmark outputs go to release assets, with only summaries in git. Test fixtures stay small (the existing M1 fixtures are grandfathered). Add this as rule 14 in AGENTS.md.
- Coverage target per SPEC 11.1: at least 85% line coverage on `core`, `export`, `models`, `queue`, `privacy`. Report the number.
- The canary log test (SPEC 11.3) is required.
- No em or en dashes anywhere (AGENTS.md rule 12).

## Reporting
Interim report when blocked or when you need the Owner (Task 1 publish, Task 3 probe). Final `docs/pm/reports/M2-report.md` with SPEC M2 acceptance evidence, coverage, CI run IDs for the network-isolation test, the ISSUE-004 findings, and the VAD results. Then stop.
