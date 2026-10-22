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

The native integration suite cancels an active transcription and checks work
and output cleanup, exercises every collision policy, and compares normalized
CPU and Vulkan text at similarity >= 0.9 when a usable Vulkan device exists.
Its crash regression kills the actual coordinator interpreter with a live
whisper-cli child, waits for child death using a Windows synchronization handle,
then loads and resumes the persisted batch while preserving completed output.
The Windows virtual-environment Python launcher can have a different PID from
the actual interpreter; the test records and terminates the interpreter PID.
The resume dialog belongs to M3; M2 verifies the recovery data and coordinator.

The dev CLI also accepts folders. `--recursive` includes subfolders;
`--keep-structure` preserves paths relative to each selected folder. The shared
scanner filters the 17 verified extensions, deduplicates resolved paths, and
returns counts without logging paths. `core/failures.py` provides an actionable
message for every failure code for the later GUI to consume. Saved batch
preferences are validated on load, and malformed known settings are quarantined.

`Coordinator.run_batch` accepts separate `cancel` (whole batch) and
`cancel_current` events. A current-file cancellation is consumed and cleared
before the next file starts. Numeric engine progress is published on the
coordinator's worker thread; stderr reads consume available pipe bytes so a
short progress line is delivered before process exit. Raw native lines are
still discarded after parsing.

While a batch runs, the Windows platform helper requests
`ES_CONTINUOUS | ES_SYSTEM_REQUIRED` with `SetThreadExecutionState` and restores
the prior thread state in a `finally` block. It does not keep the display on
or override a user's explicit sleep request. This behavior and the previous-state
return value were verified against the
[Microsoft API documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
