# Pinned Mac CPU and Metal inference recipe

MAC4-WHISPER, 2026-10-31. Worker base
69136f07875ec6a900951dc5daad964ae480c054, in an isolated worktree. Windows scripts and all existing pins are unchanged.

## Input and mutation boundary

`native/macos/build_whisper.sh` accepts a local upstream checkout, a new output
directory whose parent exists, and cpu or metal:

```sh
bash native/macos/build_whisper.sh <source-checkout> <new-output> cpu
bash native/macos/build_whisper.sh <source-checkout> <different-new-output> metal
```

There is no source/model downloader in the recipe. It verifies the caller's true
Git root, exact pinned HEAD, no untracked additions (including ignored files),
and a complete canonical diff against HEAD. Only pristine input or the exact
approved patch diff is accepted. Additional edits in either of the approved
patch's files, additional files and partial patches are rejected. Checking two
filenames or whether a reverse patch applies would not establish this closure.

The approved patch file is SHA-256 checked against native/versions.toml before
any source copy/build. Canonical diff generation fixes prefixes, context, hash
abbreviation and diff algorithm, and disables external diff/text conversion.
Its complete byte hash must equal the approved patch file hash. Noncanonical
Git formatting can cause a safe refusal, not permission to ignore a mismatch.

The caller is never patched or configured. A local clone into a fresh recipe-owned
source directory provides genuine upstream metadata, copies objects without
hard links and dissociates alternates. Checkout hooks are disabled. The pinned
commit is checked out, the hash-verified patch applied, and the entire canonical
diff checked again before CMake. All caller Git reads disable optional locks.
Source/output identity errors fail before output creation; existing outputs,
output symlinks and in-source destinations are refused rather than deleted.

CMake generates bindings/javascript/package.json even for this CLI target.
That known generated file stays in the recipe-owned source; an already configured
caller checkout with untracked output is deliberately refused. The original
MAC-0 caller was left unchanged; a fresh local clone of its existing committed
objects supplied this task's pristine input. No remote source fetch was needed.
The recipe checks tracked patch closure and caller diff again after building.

## Source, configuration and identity

Verified upstream commit: d1be6fde11ac6e0407606b4e42fe72d34add8037 (v1.9.5).
Verified upstream tree: 6fe2755682242a5c01aba65a22b3c0305d747841.
Approved VAD patch SHA-256 and actual canonical source diff SHA-256:
5dea476a89b6a7ac725cffeb72e2d80a33dc04ac0f0635dfe28cc4a25d911d1b.
Recipe SHA-256: 94d542f682177f3a2ae0e01049b4a99eede11950002ff63c05ef0a092088819f.

The build explicitly selects arm64, Release, Apple xcrun clang/SDK, system Apple
BLAS/Accelerate, and CPU or embedded-shader Metal. Only whisper-cli is built.
Server, CURL, RPC, CUDA, Vulkan, Core ML, OpenVINO, VitisAI, SDL2, OpenMP and runtime
backend loading are disabled. Native CPU tuning and ccache are disabled. Required
backend/privacy cache entries are verified before compilation, not merely printed.
The remaining optional backends retain the exact pinned source's OFF defaults;
this is not a binary network-capability audit.

WHISPER_BUILD_IS_DEV=OFF deliberately selects the upstream 1.9.5 version label.
Provenance separately retains the full upstream commit/tree, approved patch hash,
canonical source diff, input patch state, backend, target and toolchain. This is
not described as an unmodified upstream release. Configure output reports
whisper.cpp version 1.9.5 and ggml commit d1be6fd for both actual builds.

The package contains the CLI, its required shared dylibs/symlinks and upstream
LICENSE.txt. Build/install RPATH is explicitly @loader_path. Dependency listings
and hashes are recorded for every output; no server/example executable is copied.
This is a native experiment package, not a signed Dusty application or an accepted
release inventory/SBOM. No new runtime/build package or model dependency was added.

## Actual builds and outputs

Existing CMake 4.4.5, Apple clang 21.0.0, SDK 26.5, on M2 arm64 macOS 26.2.
The standalone metal compiler remains absent; embedded shaders compile/use system
Metal at runtime without a full Xcode installation on this machine.

```sh
bash native/macos/build_whisper.sh build/mac4-whisper/input build/mac4-whisper/cpu cpu
bash native/macos/build_whisper.sh build/mac4-whisper/input build/mac4-whisper/metal metal
```

Both commands exited 0. Scratch directories retain source-copy logs, complete
configure/build output, CMakeCache, provenance, architecture/dependency inspection
and SHA256SUMS.txt for CLI, libraries and license. Caller input status remained
clean; recipe-owned tracked changes remain exactly the approved patch.

| CLI | SHA-256 |
| --- | --- |
| CPU | b33c2ffa2f69996ea4f9e2e8c3bb5e8963f57e364c24d872a30a48c5ea2abd2d |
| Metal | 31ded38d3285767ab4305e908365ed0b147da33aec310888e772be532d935fd2 |

Both are Mach-O arm64. The CLI uses relative @rpath dependencies and an
@loader_path RPATH; library listings contain its bundled whisper/ggml libraries
and Apple system libraries/frameworks. No Homebrew runtime prefix is needed by
these package CLIs. LC_BUILD_VERSION reports minos 26.0 and SDK 26.5. Execution
here proves macOS 26.2 only; minimum product OS, clean-machine relocation,
signing/notarization and older/Intel support remain unverified.

## Public-fixture and backend evidence

No model was downloaded. The existing local MAC-0 Tiny and Silero VAD files were
reused read-only after size and SHA-256 verification against
`tests/fixtures/models/models-v1.json`. Tiny is the tiny-f16 entry (77,691,713
bytes, a38bcb31dcd68cf7d9a630e2148ccf0656f95ac87c5bcbc4064a689f383b2059);
VAD is 885,098 bytes, abd79739d3ff4bc37fa1d24f1fca8244f2e31ec9f0bb7ea6244b185bfaa0b8e6.

`build/mac4-whisper/verify-inference.py` invokes the actual package CLIs on the
existing 11-second public resources/selftest.wav, checks expected keywords and
passes stderr through the actual portable ProgressState parser. Exact arguments,
public-fixture output and backend evidence are retained in scratch. Results:

| Case | Exit | Observed backend | Wall seconds |
| --- | --- | --- | --- |
| CPU, -ng | 0 | cpu | 1.353 |
| Metal | 0 | metal | 12.388 |
| CPU + VAD | 0 | cpu | 0.319 |
| Metal + VAD | 0 | metal | 0.284 |
| Metal executable, -ng | 0 | cpu | 0.334 |

All five cases emit nonempty transcripts containing expected ask/country keywords
and progress reaches 1.0. Metal stderr confirms using embedded metal library and
using MTL0 backend; VAD's later no-GPU message does not overwrite Metal selection.
The forced CPU case proves direct -ng behavior, not automatic retry after a GPU
failure. These short timings include uncontrolled startup/cache effects and are
not sustained-performance or CPU-versus-GPU speed claims.

A second retained verifier, verify-vad-timestamps.py, decodes the existing public
600-second silence fixture using the prior MAC-3 FFmpeg binary after rechecking
its SHA-256, then runs Tiny+VAD on both actual package CLIs. Both produce two
segments confined to the known speech windows [0,11.5] and [299.5,311.5] seconds.
CPU checks 49 nonnegative token timestamp pairs; Metal checks 51. They remain
inside their text segments (allowing 10 ms endpoint precision), with no segment
interpolated across the removed multi-minute silence. Details are retained in
vad-timestamp-summary.json. This is timestamp regression evidence for the public
fixture, not a general transcription-accuracy or full language/catalog result.

## Checks and remaining gates

`.venv/bin/python -m pytest -q tests/unit/test_mac_whisper_recipe.py`: 12 passed.
Tests cover the explicit configuration contract, actual wrong application-repo
commit, changed approved patch hash, extra files, extra hunks in an approved file,
partial patches, untracked additions, pristine and approved-patch input reaching
existing-output refusal, inherited Git identity, in-source output and unknown
backend. Controlled Git probes test rejection without compiling; the real builds
and caller cleanliness supply positive source-closure evidence. Native shell
cases target Darwin; the static contract test is portable. No existing test or
Windows audit behavior was changed, skipped or weakened.

Shell syntax, targeted Ruff lint/format, source policies, docs consistency and
final diff checks pass. All fixture provenance remains in
`tests/fixtures/AUDIO_SOURCES.md`; only public fixtures are used. Raw native
stderr/transcripts in scratch are public-fixture evidence, not a product logging
policy or permission to log user data.

NOT RUN: full five-model catalog, Persian/translation inference, user recordings,
long-file throughput/thermal benchmark, automatic GPU failure retry, trusted app
process launch/cancel/death lifecycle, full GUI, dynamic network observation,
complete redistributed license audit, signed bundle relocation or older OS.
These direct subprocess experiments are not proof of the complete Dusty privacy
boundary or product readiness. Independent QA and PM acceptance are required.
