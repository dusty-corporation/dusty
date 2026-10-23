# M5 Phase 1: model-free Vulkan verification

Verified 2026-10-23 on the Owner desktop, using engine-v2, whisper.cpp v1.9.5
commit d1be6fde11ac6e0407606b4e42fe72d34add8037 plus the pinned VAD patch.
This is an investigation result, not an implemented installer feature.

## CLI limitation

The pinned examples/cli/cli.cpp checks input files and model existence before
calling ggml_backend_load_all. No device-list CLI flag exists in its parser.
Invoking the exact pinned whisper-cli.exe with resources/selftest.wav and a
nonexistent model returned 3, with no load_backend line. --help does not establish
device usability. The registry/ICD heuristic in the old installer is insufficient.

## Existing DLL API works without a model

The existing bundle already includes all required engine libraries. Export-table
inspection confirms these C exports and their owning DLLs:

| DLL | API used |
| --- | --- |
| ggml.dll | ggml_backend_load(absolute ggml-vulkan.dll path) |
| ggml-base.dll | ggml_backend_reg_dev_count, ggml_backend_reg_dev_get |
| ggml-base.dll | ggml_backend_dev_init(device, NULL) |
| ggml-base.dll | ggml_backend_alloc_buffer(backend, 4096), ggml_backend_buffer_clear(buffer, 0), ggml_backend_synchronize |
| ggml-base.dll | ggml_backend_buffer_free, ggml_backend_free |

The ABI is declared in ggml/include/ggml-backend.h. Use pointer results as
void*, indices/counts/sizes as size_t, strings as char*, clear value as uint8_t;
free/clear/synchronize return void. Use ctypes.CDLL (C calling convention),
not guessed C++ layouts. Enumerate only the registry returned for the Vulkan DLL.
A non-null device/backend and successful buffer clear/synchronization establish
real Vulkan initialization rather than a GPU-name or registry match.

A temporary repository-local Python probe installed Dusty's audit hook first,
used an explicit DLL directory, opened no model, and ran in a separate process
with a repository-local profile and a 60-second supervising timeout. Output:

```json
{"model_file_opened": false, "vulkan_devices": 1, "initialized": 1, "buffer_clear_and_sync": 1}
```

Exit 0, wall 0.468 seconds on this desktop. The first attempt correctly rejected
an assumed export location: device APIs live in ggml-base.dll, not ggml.dll.
The corrected call sequence above passed. Every loaded engine DLL and CLI was
byte-compared with whisper-vulkan.zip after its archive SHA-256 matched
native/versions.toml: 2a4aeae6789391c7cc2fa8bbe01648e0d36c499ca1233cbdcf58d127c47fc6a0.

This proves model-free initialization on this desktop, not Turbo inference,
adequate model memory, zero WFP events, or ThinkPad/Surface acceptance of the new
probe. Phase 2 should expose it through an isolated, guarded Dusty child entry
point with a bounded timeout and Small fallback. No new native binary or loader
should be bundled. Pre-selection happens before app files are installed, so the
installer must extract the minimal probe payload temporarily or place that page
after file installation with PM approval. Raw driver stderr must be discarded.

Pinned source references:
- https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/examples/cli/cli.cpp
- https://github.com/ggml-org/whisper.cpp/blob/d1be6fde11ac6e0407606b4e42fe72d34add8037/ggml/include/ggml-backend.h

No production probe code was added during Phase 1.

## Implemented probe evidence (M5 Step B)

The production guarded probe and its standalone diagnostic are now implemented.
Owner ThinkPad Iris Xe result on 2026-10-23:
`{"real_gpu_found":true,"model_file_opened":false}`. Desktop diagnostic passed
with PowerShell 7 and Windows PowerShell 5.1; production entry also returned true.
This supersedes the Phase 1 pending-device note, not its historical findings.
The bounded child initializes a physical integrated/discrete GPU and performs a
4 KiB buffer operation. Software devices are rejected. The post-download model
inference tests remain mandatory; enumeration alone is never inference evidence.
