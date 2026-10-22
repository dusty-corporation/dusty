# engine-v2 desktop validation

Date: 2026-10-22. Owner desktop, tiny, four threads, v1.9.5 plus ADR 0018's
hash-pinned patch. Native run 39804070663 passed both build/import jobs.
Both printed GGML_NATIVE=OFF, GGML_BACKEND_DL=ON and
GGML_CPU_ALL_VARIANTS=ON; all nine dispatch DLLs were present.

## JFK and VAD

With `DUSTY_BIN_DIR=build/engine-v2`, CPU validation used
`uv run python tools/measure_coverage.py`: 57 passed, overall strict coverage
91.9%. With `DUSTY_TEST_BACKEND=vulkan`,
`uv run pytest tests/integration/test_engine_smoke.py tests/integration/test_vad_silence.py -s`
passed both tests. JFK keywords were checked without printing transcript text.

| Backend | VAD | Process s | Words | Segments | Outside-span words | Word timestamp violations |
|---|---|---:|---:|---:|---:|---:|
| CPU | On | 4.781 | 44 | 2 | 0 | 0 |
| CPU | Off | 8.156 | 62 | 20 | 18 | 36 |
| Vulkan | On | 6.703 | 44 | 2 | 0 | 0 |
| Vulkan | Off | 3.282 | 62 | 20 | 18 | 36 |

Before the fix, VAD-on assigned 22 segment words outside the reference speech
spans. After the fix it assigns zero; total VAD-on words remain 44. The
22-word anomaly was a timestamp error, not evidence of extra hallucinated
words. VAD-off has 18 additional words in this fixture.

The regression checks both segment boundaries and every reconstructed word
interval against two known speech windows with 0.5 s tolerance. It also
requires both passages and at least 40 timed words. The spoken reference ends
at 10.5 s and 310.5 s, as in the retained M1 JFK reference, rather than at the
11 s container boundary. The first Vulkan run exposed that annotation error:
its 310.48 s end was 0.52 s before the container end. The reference was
corrected; the 0.5 s tolerance was retained. The original broad-window
22-word check is retained in the historical pre-fix summary.

## Startup probe

`pwsh -NoProfile -File tools/bench/startup-probe.ps1 -BinDir build/engine-v2`
completed ten runs, exit 0. Every run selected Haswell; every Vulkan row
confirmed actual Vulkan selection. No driver cache was cleared, so these
are warm-cache regression results, not evidence of cold-start improvement.

| Backend | Run | First progress s | Load ms | Encode ms | Decode ms | Engine total ms | Wall s |
|---|---:|---:|---:|---:|---:|---:|---:|
| CPU | 1 | 0.544 | 81.6 | 236.9 | 0.0 | 496.6 | 0.560 |
| CPU | 2 | 0.546 | 81.8 | 237.0 | 0.0 | 502.7 | 0.561 |
| CPU | 3 | 0.653 | 81.3 | 236.4 | 0.0 | 496.6 | 0.668 |
| CPU | 4 | 0.545 | 82.4 | 239.4 | 0.0 | 501.1 | 0.560 |
| CPU | 5 | 0.637 | 85.2 | 228.9 | 0.0 | 492.9 | 0.652 |
| Vulkan | 1 | 0.505 | 153.1 | 15.0 | 0.0 | 311.8 | 0.554 |
| Vulkan | 2 | 0.486 | 137.2 | 15.0 | 0.0 | 298.8 | 0.537 |
| Vulkan | 3 | 0.596 | 137.4 | 16.0 | 0.0 | 298.1 | 0.644 |
| Vulkan | 4 | 0.485 | 138.1 | 15.1 | 0.0 | 300.8 | 0.534 |
| Vulkan | 5 | 0.490 | 140.0 | 14.9 | 0.0 | 302.2 | 0.539 |

ThinkPad baseline results remain pending and do not block draft preparation.
