# 0037 - macOS direct runner with a lifeline helper

- Status: Accepted by PM under direct Owner instruction
- Date: 2026-11-07
- Supersedes for product use: the MAC-9 gating in ADR 0034, 0035 and 0036.
  Those records, the native bridge sources and the proof harnesses stay in the
  tree and in branch history as reference. They are no longer on the delivery path.

## Context

The Python audit guard (ADR 0017) blocks `subprocess`, `os.posix_spawn`, `os.fork`
and `os.exec*` in the offline app. On Windows, Dusty starts its fixed native
programs (ffmpeg, ffprobe, whisper-cli) by calling `CreateProcessW` through ctypes,
restricted by `approved_executable`, inside a kill-on-close Job Object.

macOS has no Job Object. The previous Mac plan replaced it with a three-process
native bridge, supervisor and guardian, and required an exhaustive fault matrix
before any audio could be decoded. After six days it had produced no transcript.
The Owner directed on 2026-11-07 that the port switch to a simpler design that
mirrors the Windows boundary.

## Decision

1. `dusty.platform.mac_process.run_job_process` has the same signature and
   `ProcessResult` as the Windows runner. It calls libc `posix_spawn` through
   ctypes, exactly as Windows calls `CreateProcessW` through ctypes. The audit
   guard stays installed and unchanged.
2. Only executables accepted by the shared `approved_executable` rule may start:
   files inside the runtime `bin_dir`, the isolated downloader and the app's own
   interpreter. There is no generic launch API.
3. Every processing child starts under a small native helper, `dusty-lifeline`,
   which leads its own process group, starts the target as the leader of a
   second new group and holds a pipe from the app. When the pipe reaches end of
   file (cancel, timeout or app death, including SIGKILL), the helper kills the
   target's whole group while the target is still an unreaped zombie, so its
   process ID cannot have been reused, then reaps it. This is the Mac
   equivalent of kill-on-close. Descendants that deliberately leave the group
   (setsid or setpgid) would escape; ffmpeg and whisper-cli do not do that.
4. Children receive stdin from /dev/null, stdout and stderr through pipes that
   are parsed in memory only, a minimal environment, the executable's folder as
   working directory, and no other inherited descriptors.
5. Shared code picks the runner by platform. Windows behavior and code are
   unchanged.

## Consequences

Residual risk: if the lifeline helper itself is killed with SIGKILL while the app
also dies, the target can outlive both. The helper is tiny and has no other job,
so this needs two independent failures. Startup cleanup of owned work data still
applies, and the residual is documented in privacy notes.

The native programs are already built with networking disabled (FFmpeg
`--disable-network`, whisper.cpp without curl). Network attempt observation for
native children remains a privacy acceptance task.

## Alternatives considered

Keep the ADR 0034 bridge: rejected by the Owner for delivery speed. Killing the
process group from Python only: does not cover app death. kqueue parent watching
inside each target: not possible for third-party binaries without patches.
