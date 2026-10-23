# M5 Interim 3 - Approved remediation checkpoint, vendor download blocked

## 1. Summary

The official Microsoft runtime license document returned **HTTP 403 Forbidden**
despite approved network escalation. Per the Owner's earlier instruction, work
stopped without a workaround (ISSUE-016). The stdlib DOCX writer is implemented;
the split bundle passes the local PE gate, GUI smoke and CPU/Vulkan self-test
with all three optional extensions excluded. License/SBOM updates and final CI
integration remain unfinished; ISSUE-014/015 are not falsely closed.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| ADR 0019: stdlib DOCX, python-docx test-only | locally met, final CI pending | 5ba88dd; unchanged semantic goldens and escaped Unicode/openability/empty metadata tests passed. |
| ADR 0021 exact platform pins | locally met | Both approved hashes/function sets pinned; 35 offline PEs checked, gate passed. Complete list in docs/dev/packaging-offline-pe-remediation.md. |
| No optional socket extensions or OpenSSL in offline runtime | locally met | _overlapped, _multiprocessing, select, _socket, _ssl and OpenSSL absent; packaged GUI and CPU/Vulkan self-test passed. |
| Separate onedir runtimes, no lxml/Mesa/UCRT | locally met | dist/Dusty/dusty and dusty-fetch, shared bin/resources; layout gate passed. |
| Full suite | met locally | Already-running suite completed: 142 passed, 1 CI-only skip, 94.4% strict-package coverage. |
| Final CI PE gate and pinned Python setup | pending | Local gate exists; workflow integration is not completed. |
| ADR 0020 license text, libffi notice, updated inventory/SBOM | blocked | First vendor document request failed; no files or notices fabricated. |
| Final packaged WFP and license gates | not met | Previous spike evidence is historical; no final result claimed for remediation. |
| Persian Owner confirmation on m3-gui | met | Docs-only 2a6e065 pushed; AUDIO_SOURCES.md, M3 report and ledger record complete Farsi quatrain [107, 122) s. |

## 3. What changed

- DOCX uses zipfile and escaped XML, title/subtitle, optional timestamps,
  Calibri 11 body, paragraph grouping and empty core properties. python-docx
  remains available to tests, with no runtime dependency or new package.
- Separate PyInstaller COLLECT folders isolate downloader TLS dependencies.
  Frozen runtime paths resolve shared bin/resources from their parent.
- Optional async/multiprocessing/socket/TLS modules are excluded from Dusty.
  File-only bounded logging replaces logging.handlers, whose eager socket
  transport import would otherwise pull in networking support.
- CPython's built-in SHA fallback replaces its optional _hashlib/OpenSSL path
  in the offline bundle. The real model hash verification/self-test succeeded.
- Mesa/ANGLE collection and Windows UCRT/API-set copies are omitted.
  ADR 0021 and its two exact pins are recorded; other exceptions were not added.

## 4. Results before the download failure

- Existing DOCX export goldens: 9 passed before adding the new edge regression.
- DOCX plus privacy logging regressions: **14 passed**.
- Last completed mypy: 60 source files passed before the final PE gate run.
- `uv run python tools/check_bundle.py dist/Dusty`: passed.
- `uv run python tools/check_pe_imports.py dist/Dusty/dusty`: **35 checked,
  passed**, only the two exact approved platform primitive import sets.
- `uv run python tools/smoke_packaged_gui.py dist/Dusty`: window created and
  closed successfully with excluded optional extensions.
- Packaged `dusty.exe --self-test --model tiny --backend vulkan`: **exit 0**,
  exercising CPU and Vulkan on the desktop and logging only `status=done`.
- The full suite already running at the vendor error completed: **142 passed,
  1 CI-only skip**, 128.32 s; strict-package coverage **94.4%** (923/978).
  No additional run was launched after the failure.

## 5. Blocker and exact error

Official source page:
https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/

Its linked document:
https://visualstudio.microsoft.com/wp-content/uploads/2021/09/Visual-C-Runtime-2015-2022-License-1.docx

```text
urllib.error.HTTPError: HTTP Error 403: Forbidden
```

The network escalation was approved; the server request still failed. No alternate
request or download method was tried. The sandbox uv cache permission error earlier
in the turn was resolved by the approved escalation; it was not the stop condition.

## 6. Issues

| Issue | Status |
|---|---|
| ISSUE-014, lxml | Runtime removal implemented locally; closure awaits final verification. |
| ISSUE-015, platform imports | ADR 0021 accepted and local exact-pin gate passes; final CI verification pending. |
| ISSUE-013, notices | Approved remediation underway; license gate not yet cleared. |
| ISSUE-016, vendor HTTP 403 | Owner action needed. |

## 7. Decision/action needed from the Owner

Provide the official Microsoft license document/text inside the repository, or
specify an approved way to obtain it. No new runtime, allowlist or privacy-policy
decision is requested. After this access blocker is resolved, finish the notices,
split-layout inventory, pinned CI setup and both required final gates.

## 8. Scope and branch safety

Implementation checkpoint stays on m5-packaging-spike; no installer, PR or
binary upload. m4-downloader is unchanged. The requested m3-gui changes were
documentation only. The Owner's eight-check M3 re-test remains active; no stale
20-step desktop walkthrough was requested.

## 9. Risks

This is a partial checkpoint, not an approved release or a claim of green final
CI. The old inventory script/workflow still require integration with the split
layout, and complete notices remain mandatory before license clearance.

## 10. Effort notes

The required platform policy and optional-module exclusions worked locally.
The first vendor-license request blocked completion; no workaround was attempted.
