# M4 Interim 1 - Downloader-only prework

## 1. Summary

The PM-authorized downloader scope is implemented and pushed on m4-downloader,
based on m3-gui at 9efea1f. Download/verify use the standard library only.
The M3 report now correctly records steps 6 and 17 as passed (18 original
checks passed, 2 failed); their separate Tab/extra-Start findings remain fixed.
No GUI or offline-runtime source changed, m3-gui is unchanged, and no PR was opened.
This is not completion of the full M4 milestone; Model Manager is out of scope.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Download/verify CLI, JSON-lines and exit codes | met | Installed dusty-fetch verify succeeded; docs/dev/downloader.md specifies the protocol. |
| HTTPS, exact hosts, redirect/TLS checks | met | Actual GitHub 302 to release-assets.githubusercontent.com; local TLS and disallowed redirect/host tests. |
| Resume, integrity, disk, cancellation | met | Interrupted Range resume, ignored/malformed Range, mismatch deletion, disk full, Ctrl+C, process termination and lock-release regressions. |
| Offline package boundary | met | Unchanged zero-exception static check, import trap across every dusty module, guarded-parent/separate-fetch process test, WFP green. |
| One real Tiny integration, CI only | met | Run 39857544641: explicit real_network step, 1 passed in 3.87 s. |

## 3. What was built

src/dusty_fetch/downloader.py and __main__.py, console entry metadata, localhost
TLS fixtures/tests, CI opt-in integration and docs/dev/downloader.md. No new
dependency, native component or manifest pin. Exact allowed hosts: github.com
and release-assets.githubusercontent.com; HTTPS/443 only, every redirect
checked before following, certificate/hostname verification using default
Windows CA/ROOT trust. No runtime allowlist or trust bypass is exposed.

Parts are renamed atomically only after whole-file SHA-256 and size match.
Mismatched parts are deleted; interrupted parts remain resumable. An existing
final is preserved until a verified replacement is ready. OS locks release on
termination. Forced termination may have no final JSON event, but cannot create
an unverified final. Exit codes and direct/no-proxy behavior are documented.

## 4. Test results

- Final local full suite: **129 passed, 1 skipped in 125.17 s**; the skip is the expressly CI-only network test.
- Ruff check/format passed (92 files); mypy passed (55 source files); all three policy checks passed. The no-network checker has zero exceptions.
- Required-package coverage: core 93.7%, export 98.5%, models 94.4%, queue 93.0%, privacy 95.2%; combined **893/948 = 94.2%**.
- [Final CI run 39857544641](https://github.com/dusty-corporation/dusty/actions/runs/39857544641): normal suite **128 passed, 2 skipped in 167.81 s** (hosted Vulkan comparison and network opt-out); explicit Tiny integration **1 passed in 3.87 s**.
- WFP: `selftest passed; batch passed; gui passed; connection_events=0`, with calibration and cleanup passed.
- CI downloaded and verified Tiny from models-v1: 77,691,713 bytes, SHA-256 `a38bcb31dcd68cf7d9a630e2148ccf0656f95ac87c5bcbc4064a689f383b2059`. Locally, the installed CLI verified the existing cached Tiny without network.

## 5. Deviations from SPEC

Only the PM's limited downloader prework is performed. The Owner's current M3
brief is preserved; docs/pm/briefs/M4-downloader-authorization.md records the
direct authorization. GUI integration, packaging and later milestones are untouched.

## 6. Issues

No unresolved downloader issue or new S0/S1. A stub-specific guard test initially
failed because no-argument startup is now a usage error; it was updated to a
real verify command while strengthening guarded-parent/unguarded-child assertions.
No test was weakened or disabled.

## 7. Decisions needed from PM/Owner

None for this scope. A future release redirect host must be verified before
changing the allowlist; there is no wildcard fallback.

## 8. Actions needed from the Owner

None required for the downloader interim. M3's targeted re-test remains pending.
The report correction is on m4-downloader, preserving m3-gui as requested.
No PR against main was opened; the branch is ready for later PM review.

## 9. Risks for the next work

Later Model Manager code must spawn this CLI and consume JSON-lines rather than
import dusty_fetch into dusty. Enterprise proxy support is not enabled; future
support needs an explicit host/credential policy. Test certificates are public,
localhost-only fixtures loaded in test SSL contexts, never installed into a store.

## 10. Time/effort notes

Most work was redirect/range validation, interruption safety, and adapting the
existing process-isolation regression to a functional CLI. Implementation and
CI evidence end at cf299a8; later documentation commits may queue fresh checks.
Stopped at the requested downloader-only boundary.
