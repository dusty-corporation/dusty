# M2 Report - Headless core pipeline

## 1. Summary

The offline headless pipeline now supports batch processing, five export
formats, verified models, cancellation, progress, collision policies and crash
recovery. The public engine-v2 prerelease is active, with all five asset hashes
verified and the VAD segment/word timestamp correction enabled. Local tests
passed 76/76; both final code-validation runs passed, including WFP with zero
processing connection events. ThinkPad measurements resolve ISSUE-004 without
changing ADR 0004; no significant recurring Iris Xe startup cost was measured.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Unit acceptance, SPEC 11.3 | met | Export goldens/edge cases, scanning, failures, corrupt state, model rules/hashes, guard, canary and sync detection tested |
| Integration acceptance, SPEC 11.4 | met | Five formats, mixed valid/invalid batch, cancel-current/all, real parent kill/child death/resume, all collisions, Persian Translate |
| CPU/Vulkan agreement | met on desktop | Actual Vulkan comparison passes normalized similarity >= 0.9; hosted CI has no usable device and skips only this hardware-conditional comparison |
| Firewall and WFP, SPEC 11.5 | met | Final PR and push offline jobs pass calibration, guarded self-test/batch, zero processing events and cleanup |
| Canary logs | met | Real canary-named input and vocabulary hint leave neither marker nor input path in app logs |
| Coverage >= 85% per strict package | met | Each package 91.7% or higher; overall 93.9% |
| Startup investigation | met | Owner ThinkPad and desktop measurements; ISSUE-004 closed by PM |
| VAD and Persian fixtures | met | Timestamp regression on both desktop backends; independent-source Persian translation check with Medium |
| Public pinned binaries | met | engine-v2 public downloads match all five verified draft digests; engine-v1 unchanged |

The resume dialog and other GUI work belong to M3. M2 tests the persisted
recovery state and shared coordinator without a GUI.

## 3. What was built

- `core/`, `engine/`, `models/`, `queue/`: typed data, pinned native runners,
  Windows Job Objects, progress/timings, backend probe and per-file CPU fallback,
  verified catalog, scanning, persistence, collision-safe output and recovery.
- `export/`: TXT, SRT, VTT, JSON and DOCX, with line-ending, wrapping, Unicode
  and metadata checks.
- `privacy/`: first-startup audit hook, redacted logging and sync-root detection.
  The static no-network checker still has zero exceptions.
- Self-test, shared headless/dev CLI, Windows batch sleep prevention, interface
  stubs only for V2, and repository-local test app-data isolation.
- Hash-verified dev fetching, Windows WFP CI, startup probe, approved native
  patch, benchmark summaries, developer notes, changelog and deferred backlog.

## 4. Test results

Commands run against publicly fetched engine-v2:

- `uv run python tools/fetch_dev_binaries.py`: three runtime ZIPs and Tiny,
  Small.en, Medium and VAD models verified; published patch/checksum-file bytes
  independently verified as well.
- `uv run python tools/measure_coverage.py`: **76 passed**, 67.55 s locally.
- `uv run ruff check .`: passed; `uv run ruff format --check .`: 70 files checked.
- `uv run mypy`: no issues in 43 source files.
- `uv run python tools/check_no_network.py`,
  `uv run python tools/check_no_huggingface.py`, and
  `uv run python tools/check_licenses.py`: all passed.
- `rg --hidden -n -g '!.git' '\x{2013}|\x{2014}' .`: no output, exit 1
  (no matches).

| Package | Covered/executable lines | Coverage |
|---|---:|---:|
| core | 139/146 | 95.2% |
| export | 130/132 | 98.5% |
| models | 117/124 | 94.4% |
| queue | 409/446 | 91.7% |
| privacy | 78/82 | 95.1% |
| Total | 873/930 | 93.9% |

Final code commit `826a30c`:

- [PR run 39813686035](https://github.com/dusty-corporation/dusty/actions/runs/39813686035):
  green; checks job 119946431618, **75 passed, 1 hardware skip**; coverage matches
  the table; WFP job 119946432163 green with `connection_events=0`.
- [Push run 39813676982](https://github.com/dusty-corporation/dusty/actions/runs/39813676982):
  green; checks job 119946399200 and WFP job 119946399882 passed.
- Native run 39804070663: CPU/Vulkan builds and imports passed;
  GGML_NATIVE=OFF, runtime dispatch enabled, all nine CPU variants present.

### VAD comparison

| Backend | VAD | Words | Outside-span segment words | Word-time violations |
|---|---|---:|---:|---:|
| CPU | On | 44 | 0 | 0 |
| CPU | Off | 62 | 18 | 36 |
| Vulkan | On | 44 | 0 | 0 |
| Vulkan | Off | 62 | 18 | 36 |

Before the fix, VAD-on misplaced 22 segment words; after it, zero, with the
same 44 total words. Those 22 words were a timestamp-mapping error, not proven
hallucinations. Both segment boundaries and reconstructed word intervals are
checked against known speech spans within 0.5 s. See
`docs/pm/benchmarks/m2/engine-v2-desktop.md` for timings and annotation details.

### Startup findings

Owner ThinkPad, i7-1365U/Iris Xe, Tiny, four threads, VAD off, exit 0;
CPU dispatch alderlake:

| Backend | Run 1 s | Run 2 s | Run 3 s | Run 4 s | Run 5 s |
|---|---:|---:|---:|---:|---:|
| CPU | 0.940 | 0.760 | 0.750 | 0.751 | 0.752 |
| Vulkan | 1.000 | 0.627 | 0.617 | 0.633 | 0.644 |

Vulkan load was approximately 85-93 ms; encode 85-92 ms. Desktop Vulkan's
first observed run was 13.935 s, then 0.558-0.579 s. The PM closes ISSUE-004:
M1 inferred fixed overhead from total transcription time, rather than measuring
it. A fresh machine likely pays a one-time shader compile, absorbed by installer
self-test; no direct driver trace proves that mechanism. ADR 0004 stays unchanged.
Measurements are recorded in the two `startup-probe-*.md` benchmark summaries.

## 5. Deviations from SPEC

- ISSUE-005: PM corrected the dev English-only model from nonexistent Tiny.en
  to published Small.en; models-v1 was not modified.
- ADR 0016: PM-approved V1 catalog/defaults supersede the broad candidate list.
  The Persian smoke uses the approved Medium recommendation; Small was unreliable
  across CI hosts. The original keyword assertion remains, with an extra source
  concept required. No decoding behavior was changed to make the test pass.
- ADR 0017: PM-approved audit hook supersedes SPEC 9.2.3 monkeypatching;
  all required socket events are blocked in subprocess tests, and dusty_fetch
  runs separately without inheriting the hook.
- ADR 0018: approved minimal timestamp patch against pinned v1.9.5; no newer
  stable fix existed. BACKLOG.md records replacing it after a verified stable
  upstream fix, including PR 4068 or equivalent.
- Coverage uses the standard-library tracer instead of adding a dependency.

## 6. Issues

| ID | Severity | Status | Resolution |
|---|---|---|---|
| ISSUE-004 | S2 | resolved | ThinkPad probe disproves significant recurring startup overhead; PM retains process per file |
| ISSUE-005 | S1 | resolved | PM corrected Tiny.en to Small.en |
| ISSUE-006 | S1 | resolved | Audit hook accepted; static rule unchanged |
| ISSUE-007 | S1 | resolved | Published engine-v2 patch passes segment/word regressions and WFP |
| ISSUE-008 | S1 | resolved | Recommended Medium passes stronger independent-source translation assertions on both final CI runs |

No open S0/S1 issues remain. Optional improvements and post-V1 scope are in
`docs/pm/BACKLOG.md`.

## 7. Decisions needed from PM/Owner

No unresolved M2 technical decision. PM review and acceptance are requested;
the real Surface Vulkan smoke remains a required pre-M7 condition.

## 8. Actions needed from the Owner

1. Review this report and [PR #3](https://github.com/dusty-corporation/dusty/pull/3).
   The Owner performs any merge after required checks and PM acceptance.
2. Before M7, run the real Surface Laptop 5 Vulkan smoke test and return the
   exit code and actual-backend confirmation. This does not block M2-M6.
3. Optional workspace cleanup approval: an early agreement test wrote a Vulkan
   probe entry to normal `%LOCALAPPDATA%/Dusty/settings.json`. The test now uses
   repo-local app data, verified by the full suite. The existing external cache
   was left untouched after discovery; removing only its `backend_probe` entry
   requires the Owner's explicit approval under the workspace restriction.

No further release publication or desktop/ThinkPad probe run is required for M2.

## 9. Risks for the next milestone

- Initial Vulkan setup may take approximately 13 s on a fresh driver/machine;
  installer self-test must tolerate it and keep progress understandable.
- The native patch needs maintenance until a stable upstream fix passes our
  regression. Its retirement is deferred in the backlog.
- Translation quality varies by model and content; this smoke is not a literary
  translation benchmark or a medical accuracy claim.
- M3 must consume the tested coordinator APIs for dialogs, progress and recovery.

## 10. Time/effort notes

The VAD defect required checking upstream and correcting both segment and
word mapping. Native builds, WFP work and independent pipeline tests progressed
without waiting for hardware results. Hosted CI exposed Small's weak margin
on the Persian poetry fixture; the existing recommended Medium model met the
unchanged and strengthened source checks. Nice-to-haves were recorded in the
backlog instead of expanding M2.
