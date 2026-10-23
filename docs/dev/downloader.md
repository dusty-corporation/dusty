# Isolated downloader (M4 limited scope)

The PM authorized downloader-only prework on m4-downloader from m3-gui.
The offline application and its GUI are unchanged. No dependency was added.

## CLI and protocol

```powershell
uv run dusty-fetch download --id tiny --dest build/models --manifest resources/models.json
uv run dusty-fetch verify --id tiny --dest build/models --manifest resources/models.json
```

`python -m dusty_fetch` exposes the same commands. The manifest is a local
bundled trust anchor: no manifest URL or remote refresh is supported. Canonical
catalog IDs and silero-vad are accepted. Filenames must be safe ggml-*.bin
basenames, hashes 64 lowercase hex digits, sizes positive and below 2 GiB.
Only the requested entry is selected; no downloader import of dusty is needed.

Stdout is flushed JSON lines; no filenames, paths, URLs, signed query strings
or exception text are printed. Events: downloading (bytes/total), verifying,
complete (bytes/total/cached), verified (bytes/total), error (code), cancelled
(code). Argument errors use the same error record. --help is human-readable.
Progress is monotonic except a legitimate restart when a server ignores Range.

| Exit | Code | Meaning |
|---|---|---|
| 0 | OK | Download hash/size verified and published, or verify succeeded |
| 2 | INVALID | Invalid arguments, unreadable/invalid manifest or unknown ID |
| 3 | BLOCKED | Disallowed scheme, host, port, credentials or redirect |
| 4 | MISMATCH | SHA-256/size verification failed; download .part removed |
| 5 | DISK_FULL | Insufficient preflight space or OS out-of-space error |
| 6 | NETWORK | TLS/HTTP/connection/timeout or invalid range response |
| 7 | IO | Other local filesystem error or unsafe symlink |
| 8 | BUSY | Another download holds the model's OS lock |
| 130 | CANCELLED | Ctrl+C/cooperative termination; partial download removed |

A hard OS termination may have an OS-selected exit status and no final event.
Only a fully verified file can become final; existing finals remain unchanged
until a verified replacement is ready. verify is read-only and never deletes
an existing final that fails verification.

## Verified upstream HTTPS behavior

Observed on 2026-10-22 using pinned Python 3.12.11 and a one-byte request to
https://github.com/dusty-corporation/dusty/releases/download/models-v1/ggml-tiny.bin:

- github.com returned HTTP 302 to release-assets.githubusercontent.com.
- Final response: HTTP 206, Content-Range bytes 0-0/77691713.
- Only hostnames/status/range were recorded; signed URLs were not retained.

The exact allowlist is github.com and release-assets.githubusercontent.com,
with HTTPS and port 443 only. No wildcard, alternate CDN, credentials,
fragment, implicit proxy or CLI allowlist override is allowed. Every redirect
is checked before it is followed. A future CDN hostname is rejected until it
is independently verified and approved. The single CI-only Tiny integration
exercises that real chain and the bundled hash; local unit tests use only TLS
on loopback with an injected policy and test certificate.

Python's [TLS reference](https://docs.python.org/3.12/library/ssl.html#ssl.SSLContext.load_default_certs)
confirms create_default_context verifies certificates/hostnames and loads the
Windows CA and ROOT stores. No certifi, CA-store installation or verification
bypass is used. The [redirect handler API](https://docs.python.org/3.12/library/urllib.request.html#urllib.request.HTTPRedirectHandler.redirect_request)
was verified through actual localhost redirects; standard redirect limits
remain enabled. TLS rejection is tested with the untrusted localhost fixture.

## Resume, space and publication

A .part contains only the local download prefix. Range starts at its current
length. HTTP 206 must describe that exact start, final end and manifest total;
malformed ranges are refused without appending. A 200 response restarts rather
than appending. Truncated responses retain the prefix for a later attempt.
SHA-256 and size are checked before atomic replacement in the same directory;
a mismatch removes the part. Old/mismatched prefixes can never publish as a
valid model because the full digest is always checked.

Preflight checks remaining bytes plus 1 MiB headroom on the destination volume;
a full-response restart checks full size. Real OS space failures are mapped
separately. A per-model .lock file uses an OS lock across hash and rename;
it stays as a tiny harmless file and cannot become a stale PID lock after
termination. Windows uses [msvcrt.locking](https://docs.python.org/3.12/library/msvcrt.html#msvcrt.locking);
POSIX uses flock. The subprocess termination test verifies lock release and
Range handling without touching a final file before verification. Ctrl+C and
cooperative termination close handles and remove the partial. When the GUI
cancels or closes, it first terminates and joins the child Job Object, then
removes that manifest-owned partial. The next user attempt starts fresh.
An abrupt OS crash cannot execute cleanup; an orphan prefix is still never
published without full size and hash verification.

Environment proxies are deliberately not followed: their destinations are not
part of this allowlist. Explicit proxy support is outside this limited scope.

## GUI integration and audit attribution (M4)

The offline GUI never imports dusty_fetch. It starts the existing CLI via
run_job_process, suspended until assigned to a kill-on-close Windows Job Object.
Source uses the current Python interpreter with `-m dusty_fetch`; the split
package uses `../dusty-fetch/dusty-fetch.exe` relative to dusty/dusty.exe.
Both command resolutions have unit tests; packaged behavior is verified in M5 CI.

Each CLI JSON event additionally includes `pid`, its real `os.getpid()` value.
This is ephemeral parent/child audit metadata, not a filename, URL or user-content
log. Windows interpreter launchers can have a different PID from the interpreter
that opens sockets, so the OS create-process PID alone is insufficient. The GUI
validates event type, counts, manifest total and positive PID; raw stderr is discarded.

Model Manager re-hashes locally and allows deletion of every model, including
the selected or last model. Deleting the selected model clears Options without
choosing a replacement; in-use voice detection requires confirmation too.
Only installed models are offered for transcription. A newly installed model
is selected only when Options has no choice. The PM's 2026-10-23 UX decision
supersedes the brief's earlier deletion protections and cancel/resume behavior. Voice detection is listed
separately and is included in both consent and total download size when required
by Skip silent parts. Consent precedes every download request. No host, proxy or
TLS override was added to the production CLI. Tests inject loopback trust only
in a separate test helper process, with the GUI audit hook still installed.

`tools/test_model_download_isolation.ps1` runs on disposable Windows CI only.
A positive blocked WFP event calibrates auditing. The real guarded Dusty entry
then opens the actual Model Manager, explicitly simulates its consent button,
downloads Tiny plus voice detection and verifies live installed-choice updates.
The GUI must produce zero 5156/5157 events and the reported child PIDs must
produce positive allowed events and zero blocked events. Counts are retained;
addresses, signed redirect URLs and user paths are not emitted.

In source form both processes share Python's image: the download phase attributes
by actual PIDs after removing its calibration block. The separate existing
processing acceptance still blocks Python. In split-package form the GUI image
stays blocked while the separate downloader is allowed. That phase additionally
checks all events from the GUI executable. `--check-model-download` is a hidden
CI-only acceptance entry, not a user-facing feature; ordinary use is rejected.
