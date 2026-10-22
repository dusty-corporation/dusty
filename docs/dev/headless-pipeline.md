# M2 headless pipeline

`python -m dusty.devcli transcribe <files...> --model tiny --out <directory>`
drives the same coordinator as `python -m dusty --headless-batch <files...>
--out <directory>`. The latter installs the audit hook before importing the
coordinator. Both run one file at a time, use VAD by default, and store
per-job WAV and engine JSON in the local app work directory.

The coordinator checks the input, verifies the model hash, probes duration,
checks free space against twice the estimated 16 kHz mono WAV size, decodes,
transcribes, parses, publishes requested formats, and removes the work
directory in a `finally` block. Vulkan failures classified as device/backend
errors retry that file once with the CPU package. The batch setting is not
changed. A source file is never an output target.

`queue.json` and `settings.json` use schema version 1 and atomic replacement.
Unknown or invalid files are renamed with a `corrupt-<timestamp>` suffix.
On restart, jobs still in progress return to Queued; Done jobs are retained
only when all recorded outputs still exist. Clear history deletes `queue.json`.
New outputs use an atomic same-directory rename on Windows that fails if the
target appeared after collision planning. Overwrite uses `os.replace` only
when that policy was selected.

The Vulkan probe runs the bundled public self-test clip and tiny model. Its
cache in `settings.json` is keyed by the Vulkan engine SHA-256 and a hash of
local display adapter driver identifiers, versions, and dates read from the
Windows display class registry key. A changed engine or driver forces a fresh
probe. The cache stores only success and the device name, never paths or
recording content. `--self-test` always decodes and checks CPU transcription;
Auto also checks Vulkan when the probe succeeds.

The M1 prompt context was measured at 224 tokens for the pinned engine. The
CLI warns when a conservative character estimate exceeds 200 tokens. It
passes the full prompt as one argument and never logs it. The UI can replace
this estimate with a tokenizer in a later milestone if approved.

`tools/measure_coverage.py` uses Python's standard-library line tracer; its
audit-hook exercise runs in a separate interpreter because hooks are
irreversible. The script prints package-level coverage for the strict M2
packages without adding a dependency.
