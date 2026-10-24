# engine-v3 preparation

ADR 0024 accepted by PM, 2026-10-24. Native run 40110881732 at
d0abc304942255a1d30d741fff0ca98c2c1cdf45; app candidate gate 40125892713.
The draft is Owner-publication-only. engine-v2 remains byte-for-byte unchanged.

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

Additional draft assets: SHA256SUMS.txt, BUILD-PROVENANCE.json, original CPU and
Vulkan CMake caches, ffmpeg-buildconf.txt, MIT/LGPL license texts, unchanged VAD
patch and UTF-8 manifest. Source links and build recipes are in the release notes.
Exact candidate archives include whisper-bench, as they did in validation; it
remains excluded from the installed application. No model/server is included.

Owner-only publication command (do not execute before review):

```powershell
gh release edit engine-v3 --repo dusty-corporation/dusty --draft=false --prerelease --latest=false
```

m6-engine-v3-pins contains only the prepared production pin switch. Do not merge
until PM confirms publication. Verify public assets against these exact hashes,
then integrate the switch and run normal production CI without candidate mode.
