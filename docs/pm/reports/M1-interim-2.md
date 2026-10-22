# M1 Interim Report 2 - Awaiting ThinkPad public results

## 1. Summary

The Phase B scoring and benchmark kit corrections are complete, and PR #2 checks passed. Desktop public CPU and Vulkan WER now score only documented Project Gutenberg spans, with model-derived introduction, songs, and outro excluded. The new `bench-kit-m1b` is uploaded as a draft; the original draft remains intact. The ThinkPad public results folder is empty, so the M1 gate table and proposed catalog cannot be completed yet. Per the PM instruction, work pauses for the Owner's ThinkPad files.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| ThinkPad proxy and RTF gate | met as PM decision | `docs/pm/benchmarks/m1/README.md`: i7-1365U, Iris Xe 96EU, 32 GB, estimated 20% faster than target Surface; proxy threshold RTF 0.8 |
| Source-text-only WER | met for supplied desktop public runs | `swineherd-scored-spans.json`; 20 desktop public JSON files scored; four focused tests passed |
| Public/private result separation and overwrite refusal | met | Local public and private smoke tests created distinct names; repeat public run exited 1 before overwriting |
| Quick mode | met | Local extracted-kit test selected four model IDs and completed CPU and Vulkan runs with a short public fixture |
| New draft benchmark kit | met | [Draft `bench-kit-m1b`](https://github.com/dusty-corporation/dusty/releases/tag/untagged-37ba07ac5cef03ef1fcd), 46,254,971 bytes, SHA-256 `16f94ad209be637ae41e1dda61b619d68e4b32a2bf2e8010ad848e64efaad1cc` |
| Full desktop and ThinkPad gate table | blocked | `docs/pm/benchmarks/m1/thinkpad-public/` contains no files yet |

## 3. What was built

- Scored-span configuration and token-time WER calculation in `tools/bench/summarize_bench.py`, with source lines and audio intervals documented in `docs/pm/benchmarks/m1/README.md`.
- `run-bench.ps1` now includes sample type in summary filenames, refuses to overwrite existing summaries or public JSON, redacts the public JSON model path, and supports `-Quick` across CPU and Vulkan.
- The revised kit is a new draft release. The prior `bench-kit-m1` draft was retained.
- [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md) records the PM's preliminary Iris Xe startup-cost observation for M2 investigation.

## 4. Test results

- Local: Ruff lint and format passed, mypy passed, pytest 17/17 passed, and all three policy checks passed.
- PR #2: general CI runs [39714754109](https://github.com/dusty-corporation/dusty/actions/runs/39714754109) and [39714758661](https://github.com/dusty-corporation/dusty/actions/runs/39714758661), [FFmpeg run 39714758771](https://github.com/dusty-corporation/dusty/actions/runs/39714758771), and [native CPU/Vulkan run 39714758674](https://github.com/dusty-corporation/dusty/actions/runs/39714758674) all passed.
- Desktop public results: ten models on each backend, 20 engine JSON files, with corrected scores in `desktop-public/accuracy-cpu.md` and `accuracy-vulkan.md`. Desktop private results contain ten timing rows per backend and no JSON or transcript.
- An extracted copy of `bench-kit-m1b.zip` passed a public tiny-model CPU smoke test. A local Quick test with a temporary test manifest covered four model selections on both backends. These are software checks, not substitute hardware benchmarks.

## 5. Deviations from SPEC

- The PM approved ThinkPad X1 Carbon as the M1 Surface proxy and set RTF 0.8 as the proxy threshold. The real Surface smoke test is deferred and does not block M1.
- WER excludes the non-Gutenberg spoken introduction, three songs, and outro instead of requiring a listening correction to model-derived wording.

## 6. Issues

| ID | Severity | Status | Summary |
| --- | --- | --- | --- |
| [ISSUE-003](../issues/ISSUE-003-native-illegal-instruction.md) | S1 | resolved | Portable runtime CPU dispatch passed the Owner desktop retest. |
| [ISSUE-004](../issues/ISSUE-004-iris-xe-startup-cost.md) | S2 | open | Apparent Iris Xe per-run startup cost; investigate in M2 without changing ADR 0004 now. |

## 7. Decisions needed from PM/Owner

1. No GO or NO-GO decision yet. The PM should decide after the complete ThinkPad public CPU and Vulkan results support a full RTF and WER table.

## 8. Actions needed from the Owner

1. Place the ThinkPad public CPU CSV, Markdown summary, and matching `public-*.json` files for every candidate in `docs/pm/benchmarks/m1/thinkpad-public/`. The folder is currently empty here; please also add the promised Vulkan files. The new runner's filenames include `public` and backend; older files are acceptable if their model rows and JSON match.
2. Tell me when copying is complete. I will compute source-text-only WER for each ThinkPad public run, complete the full two-machine table and proposed model catalog in `M1-report.md`, then stop for the PM's gate decision.

## 9. Risks for the next milestone

- The proxy is estimated to be about 20% faster than the real Surface; the later Surface smoke test may reveal a different Vulkan or CPU result.
- ISSUE-004 could make batches of short files slow even if full-length RTF clears the gate.
- Desktop Large-v3 quantized Vulkan WER varies from its CPU score on this clip; the full report should compare candidate accuracy and backend behavior before proposing a catalog.

## 10. Time and effort notes

The original reference included model-derived passages, so scoring required source-text line ranges and timestamped token filtering. The first runner also gave public and private summaries the same names, which required output preflight and a new draft kit.
