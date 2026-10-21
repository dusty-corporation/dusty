# Dusty — Master Engineering Specification (V1)

> **Audience:** Codex (model: Sol, reasoning effort: Medium), acting as the sole implementing engineer.
> **Authority:** This document is the source of truth. The Project Manager (PM) issues milestone briefs and reviews your reports. The Owner (the human maintainer) relays messages between you and the PM, runs hardware tests you cannot run, and makes final product decisions.
> **Location in repo:** commit this file as `docs/pm/SPEC.md`. Do not edit it. If you believe something in it is wrong, file an issue and escalate (§14).

---

## 0. How to use this document

1. Read the whole document once before writing any code.
2. Work **only** on the milestone named in `docs/pm/CURRENT_MILESTONE.md`. Do not start the next milestone until the PM replaces that file.
3. Each milestone (§12) has tasks, deliverables and acceptance criteria. A milestone is done only when every acceptance criterion has evidence (§13.4).
4. When this document says **MUST**, it is non-negotiable. **SHOULD** means do it unless you file an ADR explaining why not. **MAY** is optional.
5. When this document says **VERIFY**, do not trust the stated detail: confirm it against the pinned upstream version and record what you found in `docs/dev/`. Upstream tools change flags and formats. Never assume.
6. Because you run at Medium reasoning effort, keep tasks small. If a task needs a large design decision this spec does not settle, **stop and escalate** rather than improvise (§14.3).

---

## 1. Product summary

**Dusty** is a free, open-source Windows desktop application that transcribes audio and video recordings to text **entirely on the user's own computer**. It is built on OpenAI's Whisper models running through the `whisper.cpp` inference engine.

**Tagline:** *Private transcription that never leaves your computer.*

**Primary user (design target):** a non-technical adult who records lectures, medical discussions, and personal conversations, mostly in English, occasionally in Persian or other languages. She uses a Surface Laptop 5 (Intel i5-1235U, 16 GB RAM, Intel Iris Xe graphics, Windows 11). She must never need a terminal, Python, or any knowledge of machine learning.

**Secondary users:** anyone on Windows 10/11 x64 who needs confidential local transcription (clinicians, researchers, lawyers, journalists, students).

**Core promise:** after installation completes, every transcription feature works with the network cable unplugged, and the software contains no code path in its processing components that can send audio, transcripts, or metadata anywhere.

**We do not claim:** HIPAA compliance, HIPAA certification, clinical accuracy, or "absolute" security. User-facing text MUST use the approved wording in §9.6.

---

## 2. Non-negotiable requirements (NN)

Violating any of these is a **Severity 0** issue (§14.1). Stop work and report immediately.

| ID | Requirement |
|----|-------------|
| NN-1 | **Offline after install.** Transcription, translation, export, queue management, settings, and app startup MUST work with no network connection. |
| NN-2 | **No network in processing components.** The GUI app, job coordinator, engine runner, decoder, exporters, and the native binaries Dusty launches during processing MUST contain no network calls. The only code allowed to touch the network is the separate downloader (`dusty-fetch`), and it runs only when the user explicitly asks for a download (or during installation). |
| NN-3 | **No Hugging Face.** No runtime, build-time, or install-time dependency on Hugging Face (huggingface.co, `huggingface_hub`, HF tokens, HF-hosted models, HF mirrors). This includes transitive dependencies and download scripts. |
| NN-4 | **No telemetry.** No analytics, crash reporting, usage statistics, update checks, or "phone home" of any kind. |
| NN-5 | **Open source only.** Dusty's code is MIT-licensed. Every redistributed component MUST be under a license on the allowlist (§10.2). No proprietary binaries are bundled (this is why CUDA is excluded). |
| NN-6 | **No sensitive data in logs.** Logs MUST never contain audio, transcript text, vocabulary hints, or source file names/paths. |
| NN-7 | **No silent data loss.** Dusty MUST never delete or overwrite a user's recordings, and MUST never overwrite an existing transcript without the user choosing to. |
| NN-8 | **Verified models.** Every model file MUST be verified by SHA-256 against the manifest bundled inside the installed app before it is used for the first time and after every download. |
| NN-9 | **Verifiable, not merely promised.** Offline operation and network isolation MUST be demonstrated by automated tests (§11.5), not just asserted. |
| NN-10 | **No fake completion.** You MUST NOT mark work complete based on "it compiles," skip or disable failing tests, fabricate benchmark numbers, or silently substitute a different library or approach. (§13) |

---

## 3. Scope

### 3.1 In scope for V1

1. Windows installer (unsigned, per-user, no admin rights needed) that installs the app, the native engine, the decoder, and the Whisper model(s) the user selects.
2. Fully offline operation after install (NN-1).
3. Single-file transcription.
4. **Batch transcription:** add multiple files and/or whole folders (optionally recursive); process sequentially; save all outputs to one chosen directory, optionally preserving subfolder structure.
5. Model choices: Tiny through Large-v3 and Large-v3-Turbo, including English-only (`.en`) variants and quantized variants decided in M1.
6. **GPU acceleration via Vulkan** (NVIDIA, AMD, Intel integrated and discrete), with automatic CPU fallback and a manual Auto/GPU/CPU setting.
7. Source language: auto-detect or user-selected from Whisper's supported languages.
8. Tasks: **Transcribe** (output in the spoken language) and **Translate to English** (Whisper's built-in task; disabled for models that do not support it, §6.5).
9. Voice activity detection (Silero VAD via whisper.cpp), on by default, to reduce hallucinations during silence.
10. Vocabulary hints (Whisper initial prompt) for names, acronyms, and medical terms.
11. Exports: TXT, SRT, VTT, JSON, DOCX (any combination).
12. Per-file and overall progress, ETA, cancel current file, cancel batch.
13. Fault tolerance: one bad file never stops the batch; queue survives app restart; retry failed files.
14. Model manager: view, download (explicit user action), verify, and delete models after install.
15. Self-test command used by the installer to prove the selected model works before reporting success.
16. Uninstaller.
17. Documentation: user guide, privacy statement, developer guide, third-party notices, SBOM.

### 3.2 Explicitly out of scope for V1 (do not build)

| Feature | Target |
|---------|--------|
| Speaker diarization | V2 (interface stub only, §5.9) |
| Arbitrary language-to-language translation (e.g., Argos) | V2 (interface stub only, §5.9) |
| In-app transcript editor | V2 |
| Recording audio inside the app | V2 |
| Live / real-time transcription | V2+ |
| CUDA backend | Not planned (proprietary runtime violates NN-5) |
| Automatic updates or update checks | Not planned (NN-4) |
| Code signing | Post-V1 |
| macOS / Linux builds | Post-V1 (keep core code portable, §5.10) |
| Fully offline installer (models bundled) | Post-V1 |
| Microsoft Store / winget | Post-V1 |

If you find yourself building anything in this table, stop.

---

## 4. Decisions already made

These are settled. Record each one as an Architecture Decision Record (ADR) in M0 (`docs/adr/`), using the template in §15.3, status "Accepted."

| ADR | Decision | Rationale |
|-----|----------|-----------|
| 0001 | **Inference engine: whisper.cpp**, pinned to a specific release tag. | Native, no PyTorch at runtime, MIT, Vulkan support, quantization, easy to audit. |
| 0002 | **GPU backend: Vulkan.** CPU fallback always available. No CUDA. | Open source, cross-vendor (works on Intel Iris Xe and NVIDIA RTX), no proprietary redistributables. |
| 0003 | **Model source: OpenAI's official `.pt` weights**, downloaded in CI from the URLs in the pinned `openai/whisper` source, verified by SHA-256, converted to GGML with whisper.cpp's own conversion script, quantized with `whisper-quantize`, and published as assets on a dedicated GitHub Release (`models-v1`). | Authoritative source, no Hugging Face, reproducible conversion anyone can re-run. |
| 0004 | **GPU/engine process model:** the GUI launches `whisper-cli.exe` as a **child process per file**. No Python bindings. Never ship `whisper-server`. | Crash isolation, easy cancellation, no HTTP server in the bundle, simpler network audit. Model reload per file (seconds) is acceptable vs. multi-minute jobs. |
| 0005 | **Audio decoding: a minimal LGPL FFmpeg** built in CI with networking disabled, invoked as a child process with `-protocol_whitelist file,pipe`. | whisper.cpp needs 16 kHz mono PCM; FFmpeg decodes every common format; LGPL build plus disabled network satisfies NN-2/NN-5. |
| 0006 | **GUI: Python 3.12 + PySide6 (Qt 6)**, managed with `uv` and a committed `uv.lock`. | Mature, native-looking, LGPL. |
| 0007 | **Packaging: PyInstaller in `--onedir` mode** (never `--onefile`). | `--onedir` keeps Qt as replaceable shared libraries (LGPL compliance) and avoids temp-dir extraction. |
| 0008 | **Installer: Inno Setup 6**, per-user install (`PrivilegesRequired=lowest`), unsigned for V1. | Free, mature, supports custom pages and SHA-256-verified downloads. |
| 0009 | **Downloader isolation:** all network code lives in a separate package and executable, `dusty-fetch`. The main `dusty` package must not import it. | Makes NN-2 structurally true and machine-checkable. |
| 0010 | **Trust anchor:** the model manifest (`models.json`) is bundled inside each app release. Dusty and the installer only accept files whose SHA-256 matches that bundled manifest. No remote manifest fetching. | No signing keys to manage; integrity rides on the app download itself. |
| 0011 | **VAD: Silero VAD**, converted from the upstream MIT-licensed Silero project in CI with whisper.cpp's conversion script and published alongside the Whisper models. | Reduces hallucination; same HF-free supply chain as the models. |
| 0012 | **License: MIT** for Dusty's own code. | Simple, compatible with all dependencies. |
| 0013 | **Platform:** Windows 11 x64 primary, Windows 10 22H2 x64 supported. Core code kept platform-neutral. | Owner's and primary user's machines. |

---

## 5. Architecture

### 5.1 Component diagram

```
┌──────────────────────────────── Dusty install dir (%LOCALAPPDATA%\Programs\Dusty) ───────────────────────────────┐
│                                                                                                                │
│  dusty.exe  (PySide6 GUI + job coordinator)          ── NO NETWORK CODE ──                                      │
│     │                                                                                                          │
│     ├── spawns ──► bin\ffmpeg.exe        (decode → 16 kHz mono WAV, network disabled at build + runtime)         │
│     ├── spawns ──► bin\cpu\whisper-cli.exe     (CPU backend)                                                   │
│     ├── spawns ──► bin\vulkan\whisper-cli.exe  (Vulkan backend, CPU fallback inside ggml)  [layout VERIFY in M1]│
│     │                                                                                                          │
│     └── spawns (only on explicit user action) ──► dusty-fetch.exe  (the ONLY networked component)              │
│                                                                                                                │
│  resources\models.json    (bundled manifest = trust anchor)                                                    │
│  resources\selftest.wav   (short public-domain clip for self-test)                                             │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────── User data (%LOCALAPPDATA%\Dusty) ────────────────┐
│  models\      verified model files (*.bin)                       │
│  work\<job>\  per-job temp WAV (deleted after every job)         │
│  state\       queue.json (restart recovery)                      │
│  settings.json                                                   │
│  logs\        dusty.log (redacted, rotating)                     │
└──────────────────────────────────────────────────────────────────┘

User outputs: wherever the user chooses (never auto-synced locations without a warning, §9.4).
```

### 5.2 Repository layout

Create exactly this structure in M0 (empty modules with docstrings are fine at first):

```
dusty/
├── AGENTS.md                      # your operating rules (§15.1), kept current
├── README.md
├── LICENSE                        # MIT
├── CHANGELOG.md                   # Keep a Changelog format
├── THIRD_PARTY_NOTICES.md         # generated in release builds (§10.4)
├── pyproject.toml
├── uv.lock
├── src/
│   ├── dusty/                     # main app — MUST NOT import networking modules or dusty_fetch
│   │   ├── __init__.py            # __version__
│   │   ├── __main__.py            # entry: GUI by default; --self-test; --version
│   │   ├── app/                   # Qt GUI (windows, dialogs, widgets, view-models)
│   │   ├── core/                  # pure data types: Job, JobStatus, Segment, Transcript, Settings
│   │   ├── engine/                # ffmpeg runner, whisper-cli runner, progress parsing, backend probe
│   │   ├── export/                # txt.py, srt.py, vtt.py, json_out.py, docx_out.py
│   │   ├── models/                # manifest loading, local registry, SHA-256 verification (no download)
│   │   ├── queue/                 # coordinator, persistence, collision handling
│   │   ├── privacy/               # network guard, log redaction, sync-folder detection
│   │   ├── platform/              # Windows-specific helpers (Job Objects, memory, paths)
│   │   ├── extensions/            # V2 interface stubs only (§5.9)
│   │   └── selftest.py
│   └── dusty_fetch/               # the ONLY package allowed to use the network
│       ├── __init__.py
│       └── __main__.py
├── native/
│   ├── versions.toml              # pinned whisper.cpp tag+commit, ffmpeg tag, Vulkan SDK version
│   ├── build_whisper.ps1
│   └── build_ffmpeg.sh            # cross-compile on Linux (MinGW-w64)
├── modelpipeline/
│   ├── model_sources.json         # generated from pinned openai/whisper; reviewed by PM
│   ├── convert_models.py
│   └── README.md
├── installer/
│   ├── dusty.iss.template
│   └── generate_iss.py            # fills model catalog + hashes from models.json
├── resources/
│   ├── models.json
│   ├── selftest.wav
│   └── icons/
├── tools/
│   ├── check_no_network.py
│   ├── check_licenses.py
│   ├── check_no_huggingface.py
│   ├── gen_notices.py
│   ├── gen_sbom.py
│   └── bench/
│       ├── run-bench.ps1          # runs without Python (native binaries only)
│       └── summarize_bench.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── offline/
│   ├── fixtures/
│   │   ├── audio/
│   │   └── AUDIO_SOURCES.md       # provenance + license for every fixture
│   └── conftest.py
├── docs/
│   ├── user/                      # user guide, FAQ, troubleshooting
│   ├── dev/                       # build guide, engine-cli.md, ffmpeg-build.md, release.md
│   ├── privacy.md
│   ├── adr/
│   └── pm/
│       ├── SPEC.md                # this file
│       ├── CURRENT_MILESTONE.md   # written by PM
│       ├── LEDGER.md              # task ledger (§15.2)
│       ├── issues/                # ISSUE-NNN.md (§15.4)
│       ├── reports/               # milestone reports (§15.5)
│       └── benchmarks/
└── .github/
    └── workflows/
        ├── ci.yml
        ├── models.yml
        └── release.yml
```

### 5.3 Processing pipeline (per file)

```
Job(Queued)
  → Preflight     : file exists, readable, size > 0, free disk ≥ 2× estimated WAV size, model verified
  → Decoding      : ffmpeg → %LOCALAPPDATA%\Dusty\work\<job-uuid>\audio.wav  (16 kHz, mono, s16le)
  → Transcribing  : whisper-cli on audio.wav → work\<job-uuid>\raw.json
  → Parsing       : raw.json → Transcript (list of Segment)
  → Exporting     : each selected format written atomically to the output dir
  → Cleanup       : delete work\<job-uuid>\ (ALWAYS: on success, failure, and cancel)
Job(Done | Failed(code) | Cancelled | Skipped)
```

### 5.4 Engine invocation (VERIFY every flag in M1)

**FFmpeg (decode):**
```
ffmpeg.exe -nostdin -hide_banner -loglevel error -protocol_whitelist file,pipe
           -i "<input>" -vn -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le -f wav "<work>\audio.wav"
```
- Get duration first with a probe call (or the bundled `ffprobe.exe` if built). Record it for progress/ETA.
- If the input has no audio stream → `Failed(NO_AUDIO)`.

**whisper-cli (transcribe):** build the argument list from these concepts and confirm the exact flag spellings against `whisper-cli --help` for the pinned version. Record the verified mapping in `docs/dev/engine-cli.md`.

| Concept | Expected flag (VERIFY) |
|---------|------------------------|
| model file | `-m <path>` |
| input file | `-f <wav>` |
| language (`auto` or code) | `-l <code>` |
| translate to English | `-tr` |
| threads | `-t <n>` |
| initial prompt / vocab hints | `--prompt "<text>"` |
| full JSON output | `-ojf` (or `-oj`) with `-of <path-without-ext>` |
| progress on stderr | `-pp` |
| disable GPU | `-ng` / `--no-gpu` |
| VAD on + model | `--vad --vad-model <path>` |
| suppress console transcript print | `-np` (no prints) — confirm it doesn't suppress progress |

- Dusty generates **all** user-facing outputs itself from the parsed JSON (§7). Do not use whisper-cli's own TXT/SRT/VTT writers, so formatting is identical across backends.
- The vocabulary-hint text is passed as a single argument (no shell). Never pass it through a shell or log it.

**Process control:**
- Every child process MUST be assigned to a Windows **Job Object** with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (via `ctypes` in `platform/`), so children die if Dusty crashes or is killed.
- Spawn with `CREATE_NO_WINDOW`, no shell, explicit argument lists.
- Cancellation = terminate the job object's processes, then run Cleanup.

### 5.5 Backend selection (CPU / Vulkan)

- Setting: **Auto** (default) / **GPU** / **CPU**.
- **Probe:** on first launch and when the setting changes, run the Vulkan engine with a probe (VERIFY in M1 how whisper-cli reports available Vulkan devices, e.g., via its startup log or a tiny self-test). Cache the result (device name, OK/failed) in settings with the engine version. Re-probe if the engine version or GPU driver signature changes.
- **Auto:** use Vulkan if the probe succeeded, otherwise CPU.
- **Runtime fallback:** if a Vulkan run fails with a backend/device error, automatically retry **that file once on CPU**, mark the job "Completed on CPU (GPU failed)," and show a non-blocking notice. Do not switch the setting permanently.
- **Threads:** default = physical core count, capped at 8. Advanced setting allows 1–logical cores.
- **Vulkan loader:** `vulkan-1.dll` comes from the GPU driver. Never bundle it. If it is absent, Auto → CPU.
- M1 decides whether one Vulkan-enabled build (which can also run on CPU) suffices, or whether separate CPU and Vulkan builds are needed (e.g., for CPU instruction-set dispatch via ggml's `GGML_BACKEND_DL` / `GGML_CPU_ALL_VARIANTS` options — VERIFY these exist and work on Windows for the pinned version).

### 5.6 Data model (`dusty/core`)

```python
class JobStatus(Enum): QUEUED, PREFLIGHT, DECODING, TRANSCRIBING, EXPORTING, DONE, FAILED, CANCELLED, SKIPPED

class FailureCode(Enum):
    NOT_FOUND, UNREADABLE, EMPTY_FILE, NO_AUDIO, DECODE_ERROR, UNSUPPORTED_FORMAT,
    DISK_FULL, MODEL_MISSING, MODEL_CORRUPT, ENGINE_ERROR, ENGINE_CRASH, GPU_ERROR,
    OUTPUT_UNWRITABLE, OUTPUT_EXISTS_SKIPPED, INTERNAL_ERROR

@dataclass(frozen=True)
class Segment: index: int; start: float; end: float; text: str   # seconds

@dataclass(frozen=True)
class Transcript:
    segments: tuple[Segment, ...]
    language: str            # detected or chosen
    task: Literal["transcribe", "translate"]
    model_id: str
    backend: Literal["cpu", "vulkan"]
    duration_sec: float

@dataclass
class Job:
    id: UUID
    source: Path             # NEVER logged
    relative_dir: Path | None  # for preserve-structure output
    status: JobStatus
    failure: FailureCode | None
    progress: float          # 0..1
    outputs: list[Path]      # NEVER logged
```

Every user-visible failure code maps to a plain-language message and a suggested action (§8.6).

### 5.7 Persistence

- `settings.json`: user preferences (model, language, task, formats, output dir, collision policy, backend, threads, VAD, vocabulary hints, window geometry). Write atomically.
- `state/queue.json`: the current batch for restart recovery. It contains file paths (necessary for resume). It lives in the user-only `%LOCALAPPDATA%`. It MUST be deleted when a batch finishes and the user dismisses it, and there MUST be a "Clear history" action. Document this in `docs/privacy.md`.
- Schema-versioned; unknown/corrupt files are renamed to `*.corrupt-<timestamp>` and the app continues with defaults (never crash on bad state).

### 5.8 Model storage and manifest

`resources/models.json` (bundled; generated by the model pipeline; schema-versioned):

```json
{
  "schema_version": 1,
  "release_tag": "models-v1",
  "models": [
    {
      "id": "large-v3-turbo",
      "display_name": "Large v3 Turbo",
      "description": "Near top accuracy, much faster than Large. Best choice with a GPU.",
      "file_name": "ggml-large-v3-turbo.bin",
      "size_bytes": 0,
      "sha256": "<hex>",
      "url": "https://github.com/<owner>/dusty/releases/download/models-v1/ggml-large-v3-turbo.bin",
      "multilingual": true,
      "supports_translate": false,
      "english_only": false,
      "quantization": "f16",
      "source": {
        "openai_pt_url": "<from pinned openai/whisper>",
        "openai_pt_sha256": "<hex>",
        "whisper_cpp_commit": "<sha>",
        "converter": "models/convert-pt-to-ggml.py"
      },
      "recommended_min_ram_gb": 8
    }
  ],
  "vad": [ { "id": "silero-vad", "file_name": "...", "sha256": "...", "url": "...", "source": { } } ]
}
```

- Models are stored in `%LOCALAPPDATA%\Dusty\models\`. App upgrades and reinstalls MUST NOT delete or re-download models that still verify.
- A model is "installed" only if its file exists and its SHA-256 matches. Verification runs after download and on first use per app session (cache by size+mtime afterwards). Corrupt → offer re-download, never use.
- No file in any release may exceed **2 GiB** (GitHub Release asset limit). The model pipeline MUST fail if one does. Any model that exceeds it ships quantized (M1 decides q8_0 vs q5_0 for Large-v3).

### 5.9 V2 extension stubs (interfaces only)

In `dusty/extensions/`, define abstract interfaces with docstrings and **no implementation and no dependencies**:

```python
class Diarizer(Protocol):
    def diarize(self, wav_path: Path) -> list[SpeakerTurn]: ...

class TextTranslator(Protocol):
    def available_pairs(self) -> list[tuple[str, str]]: ...
    def translate(self, transcript: Transcript, target_lang: str) -> Transcript: ...
```

The pipeline should have a clearly marked hook point after Parsing where these could run. Do not add any packages for them.

### 5.10 Portability rule

`core/`, `export/`, `models/`, and `queue/` MUST be platform-neutral (pathlib, no Windows APIs). Windows-specific code lives only in `platform/` behind small functions.

---

## 6. Functional requirements

### 6.1 Adding files

- **Add files…** (multi-select), **Add folder…** (with "Include subfolders" checkbox), and drag-and-drop of files and folders onto the window.
- Supported extensions (final list confirmed in M1 against the minimal FFmpeg build): `mp3 m4a aac wav flac ogg oga opus wma webm mp4 m4v mov mkv avi 3gp amr`.
- Unsupported files found in folders are ignored and counted ("12 files added, 3 unsupported files skipped").
- Duplicate detection: the same resolved path cannot be queued twice.
- Before starting, the queue is editable: remove, reorder (drag or up/down), clear.

### 6.2 Settings applied to a batch

- Model (installed models only; link to Model Manager).
- Language: Auto-detect + full Whisper language list (display names in English, sorted, with the most common at the top: English, Persian, Spanish, French, German, Arabic, Chinese).
- Task: Transcribe / Translate to English.
- Output formats: TXT, SRT, VTT, JSON, DOCX (checkboxes; default TXT + DOCX).
- Output location: **Choose a folder** (default; prompt on first run and remember) or **Same folder as each recording**.
- "Keep folder structure" (when input came from a folder).
- Collision policy: **Ask** (default; one dialog per batch with "apply to all") / Skip / Overwrite / Keep both (adds ` (1)`, ` (2)`…).
- Vocabulary hints: multi-line text field with helper text ("Names, medications, acronyms, separated by commas"). Persisted. Show a soft warning above ~200 tokens (Whisper's prompt window is limited; VERIFY the limit in whisper.cpp).
- Advanced (collapsed): Processing device (Auto/GPU/CPU), threads, VAD on/off.

### 6.3 Running a batch

- **Start** processes files one at a time in queue order.
- Per-file row: name, duration, status, progress bar, elapsed, and a result link ("Open folder").
- Overall: "File 3 of 12," overall progress bar, ETA (based on measured real-time factor after the first 30 s of processing; show "Estimating…" before that).
- **Cancel current file** and **Cancel all**. Cancelled files are marked Cancelled; partial outputs are never left behind (atomic writes, §7.1).
- Closing the window during a batch asks for confirmation; on confirm, cancel cleanly and persist state.
- When done: summary dialog (Done / Failed / Skipped counts), **Retry failed**, **Open output folder**.
- Windows sleep: while a batch runs, request that the system not sleep (`SetThreadExecutionState`), and release it afterwards.

### 6.4 Restart recovery

- On launch, if `state/queue.json` has unfinished jobs: "You have an unfinished batch (N files remaining). Resume / Discard."
- Jobs that were mid-processing restart from the beginning. Jobs whose outputs all exist and were recorded Done are skipped.

### 6.5 Model rules

- `.en` models: English only. When selected, the language control is fixed to English and Translate is disabled.
- **Large-v3-Turbo does not support translation.** When selected, Translate is disabled with a tooltip ("Turbo can transcribe many languages but can't translate. Choose Medium or Large v3 to translate to English.").
- If the selected task needs a model that isn't installed, say so and link to Model Manager.

### 6.6 Model Manager

- Lists every manifest model: name, description, size, status (Installed / Not installed / Corrupt / Downloading).
- **Download:** shows a confirmation that clearly states it will connect to `github.com` to download N MB, then launches `dusty-fetch` and shows its progress. Resumable. Verifies SHA-256. Writes to a `.part` file, renamed only after verification.
- **Delete** (with confirmation; cannot delete the last installed model while it's selected without choosing another).
- **Verify all** (re-hash).
- Shows free disk space.

### 6.7 Self-test (`dusty.exe --self-test --model <id>`)

- Runs fully offline: verify the model hash, decode `resources/selftest.wav` with FFmpeg, transcribe it with the chosen model on the chosen backend (and on CPU), check that the output contains expected keywords (case-insensitive, fuzzy). Exit code 0 on success, non-zero with a reason code otherwise. Writes no user-visible files except a redacted log line.
- Used by the installer (§10.5) and available in the GUI under Help → "Run self-test."

### 6.8 First-run experience

1. Welcome screen (one screen): what Dusty does, the privacy promise, the medical disclaimer (§9.6).
2. Choose the default output folder.
3. Done. The main window opens.

---

## 7. Export formats

### 7.1 General rules

- File name: `<stem>.<ext>` for Transcribe, `<stem>.en.<ext>` for Translate. Use the collision policy (§6.2) when the target exists.
- **Atomic writes:** write to `<target>.dusty-tmp` in the same directory, flush, `os.replace` to the final name. Never leave partial files.
- UTF-8 (no BOM) for text formats. Windows line endings (`\r\n`) for TXT/SRT/VTT.
- Text cleanup: trim whitespace, collapse multiple spaces, drop empty segments. Do not alter wording.
- No hidden metadata: no source paths, user names, or machine names in any output.

### 7.2 TXT
Plain transcript. Consecutive segments join with a space; start a new paragraph when the gap between segments is ≥ 2.0 s.

### 7.3 SRT
Standard SubRip: 1-based cue numbers, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, max 42 characters per line, max 2 lines per cue; split long segments on word boundaries, distributing time proportionally to character count. Blank line between cues.

### 7.4 VTT
`WEBVTT` header, blank line, then cues with `HH:MM:SS.mmm`. Same line rules as SRT.

### 7.5 JSON (Dusty schema, versioned)
```json
{
  "schema": "dusty.transcript", "schema_version": 1,
  "app_version": "1.0.0", "model_id": "large-v3-turbo", "backend": "vulkan",
  "task": "transcribe", "language": "en", "duration_sec": 3612.4,
  "source_file_name": "Lecture_01.mp4",
  "created_utc": "2026-10-21T21:40:00Z",
  "segments": [ { "index": 0, "start": 0.0, "end": 4.5, "text": "..." } ]
}
```
`source_file_name` is the base name only, never the full path.

### 7.6 DOCX (python-docx)
- Title paragraph: the file stem. Subtitle line: date, duration, model, language.
- Body: paragraphs grouped as in TXT; option (setting, default on) to prefix each paragraph with `[HH:MM:SS]`.
- Core properties: set `author`, `last_modified_by`, `comments`, etc. to empty strings (python-docx defaults to "python-docx" — override it).
- Calibri 11 pt body, readable spacing.

---

## 8. User interface requirements

### 8.1 Principles
Written for a non-technical user. Plain language, no jargon, large click targets, nothing destructive without confirmation, every error explains what to do next.

### 8.2 Main window layout (single window)
- **Top:** "Add files", "Add folder", drag-and-drop hint area (when the queue is empty).
- **Center:** queue table.
- **Right or bottom panel:** settings (§6.2) with Advanced collapsed.
- **Bottom bar:** overall progress, ETA, Start / Cancel buttons, output folder link.
- **Menu:** File (Add files, Add folder, Exit), Tools (Model Manager, Settings, Clear history), Help (User guide [opens local HTML], Privacy, Run self-test, About).

### 8.3 Visual
Follow the Windows light/dark theme. Base font ≥ 10 pt, scalable with Windows display scaling (test at 100%, 150%, 200%). App icon in `resources/icons/` (simple, original; no third-party marks).

### 8.4 Sync-folder warning
If the chosen output folder (or "same folder as recording" for a file) is inside OneDrive (`%OneDrive%`, `%OneDriveConsumer%`, `%OneDriveCommercial%`), Dropbox (path from `%LOCALAPPDATA%\Dropbox\info.json` or `%APPDATA%\Dropbox\info.json`), or Google Drive for desktop (VERIFY detection approach), show a one-time-per-folder warning: "This folder syncs to the cloud. Transcripts saved here will be uploaded by <service>. Continue / Choose another folder." Never block the user.

### 8.5 Accessibility
Keyboard navigable, sensible tab order, accessible names on controls, no information conveyed by color alone.

### 8.6 Error messages (examples; full table in `app/messages.py`)
| Code | Message |
|------|---------|
| NO_AUDIO | "This file doesn't contain any audio we can transcribe." |
| UNSUPPORTED_FORMAT | "Dusty can't read this file type. Try converting it to MP3 or WAV." |
| DISK_FULL | "Not enough free disk space. Free up at least {n} GB and retry." |
| MODEL_CORRUPT | "The {model} model file is damaged. Open Model Manager to re-download it." |
| GPU_ERROR | "The graphics card couldn't process this file, so Dusty used the processor instead. It may be slower." |
| ENGINE_CRASH | "Transcription stopped unexpectedly. Click Retry. If it keeps happening, switch Processing device to CPU in Advanced settings." |

---

## 9. Security and privacy specification

### 9.1 Threat model (V1)
**Protect against:** accidental network transmission of audio, transcripts, prompts, or metadata; sensitive data leaking into logs, temp files, or document metadata; silent overwrites or deletion of user data; tampered or corrupted model downloads; supply-chain surprises (unexpected dependencies, Hugging Face fallbacks).
**Out of scope:** an attacker with access to the user's Windows account or admin rights; disk forensics on deleted temp files (no secure-wipe claims); malicious GitHub account takeover (mitigated only by hash pinning in each app release).

### 9.2 Network isolation (enforces NN-2)
1. **Static check** (`tools/check_no_network.py`, runs in CI): AST-scan `src/dusty/**` and fail if any module imports `socket`, `ssl`, `http`, `urllib`, `ftplib`, `smtplib`, `requests`, `httpx`, `aiohttp`, `websocket*`, `PySide6.QtNetwork`, `PySide6.QtWebEngine*`, or `dusty_fetch`. Only `src/dusty_fetch/**` may import networking modules.
2. **Bundle check:** the PyInstaller build for `dusty.exe` MUST exclude `PySide6.QtNetwork`, `QtWebEngine*`, and other unneeded Qt modules; CI verifies the corresponding DLLs (`Qt6Network.dll`, `Qt6WebEngine*.dll`) are absent from the `dusty` bundle.
3. **Runtime guard:** at the very start of `dusty.exe` (and `--self-test`), replace `socket.socket`, `socket.create_connection`, and `socket.getaddrinfo` with functions that raise `NetworkBlockedError` and write a redacted log entry. This is defense in depth; it MUST be covered by a unit test.
4. **Native binaries:** ship only `whisper-cli.exe` (plus its DLLs) from whisper.cpp — never `whisper-server`, `talk`, `stream`, or download scripts. FFmpeg is built with `--disable-network` (VERIFY in the configure output) and always invoked with `-protocol_whitelist file,pipe`.
5. **Dynamic test:** §11.5.

### 9.3 Logging (enforces NN-6)
- Location: `%LOCALAPPDATA%\Dusty\logs\dusty.log`, rotating 5 × 1 MB.
- Allowed fields: timestamps, app/engine versions, job UUID, file extension, file size bucket, duration, model id, backend, status, failure code, timings, real-time factor.
- **Forbidden:** file names, paths (input or output), transcript text, prompts, raw stderr from whisper-cli/FFmpeg (which can echo paths and text). Child stderr is parsed in memory for progress/errors and discarded; only the derived failure code is logged.
- A redaction filter in `privacy/` drops any log record containing a path separator pattern combined with a user-folder prefix, as a last line of defense. Unit-tested.
- No log upload, no "copy diagnostics to clipboard" feature in V1.

### 9.4 Temporary files
- Per-job directory `%LOCALAPPDATA%\Dusty\work\<uuid>\`; deleted in a `finally` block after every job outcome.
- On startup, delete any orphaned `work\*` directories (crash leftovers).
- Never write temp files next to the user's recordings or in `%TEMP%`.

### 9.5 Output safety (enforces NN-7)
- Never modify, move, or delete source recordings.
- Overwrite only when the collision policy says Overwrite (and the user chose it).

### 9.6 Approved user-facing wording
- Privacy: "Dusty processes your recordings entirely on this computer. After installation, it never needs an internet connection, and it never sends your audio or transcripts anywhere."
- Medical/accuracy disclaimer: "Automatic transcripts can contain mistakes, especially with names, medications, and numbers. Always review a transcript before relying on it for medical, legal, or other important decisions."
- HIPAA (docs/FAQ only): "Dusty is designed for confidential workflows and keeps all processing on your device. It is not certified as HIPAA-compliant; compliance depends on how your organization secures its computers and data (for example, account security, disk encryption, and backups)."
- Never use: "HIPAA-compliant," "HIPAA-certified," "100% secure," "clinically accurate."

---

## 10. Dependencies, licensing, and supply chain

### 10.1 Pinning
- Python deps: pinned in `uv.lock` with hashes. Python 3.12.x. Record PySide6 / python-docx / PyInstaller versions chosen in M0 in `docs/dev/dependencies.md`.
- Native: `native/versions.toml` pins the whisper.cpp release tag **and** commit SHA, FFmpeg release tag, Vulkan SDK version, Inno Setup version.
- GitHub Actions: pin third-party actions by full commit SHA, not tag.

### 10.2 License allowlist for anything redistributed
Allowed: MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, Zlib, PSF-2.0, Unlicense/CC0 (data only), **LGPL-2.1+/LGPL-3.0 only when dynamically linked or a separate executable** (PySide6/Qt, FFmpeg).
Forbidden: GPL (any version) in shipped artifacts, AGPL, SSPL, proprietary/EULA-only (incl. NVIDIA CUDA redistributables), "non-commercial" licenses, unknown licenses.
`tools/check_licenses.py` fails CI on anything not allowlisted. Adding a dependency requires an ADR and PM approval (§14.3).

### 10.3 Hugging Face exclusion (enforces NN-3)
`tools/check_no_huggingface.py` fails CI if `huggingface`, `hf_hub`, `hf.co`, or `HF_TOKEN` appears in source, lockfile, workflows, native build scripts, or the model pipeline (allow it only inside this SPEC and ADR files that explain the exclusion).

### 10.4 Notices and SBOM
- `THIRD_PARTY_NOTICES.md` generated at release: every bundled component, version, license, copyright, and source URL. Includes the LGPL notices and source links for Qt/PySide6 and the exact FFmpeg source tag + configure flags.
- SBOM: CycloneDX JSON (`dusty-<version>-sbom.json`) covering Python packages and native components, attached to each release.

### 10.5 Model pipeline (`.github/workflows/models.yml`, manual dispatch, Linux runner)
1. Check out `openai/whisper` at the pinned commit; extract each model's URL from its source (the SHA-256 is embedded in the URL path — VERIFY); write/compare `modelpipeline/model_sources.json`.
2. Download each `.pt`, verify SHA-256. Fail on mismatch.
3. Build whisper.cpp at the pinned commit (for `whisper-quantize`); install pinned CPU-only PyTorch **in the CI job only**; run whisper.cpp's `models/convert-pt-to-ggml.py` (with the openai/whisper checkout for assets).
4. Quantize where specified (list decided in M1).
5. Convert Silero VAD from the upstream Silero package using whisper.cpp's conversion script (pinned versions; VERIFY the upstream package does not fetch from Hugging Face).
6. **Reproducibility check:** run conversion twice; hashes MUST match. If not deterministic, stop and report (S1).
7. Fail if any file ≥ 2 GiB.
8. Emit `models.json` (§5.8) and upload all files to the `models-v1` release as a **draft**. The Owner publishes it.
Model releases are independent of app releases; an app release only bundles the manifest.

---

## 11. Test strategy

### 11.1 Tooling
pytest (+ pytest-qt for GUI), ruff (lint + format), mypy (strict on `core/`, `export/`, `models/`, `queue/`, `privacy/`). Coverage report; target ≥ 85% line coverage for those strict packages.

### 11.2 Fixtures
- All fixture audio MUST be public domain or CC0, documented in `tests/fixtures/audio/AUDIO_SOURCES.md` (source URL, license, duration, expected text). Suggested: whisper.cpp's `samples/jfk.wav` (public-domain speech), short LibriVox (public domain) clips, a short Persian clip from a CC0 source (e.g., Mozilla Common Voice).
- Generated fixtures (create once with a full FFmpeg on the dev machine, commit the results, document the commands): same clip as mp3/m4a/flac/ogg/opus/wma/mp4/mkv/mov/webm; a video with no audio track; a zero-byte file; a truncated/corrupt mp3; a 10-minute file of mostly silence with a few words (VAD/hallucination test); a file with a non-ASCII name (`تست ضبط.m4a`) and a very long path.
- **The Owner's real recordings are never committed, never logged, and never stored in the repo.** Benchmarks that use them read a path from a CLI argument and record only timings.

### 11.3 Unit tests (examples, not exhaustive)
Exporters (golden files for each format, line wrapping, timestamp formatting, edge cases: zero segments, very long segment, unicode/RTL text); collision policy; folder scanning (recursive, unsupported filtered, duplicates); progress parser (feed recorded stderr samples); failure-code mapping; settings/queue load/save incl. corrupt files; manifest parsing and hash verification; network guard; log redaction (canary test: a job whose file is `CANARY_PATIENT_JANE_DOE.wav` with prompt `CANARYMEDTERM` must leave no trace of either string in logs); sync-folder detection; model rules (§6.5).

### 11.4 Integration tests (use `tiny.en` / `tiny` for speed)
- End-to-end single file → all 5 formats; content contains expected keywords.
- Batch of mixed formats including corrupt/no-audio/zero-byte → good files succeed, bad ones fail with the correct codes, batch completes.
- Cancel mid-file → no partial outputs, work dir removed, status Cancelled.
- Kill the app process mid-batch → child processes die (Job Object), restart shows resume prompt, resume completes remaining files.
- Collision policies (each).
- Translate task with a multilingual model on the Persian clip → English output (keyword check, loose).
- Vulkan vs CPU on the same file (where a Vulkan device exists) → transcripts substantially agree (normalized text similarity ≥ 0.9).

### 11.5 Offline and network-isolation tests (enforce NN-1, NN-2, NN-9)
**Automated (Windows CI runner and the release VM checklist):**
1. Enable WFP auditing: `auditpol /set /subcategory:"Filtering Platform Connection" /failure:enable /success:enable`.
2. Add outbound **block** firewall rules for `dusty.exe`, `whisper-cli.exe` (all builds), and `ffmpeg.exe`.
3. Run `dusty.exe --self-test` and a headless end-to-end batch (a hidden `--headless-batch` test entry point is acceptable if it uses exactly the same coordinator code).
4. Assert success, then query the Security event log for events 5156/5157 (allowed/blocked connections) whose application path matches any of those executables. **Any such event = test failure (S0).**
5. Remove the rules.

**Manual (release checklist, Owner performs on real hardware):** install → disconnect Wi-Fi/airplane mode → reboot → transcribe a batch on both the desktop (Vulkan/NVIDIA) and the Surface (Vulkan/Iris Xe and CPU) → success.

### 11.6 Installer tests (fresh Windows 11 VM, standard user account)
Clean install with model selection → self-test passes → shortcuts work → transcribe → uninstall (with and without keeping models) → no leftovers except what the user chose to keep → reinstall/upgrade preserves models without re-downloading → interrupted download resumes → tampered model file is rejected.

### 11.7 Performance tests
`tools/bench/run-bench.ps1` (native binaries only, no Python required, so it can run on the Surface from a USB folder): for each model × quantization × backend × thread count, transcribe a provided recording, record wall time and real-time factor (RTF = processing time ÷ audio duration), peak memory, and backend actually used. Output CSV + Markdown summary into `docs/pm/benchmarks/<machine>-<date>.md`.

---

## 12. Milestones

Work strictly in order. After each milestone, write the report (§15.5) and **stop**.

### M0 — Foundation
**Tasks**
1. Create the repo structure (§5.2), MIT LICENSE, README stub, CHANGELOG.
2. `pyproject.toml` with uv; pin Python 3.12; add PySide6, python-docx; dev deps: pytest, pytest-qt, ruff, mypy, pyinstaller, cyclonedx tooling, pip-licenses (or equivalent). Commit `uv.lock`.
3. Write `AGENTS.md` (§15.1), `docs/pm/LEDGER.md` (§15.2), ADRs 0001–0013 (§4).
4. Implement `tools/check_no_network.py`, `check_no_huggingface.py`, `check_licenses.py` (with tests).
5. `ci.yml`: on push/PR (Windows runner): ruff, mypy, pytest, the three checks.
6. A minimal `dusty` entry point that opens an empty Qt window titled "Dusty" and supports `--version`.
**Acceptance**
- CI green on `main`.
- Each checker demonstrably fails on a deliberately bad sample (include those negative tests).
- `uv run python -m dusty` opens the window on the Owner's machine (Owner confirms).

### M1 — Engine and model pipeline spike (GO / NO-GO GATE)
**Tasks**
1. `native/build_whisper.ps1`: build whisper.cpp (pinned) on Windows for CPU and Vulkan; decide single vs split builds (§5.5); document in `docs/dev/build-native.md`.
2. `native/build_ffmpeg.sh`: minimal LGPL FFmpeg cross-compiled (MinGW-w64) on Linux: `--disable-network --disable-everything --disable-autodetect --disable-gpl --disable-nonfree`, then enable only: `file`/`pipe` protocols; demuxers for the extensions in §6.1; the needed audio decoders (aac, mp3*, opus, vorbis, flac, alac, pcm_*, wmav1/2, amrnb/amrwb, ac3/eac3); parsers; `aresample`/`pan` filters as needed; WAV muxer + `pcm_s16le` encoder. Build `ffprobe` too if cheap. Record the full configure line and `ffmpeg -buildconf` in `docs/dev/ffmpeg-build.md`. Fallback ONLY with PM approval: a pinned third-party LGPL build verified by hash.
3. `models.yml` pipeline (§10.5) producing all candidate model files + VAD + `models.json` as a draft release.
4. VERIFY and document every whisper-cli flag in §5.4 (`docs/dev/engine-cli.md`), the JSON output structure (save a real sample), the stderr progress format (save samples for tests), and how Vulkan devices are reported.
5. `tools/bench/run-bench.ps1` + `summarize_bench.py`; package a "bench kit" folder (binaries + models + script) the Owner can copy to the Surface.
6. Owner runs benchmarks on (a) the desktop (Ryzen + RTX 3080 Ti: Vulkan and CPU) and (b) the Surface (i5-1235U: Vulkan on Iris Xe and CPU), using a ~10-minute representative English recording. Candidates at minimum: small, small.en, medium, large-v3-turbo (f16, q8_0, q5_0), large-v3 (quantized).
**Acceptance (gate criteria)**
- Conversion reproducible (identical hashes across two runs) and no HF access anywhere in logs.
- All files < 2 GiB.
- FFmpeg decodes every format in §6.1 fixtures; `-buildconf` shows networking disabled.
- Vulkan works on both machines OR the failure is precisely documented.
- Benchmark report includes RTF for every candidate on both machines.
- **Report must include a proposed final model catalog** (which models/quantizations ship, which is the default "Recommended" for CPU-only and for GPU machines) with evidence. The PM decides GO/NO-GO and the catalog. Targets: on the Surface, at least one model at the accuracy level of `small` or better runs at RTF ≤ 1.0; on the desktop, Large-v3-Turbo on Vulkan runs at RTF ≤ 0.15.

### M2 — Headless core pipeline
**Tasks**
`core/` types; `engine/` runners (FFmpeg, whisper-cli, Job Objects, progress parsing, backend probe + fallback); `models/` (manifest, registry, verification); `export/` (all five formats); `queue/` coordinator with persistence and collision handling; `privacy/` (network guard, log redaction, sync detection); `selftest.py`; a dev-only CLI `python -m dusty.devcli transcribe <files...> --model ... --out ...` that drives the same coordinator.
**Acceptance**
- All unit tests (§11.3) and integration tests (§11.4) pass.
- Offline/network test (§11.5) passes against `python -m dusty --self-test` on the CI runner (pre-packaging variant).
- Canary log test passes.

### M3 — GUI (single file and batch)
**Tasks**
Main window (§8.2), settings panel (§6.2), queue table, drag-and-drop, folder scan dialog, progress/ETA, cancel, collision dialog, summary dialog, resume prompt, first-run screens (§6.8), sync-folder warning, error messages (§8.6), light/dark, scaling. The GUI calls the M2 coordinator only (no business logic in widgets). Coordinator runs off the UI thread (QThread / worker) and communicates via signals.
**Acceptance**
- pytest-qt tests for: add files/folder, reorder/remove, start/cancel, collision dialog, resume prompt, model rules (§6.5) disabling controls.
- The Owner completes a scripted UI walkthrough (provide it in the report as a checklist) on the desktop and reports pass/fail per step.
- UI responsive (no freezes > 200 ms) during a batch.

### M4 — Model Manager and `dusty-fetch`
**Tasks**
`dusty_fetch`: CLI `dusty-fetch download --id <model> --dest <dir> --manifest <path>`; HTTPS only, host allowlist = `github.com` and GitHub's release-asset CDN host(s) (VERIFY the redirect hosts); resumable (HTTP Range); `.part` files; SHA-256 verification against the bundled manifest; machine-readable progress on stdout (JSON lines); exit codes. Model Manager dialog (§6.6) driving it as a child process.
**Acceptance**
- Tests: successful download, resume after interruption, hash mismatch rejected and `.part` deleted, disallowed host rejected, disk-full handled.
- `dusty` package still passes `check_no_network.py` (it only spawns `dusty-fetch.exe`).

### M5 — Packaging, installer, release pipeline
**Tasks**
1. PyInstaller specs: `dusty` (windowed, onedir, Qt networking/WebEngine excluded) and `dusty-fetch` (console, onedir or merged into the same dir — VERIFY the cleanest layout); bundle `bin\` native binaries and `resources\`.
2. Inno Setup script generated from `models.json` (`installer/generate_iss.py`): Welcome → License (MIT + notices) → **Choose model** page (catalog with sizes; pre-selects the M1 recommendation based on detected Vulkan GPU and RAM; user can pick one or more) → install dir (default `%LOCALAPPDATA%\Programs\Dusty`) → shortcuts (Start Menu; optional Desktop) → **download page using Inno Setup's built-in downloader with SHA-256 checks** (VERIFY the API for the pinned Inno version) → run `dusty.exe --self-test --model <id>` → finish. **Installation MUST report failure if download, verification, or self-test fails**, with retry.
3. Upgrade behavior: detect existing install; keep models; skip downloads for models that verify.
4. Uninstaller: removes app files, settings, state, logs, work dirs; checkbox "Also remove downloaded models (X GB)" default checked; never touches user output folders.
5. `release.yml` on tag `v*`: build native (or reuse pinned artifacts from M1 builds, with hashes), build FFmpeg, PyInstaller, Inno Setup, generate notices + SBOM + `SHA256SUMS.txt`, run the offline/network test (§11.5) against the **installed** app on the runner, upload everything to a **draft** GitHub Release. The Owner publishes.
6. README section "Windows SmartScreen warning" explaining "More info → Run anyway," why (unsigned open-source), and how to verify the installer against `SHA256SUMS.txt`.
**Acceptance**
- Draft release produced by CI from a tag with all artifacts.
- §11.6 installer tests pass on a fresh Windows 11 VM (Owner runs; provide a checklist).
- Installer size reported in the milestone report.

### M6 — Hardening and documentation
**Tasks**
Fix all open S1/S2 issues; full offline manual test (§11.5 manual) on both machines; long-file test (≥ 2 h recording) on the Surface (memory and temp-disk behavior); `docs/user/` (install, first run, batch how-to, choosing a model, vocabulary hints, troubleshooting, FAQ incl. HIPAA wording), `docs/privacy.md` (exactly what is stored where, what touches the network and when), `docs/dev/` (build from source, release process, reproducing model conversion), CONTRIBUTING.md.
**Acceptance**
- Zero open S0/S1 issues.
- All checklists passed with Owner sign-off.

### M7 — Release candidate → v1.0
**Tasks**
Tag `v1.0.0-rc.1`; the primary user installs and uses it on the Surface with the Owner present; collect issues; fix; tag `v1.0.0`.
**Acceptance**
- Primary user completes install + a real batch without assistance beyond the SmartScreen step.
- PM sign-off.

---

## 13. Definition of done

### 13.1 For a task
Code + tests written; tests pass locally and in CI; ledger updated with evidence; no new lint/type errors; docs updated if behavior changed.

### 13.2 For a milestone
All tasks done; all acceptance criteria met **with evidence**; report written (§15.5); CHANGELOG updated; branch merged to `main` via PR (squash) with CI green.

### 13.3 Things that never count as done
"It builds." "Tests were flaky so I skipped them." "Should work on Windows 10." "Benchmarks look roughly like X." Anything verified only by reading code.

### 13.4 Evidence means
Exact commands run + their summarized output (pass counts, hashes, timings), CI run links/IDs, file paths of generated artifacts, and screenshots or Owner confirmations for things you cannot run yourself. If the Owner must run something, give exact copy-paste steps and say what output to send back.

---

## 14. Issue management and escalation

### 14.1 Severity
| Sev | Definition | Action |
|-----|------------|--------|
| **S0** | Violates any NN requirement (network activity during processing, sensitive data in logs, HF dependency, data loss/overwrite, proprietary component shipped, unverified model used) | **Stop all work immediately.** File the issue, write an interim report, wait for PM. |
| **S1** | Core feature broken or acceptance criterion cannot be met | File issue; continue other tasks if independent; report at milestone end (or immediately if it blocks the milestone). |
| **S2** | Feature works but degraded (performance, edge case, confusing UX) | File issue; fix within milestone if cheap, otherwise list in report. |
| **S3** | Cosmetic / polish | File issue; batch for M6. |

### 14.2 How to file
One file per issue: `docs/pm/issues/ISSUE-NNN-short-title.md` using the template (§15.4). Reference it in the ledger and commit messages. Never delete issues; close them with a resolution.

### 14.3 You MUST stop and escalate (interim report, then wait) when:
- Any S0.
- You need to add, remove, or swap a dependency or native component.
- An upstream tool behaves differently from this spec in a way that changes design (flags missing, formats changed, Vulkan unusable, conversion non-reproducible).
- An acceptance criterion seems impossible or wrong.
- You're about to change any decision in §4 or any NN requirement.
- You've spent ~3 focused attempts on the same failure without progress.
- You need a credential, account, or anything the Owner must do.

### 14.4 Root-cause expectations
For S0/S1 issues, the issue file MUST include a root-cause analysis (what failed, why, how it was found, why tests didn't catch it, what test now prevents recurrence).

---

## 15. Templates

### 15.1 `AGENTS.md` (create in M0; keep it short and current)
```markdown
# AGENTS.md — Dusty

You are the implementing engineer for Dusty. Source of truth: docs/pm/SPEC.md. Current assignment: docs/pm/CURRENT_MILESTONE.md.

## Rules
1. Work only on the current milestone. Do not start the next one.
2. Never violate NN-1..NN-10 (SPEC §2). If something would, stop and escalate.
3. No network code outside src/dusty_fetch. No Hugging Face anything. No telemetry.
4. No new dependencies without an ADR + PM approval.
5. Never skip, disable, or weaken a test to make CI pass. Never fabricate results.
6. VERIFY upstream behavior (flags, formats) against pinned versions; document in docs/dev/.
7. Small commits, Conventional Commits (feat:, fix:, test:, docs:, chore:, refactor:, build:, ci:), one branch per milestone (m<N>-<slug>).
8. Never log file names, paths, transcript text, or prompts.
9. Never commit user recordings or any non-public-domain/CC0 audio.
10. Update docs/pm/LEDGER.md as tasks change state, with evidence.

## Commands
- Setup: uv sync
- Lint/format: uv run ruff check . && uv run ruff format --check .
- Types: uv run mypy
- Tests: uv run pytest
- Checks: uv run python tools/check_no_network.py && uv run python tools/check_no_huggingface.py && uv run python tools/check_licenses.py
- Run app: uv run python -m dusty

## When blocked
Write docs/pm/reports/M<N>-interim-<n>.md (SPEC §15.5), then stop.
```

### 15.2 `docs/pm/LEDGER.md`
```markdown
# Task Ledger
| ID | Milestone | Task | Status (todo/doing/blocked/done) | Evidence | Issues |
|----|-----------|------|----------------------------------|----------|--------|
| M0-01 | M0 | Repo structure | done | commit abc123; tree in report | — |
```

### 15.3 ADR (`docs/adr/NNNN-title.md`)
```markdown
# NNNN — Title
- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD
## Context
## Decision
## Consequences
## Alternatives considered
```

### 15.4 Issue (`docs/pm/issues/ISSUE-NNN-title.md`)
```markdown
# ISSUE-NNN — Title
- Severity: S0 | S1 | S2 | S3
- Milestone: M<N>
- Status: Open | In progress | Resolved | Won't fix (PM approval required)
- Environment: machine, Windows version, backend, model, app/engine versions
## Steps to reproduce
## Expected
## Actual
## Evidence (logs must be redacted; no file names or transcript text)
## Root cause (required for S0/S1)
## Fix / proposed fix
## Regression test added
```

### 15.5 Milestone report (`docs/pm/reports/M<N>-report.md`) — the Owner pastes this to the PM
```markdown
# M<N> Report — <title>
## 1. Summary (3–5 sentences: what works now, what doesn't)
## 2. Acceptance criteria
| Criterion | Status (met / not met / partial) | Evidence |
## 3. What was built (files/modules, brief)
## 4. Test results (counts, coverage, CI run IDs)
## 5. Deviations from SPEC (each with reason; link ADR if any)
## 6. Issues (table: ID, severity, status, one-line summary)
## 7. Decisions needed from PM/Owner (numbered, each with options and your recommendation)
## 8. Actions needed from the Owner (exact steps, what to send back)
## 9. Risks for the next milestone
## 10. Time/effort notes (what was harder than expected)
```
Keep reports factual and concise. Do not pad. Bad news goes in section 1, not buried.

---

## 16. Working agreement with the PM

1. The Owner places this file at `docs/pm/SPEC.md` and the first brief at `docs/pm/CURRENT_MILESTONE.md` (initially: "M0 — Foundation. Proceed per SPEC §12 M0.").
2. You execute the milestone autonomously, escalating only per §14.3.
3. At milestone end you produce the report and stop.
4. The Owner pastes the report to the PM. The PM reviews, may request fixes (as a revised CURRENT_MILESTONE.md), and then issues the next brief.
5. Disagreements: if you believe the PM's instruction is technically wrong, say so in the report with evidence and a recommendation — then follow the PM's final decision.

---

## Appendix A — Hardware reference

| Machine | CPU | RAM | GPU | Role |
|---------|-----|-----|-----|------|
| Owner desktop | AMD Ryzen | — | NVIDIA RTX 3080 Ti (12 GB) | Dev machine; Vulkan/NVIDIA test target |
| Primary user laptop | Intel Core i5-1235U (10C/12T) | 16 GB | Intel Iris Xe (integrated) | CPU and Vulkan/iGPU test target; design target for defaults |

## Appendix B — Glossary
- **RTF (real-time factor):** processing time ÷ audio duration. RTF 0.5 = a 60-min file takes 30 min.
- **GGML:** the model file format whisper.cpp uses.
- **Quantization (q8_0, q5_0):** smaller, faster model files with slightly lower precision.
- **VAD:** voice activity detection; skips silence so Whisper doesn't invent words.
- **Owner:** the human maintainer. **PM:** the project manager reviewing your reports.
