# engine-v3 provenance and activation

ADR 0024 accepted by PM, 2026-10-24. Native run 40110881732 at
d0abc304942255a1d30d741fff0ca98c2c1cdf45; app candidate gate 40125892713.
The maintainer published engine-v3 as a prerelease on 2026-10-24. engine-v2 remains
byte-for-byte unchanged; published CPU/Vulkan/FFmpeg hashes below are verified.

`tools.prepare_m6_candidate.candidate_archives` checks the pinned manifest,
every native member, unexpected files, deterministic archive size and SHA-256
before returning either package. It does not stage binaries or change pins.
Original native artifacts, not a rebuild, are the input. STORED ZIP packaging is
intentional: preserve the exact previously gated archive bytes and hashes.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| whisper-cpu.zip | 13225699 | b47ec54df7ecb09b341bb7abc5f0f461f746f4bfe72b4873d5843340b9cef910 |
| whisper-vulkan.zip | 58828109 | 0e8f26c55c4abd7b708af1106027c2d75ed2d4592f103e10263f08e0c8d523c7 |
| minimal-ffmpeg.zip | 4310689 | d687eb1e7403b6ab9c444118c055ac99521ea34782f52538787690d1e53da40c |

Additional release assets: SHA256SUMS.txt, BUILD-PROVENANCE.json, original CPU and
Vulkan CMake caches, ffmpeg-buildconf.txt, MIT/LGPL license texts, unchanged VAD
patch and UTF-8 manifest. Source links and build recipes are in the release notes.
Exact candidate archives include whisper-bench, as they did in validation; it
remains excluded from the installed application. No model/server is included.

Publication by the maintainer was confirmed with isDraft=false and isPrerelease=true;
source remains d0abc30 / native run 40110881732. Do not republish/edit it.
The isolated production-pin commit 299fea3 was integrated as f427da5 on
m6-hardening-main, based on actual main after M5 PR #6. Normal CI now fetches
these public assets and runs without candidate mode. See M6-report.md for the
final production/PR gates and consolidated maintainer session.
