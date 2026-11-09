# 0032 - Reusable pinned Mac inference recipe

Status:Accepted by PM for bounded reproducible build verification,2026-10-31.
Persist MAC-0's demonstrated CPU/embeddedMetal route in a separate Mac recipe.
Use exact whisper_cpp pin and existing patch hash; verify source patch closure,
not merely filenames. Refuse archives inheriting Dusty Git metadata and source
changes beyond approvedpatch. No network/server/CURL/CUDA/Vulkan/RPC targets.
Use system Apple frameworks and existing CMake tool, no new shipped component.
No deletion of existing output or mutation of caller's unverified source.

Record actualsource identity, patch/toolchain/config/output digests and backend
observations. Resolve upstreamdevbanner deliberately without obscuring patched
identity. Tests must reject wrong/dirty sources before build and preserve outputs.
LowerOS/signing/packagedshader/realapp/privacy acceptance remain separate.

## Amendment 2026-11-07: deployment target and reproducibility (MAC10-NATIVE2)

build_whisper.sh now takes an optional macOS deployment target, default 13.3,
passed as CMAKE_OSX_DEPLOYMENT_TARGET. Before this, outputs inherited the SDK
default (26.0), which forced Dusty.app to require macOS 26.

Why 13.3 and not 13.0: ggml-blas calls cblas_sgemm through Accelerate's
ACCELERATE_NEW_LAPACK interface, which exists only on macOS 13.3 and newer.
A probe build at 13.0 warned about it and weak linked
_cblas_sgemm$NEWLAPACK$ILP64; the call has no run time guard, so on 13.0 to
13.2 the BLAS path would crash. The Metal backend is fine at 13.x: residency
sets and the tensor API are behind @available(macOS 15.0) or device family
checks, and bfloat shaders fall back when the Metal language is older than 3.1.
Shaders are embedded and compiled at run time by the system. A probe build at
13.3 with -Werror=unguarded-availability and -Werror=unguarded-availability-new
succeeded, and the recipe now always builds with those two errors enabled.

Reproducibility: C, C++ and assembly flags map the output folder with
-ffile-prefix-map=<output>=/dusty-whisper, so ggml assert messages no longer
embed build paths. Two CPU and two Metal builds into different folders were
identical, and libggml-base, libggml-cpu and libggml-blas are identical between
the CPU and Metal builds. The recipe checks that every output's minos equals
the target and that no output contains its build path. Transcripts and
timestamps of the selftest fixture are unchanged against the native-v2 builds.
Not yet observed: a run on real macOS 13.3 hardware.

## Amendment 2026-11-08: GPUs the Metal engine cannot use (MAC11-GPU)

GitHub's free Mac runners are virtual Macs with Apple's paravirtual GPU. The
pinned engine reports it as family Apple5 with "simdgroup reduction = false"
and "simdgroup matrix mul. = false". Every Apple Silicon GPU reports both as
true. Without them ggml moves matrix multiplication, softmax and normalization
to the CPU and still sends the rest to the GPU. On M2 Pro hosts that works
slowly. On an M1 host the public CI run of the 1.1.0 snapshot stalled inside
the Metal engine until the 90 minute job limit, and another project saw a
GPU hang error on the same runners. That snapshot was never released.

Dusty therefore does not use a GPU without both features. A Metal run is
stopped as soon as its stderr reports either feature false, before any GPU
work, or a known Metal command failure, and the existing CPU retry runs the
job. The GPU check records such a GPU as unsupported with its device name, so
Automatic uses the CPU, and the Mac GPU check now stops after 120 seconds.
Windows is unchanged. The next amendment replaces how tests choose the Metal
rows.

## Amendment 2026-11-08: no Metal engine inside a virtual Mac (MAC11-VM)

The stderr check above was not enough. On GitHub's M1 runners (3 cores) a
Metal run then went for over 20 minutes without the report that would stop it.
The pinned engine prints the GPU name and features only after it compiles its
35 Metal shader libraries. That takes 0.2 seconds on an M2 Mac, and the whole
GPU check took about 12 seconds on GitHub's M2 Pro runners, which suggests the
compile stalls on the M1 runners.

Dusty therefore never starts the Metal engine inside a virtual Mac. It
recognizes one from two sysctls, without starting a process: macOS sets
kern.hv_vmm_present to 1 inside a virtual machine, and GitHub's runners name
their processor "Apple M1 (Virtual)" or "Apple M2 Pro (Virtual)". There, a
Metal request fails on the GPU at once and the existing CPU retry runs the job,
and the GPU check records an unsupported GPU in a virtual Mac, so Automatic
uses the CPU. A virtual Mac on Apple Silicon only has Apple's paravirtual GPU,
so no working GPU is lost. The stderr check stays for any other GPU the engine
reports it cannot use. Tests of the Metal engine itself skip only where Dusty's
own GPU check recorded a virtual Mac; on a real Mac they must pass, and a test
makes Dusty see a virtual Mac on every Mac to check that no Metal engine starts.

## Amendment 2026-11-08: speech detection threads (MAC11-VAD)

The two amendments above did not find the cause of the stalls. A probe in the
public repository dusty-corporation/dusty-staging (run 42531936313) timed the
published engine-macos-v1 on three of GitHub's M1 runners (3 cores), with no
Dusty code. The CPU engine transcribed 11 seconds of speech in 0.5 to 1.6
seconds with 1 to 3 threads but took 13 to 14 seconds with 4. Speech detection
over the ten minute test recording did not finish in 8 minutes; on an M2 Mac
the same run takes about 2 seconds. The Metal engine finished the 11 seconds of
speech in 17 to 35 seconds: slow, but it did not stall.

The cause is in whisper.cpp. Speech detection creates its own context with the
library default of 4 threads and ignores the thread count of the run, and
upstream has the same default. With more threads than cores, ggml's threads
wait for each other at every step, and speech detection takes about 18,750
small steps over ten minutes of audio. Both tests that stalled use speech
detection on that recording. It always runs on the CPU, inside the Metal
engine too, so the Metal runs of 1.1.0 and 1.1.1 stalled in the same place.

The Mac engine therefore gets its own complete approved patch,
native/patches/0002-vad-timestamps-and-threads.patch, pinned in the
[whisper_cpp_macos] section of native/versions.toml: patch 0001 plus one line,
so that speech detection never uses more threads than the run. Dusty runs at
most 4 threads, so where it runs 4, as on every Mac with at least 4
performance cores, nothing changes. Transcripts and timestamps from the
patched engine match the published one exactly with 1 to 4 threads. On two M1
runners (staging run 42542594477) the patched engine finished the same speech
detection run in 2.1 to 3.3 seconds with 1 to 3 threads, with the same
transcript as on the M2 Mac, while the published engine was still running at
300 seconds and the patched engine with 4 threads at 180 seconds. The rebuilt
engine, engine-macos-v2 (staging run 42542628054), differs from
engine-macos-v1 only in libwhisper. The Windows engine keeps patch 0001 until
its next build, so on a Windows PC with fewer than 4 logical processors, Skip
long silences can still be very slow.

The changes of the two amendments above stay: inside a virtual Mac the CPU is
much faster than the paravirtual GPU, so the CPU is the right engine there.
