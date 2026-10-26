# Reproducing a benchmark kit

The historical benchmark kits are private review artifacts, not public release
assets. Build a new kit with tools/bench/package-kit.ps1 from verified CPU,
Vulkan and FFmpeg folders plus the pinned models-v1 manifest. Its parameters
name these inputs explicitly. The script includes only public reference audio;
model weights are separate verified downloads.

run-bench.ps1 refuses to overwrite results and distinguishes public/private
summaries. Private runs retain timings, not transcript output. Quick mode runs
tiny, small, Turbo q5_0 and Large-v3 q5_0 on both backends. A focused thread sweep
uses -Quick -SweepModel small-f16 -Threads '4,8,10'. The kit needs those selected
models. The full historical Quick set includes cut models kept only in the
private archive, so it is not a dependency of the public build or a supported
public download set. A focused Small thread sweep uses the shipped catalog
model. The normal app's default development download is a different test set.

summarize_bench.py scores only the source-text spans in the public fixture's
swineherd-scored-spans.json. The fixture provenance and exact extraction boundaries are in
../../tests/fixtures/AUDIO_SOURCES.md. No human listening pass is substituted
for an independent source-text reference. Do not commit private recordings or
raw benchmark outputs. Keep raw outputs separate from the release source tree.
