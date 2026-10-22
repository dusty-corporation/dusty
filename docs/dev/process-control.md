# Native process control

The pinned FFmpeg and whisper-cli binaries are launched with absolute executable
paths and argument arrays. The Windows launcher creates each process suspended,
assigns it to a Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, then resumes
it. It uses `CREATE_NO_WINDOW`. Cancellation terminates the Job Object. This order
prevents a child from running before assignment. The launcher parses stderr in
memory and discards unrecognized lines, including paths and transcript text.

The default thread count uses Windows `GetLogicalProcessorInformationEx` with
`RelationProcessorCore`, capped at eight. This counts P and E cores separately
on hybrid laptops. See Microsoft's
[processor relationship API](https://learn.microsoft.com/en-us/windows/desktop/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex).

Microsoft documents the relevant APIs and flags in
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw),
[process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags),
[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
and [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

The pinned CPU and Vulkan binaries were exercised locally on the public JFK WAV
with the pinned tiny and Silero VAD models on 2026-10-22. Both produced JSON with
the expected transcript. The CPU package omits a backend banner with `-ng`; the
Vulkan package prints `whisper_backend_init_gpu: using Vulkan0 backend`. A later
`no GPU found` line refers to the VAD context and does not negate the main Vulkan
selection. `-pp` emits timing lines, while `-np` suppressed them in this pinned
build, so Dusty discards stdout instead of adding `-np`.
