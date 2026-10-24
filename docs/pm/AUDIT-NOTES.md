# Independent audit notes (M6)

Non-urgent review items, not accepted defects or waivers. Add evidence and
promote an item to an issue if it affects correctness, privacy or licensing.

1. **ModelRegistry cache API:** app/model_manager.py reaches into the private
   ModelRegistry._verified cache for invalidation and forced re-hashing. Review
   a public invalidation/verify API and ownership across Qt worker threads.
2. **Worker/view separation:** app/model_manager.py combines JSON protocol,
   child lifecycle and dialog state. Review the boundaries and failure paths
   independently, including cancellation during final local verification.
3. **Prepared-state compatibility default:** Prepared.vad_installed defaults to
   True for existing injected callers; the real preparer computes it explicitly.
   Audit new callers so an omitted flag cannot mask missing voice detection.
4. **Qt task retention:** MainWindow and ModelManager retain completed QThread
   objects for safe lifetime handling. Review long-session retention and teardown;
   current acceptance tests cover the normal close/cancel paths.
5. **Installer cleanup ownership:** the M5 helper deliberately preserves unknown
   content and refuses corrupt protection metadata or reparse points. Review
   leftover reporting, uncommon output locations and mutation races independently;
   recursive wildcard deletion is intentionally absent.
6. **Installer ABI boundary:** Inno 6's PE32 Job Object record is explicitly
   sized and architecture-gated. Review marshalling and cancellation/termination
   on a standard-user VM before treating the draft as installer acceptance.

7. **Installer runtime attribution:** ADR 0023 verification uses pinned upstream source/build selection and exact received runtime hashes, not a recovered linker map or independent reproducible Inno build. Audit the selected units, notice/source archive and the boundary between installer-only exceptions and the processing-app gate.

- M5: the standalone PowerShell/C# hardware diagnostic and production Python
  probe share the same checked ABI/classification rules but have separate code.
  Audit future changes for drift; production remains the guarded Python entry.
- M5: review-only Inno page navigation uses the production controls with synthetic
  progress/outcomes and never installs; keep it separate from acceptance evidence.

- M5: the native page controller encodes asynchronous stages as integers. Review
  transition coverage, stale result handling and repeated retry/cancel scenarios
  independently; the UI review executable is not a failure-injection harness.
- M5: temporary extraction precedes the bounded driver probe. Measure full page
  entry time on a slow clean machine; driver deadlines alone do not measure disk
  extraction. Do not extrapolate the standalone probe timing into install timing.

- M5: native license-viewer links. Pinned Inno RichEditViewer.pas EN_LINK handling
  invokes ShellExecute to open the default browser after an explicit link click.
  Full terms are already bundled locally. No link was clicked and no network
  activity was observed from Setup. Independently review whether to disable
  auto-link activation for a stricter offline Setup experience; this external
  browser action is outside the processing-image WFP attribution.
- M5: Inno partial cleanup ignores DeleteFile's failure return. Normal cancellation
  is covered, but a future audit should inject a locked/permission-denied partial
  and verify that any preserved file is explained without promising removal.

## M5 follow-up audit notes

- Work ownership currently uses preflight reparse/inventory checks, not OS handle-relative
  traversal. Review concurrent path replacement and two simultaneous Dusty instances in M6.
- Queue relative_dir is persisted input. Audit containment of restored relative paths under
  the explicitly chosen output folder, including manually edited queue metadata.
- M5 local pytest-qt event-loop test emits Windows diagnostic 0x8001010d under
  faulthandler, while completing with exit 0. Full source: 302 passed/1 skip;
  targeted recheck: 1 passed. Review COM/window event interaction on this desktop
  in M6. No cause, product crash or test suppression is claimed.
- M5 interrupted upgrade: the purpose/hash recovery receipt stays until a new
  installer successfully resumes cleanup. Review uninstalling an older version
  instead of resuming that interrupted transition; conservative recovery metadata
  may remain. Normal completed upgrade/uninstall gates require no such leftovers.

- M5 atomic writes: abrupt exit before replace can leave a unique .dusty-tmp
  beside the destination, while the original stays intact. Do not sweep output
  folders or guess ownership from that suffix; review explicit recovery ownership
  in M6. Ordinary failed writes remove only their own exclusive temporary file.

## M6 engineering dispositions, 2026-10-24

The entries above are retained as the original review questions. This table
records each outcome. "Acceptable for V1" describes an engineering assessment
within SPEC 9.1, not a new NN exception or a substitute for PM acceptance.

| Item | Disposition and reason | Evidence / remaining limit |
|---|---|---|
| 1. Registry private cache | Fixed: public invalidate serializes with hash verification. | 989a5b6; same-size/same-mtime tamper and forced-rehash tests; manager no longer touches _verified. |
| 2. Worker/view separation | Acceptable for V1: process/protocol state stays in the worker, widgets receive only validated progress/results. A larger controller refactor adds risk without changing the boundary. | Local TLS success/cancel/resume/hash/protocol tests, forced GUI-death and packaged WFP checks. Cancel during local hash cannot publish an unverified final. |
| 3. Prepared VAD default | Fixed: omitted state is false; real preparer computes it explicitly. | 2f12720; positive fixtures now declare VAD; missing-flag regression and 67 GUI/manager tests. |
| 4. Completed QThreads | Acceptable for V1 with a known retention cost: wrappers are retained through the window lifetime to avoid destroying a running thread. One BatchWorker serves a whole run, not every recording. Models/audio are in native children and not stored in these wrappers. | Real cancel/close/forced-death/resume and 200 ms event-loop tests; repeated-action memory is not claimed bounded. Independent audit should inspect very long interactive sessions. |
| 5. Cleanup ownership/leftovers | Fixed boundaries plus conservative V1 behavior: unknown/changed/linked/protected content stays. Guessing ownership would violate NN-7. | All original ISSUE-020/023/025 regressions and 49 OS adversarial cases retained; native installed preflight/receipts; ISSUE-028 normal/extended namespace equality repaired at 8818032 and both native refusals passed in 40124502580. |
| 6. PE32 installer ABI | Acceptable pinned ABI, not a guess: compiler/architecture gate plus sized Job records, suspended assignment and cancellation tests. | M5 source/build verification; actual ThinkPad .14 no-UAC, graphics/CPU self-tests and uninstall pass. Fresh standard-user VM still pending. |
| 7. Installer attribution | Acceptable under PM-approved ADR 0023: exact runtime hashes, reviewed upstream build selection and notices/source retention. It is not a recovered linker-map claim. | Unchanged installer-wide allowlist and license gate; new compiler/hash/unit selection requires PM review. |
| Standalone/production probe drift | Same verified physical-device rules and ABI; standalone is diagnostics only, never bundled or called by app. | Existing classification fixtures and real ThinkPad model-free PASS; a change must update both. Source parity remains an independent-audit check. |
| Review-only navigation | Acceptable separate evidence tool: compile-time ReviewOnly disables installation and uses synthetic states. | Generator tests and archive PNG/README gate; accepted M5 images are not failure-injection acceptance. |
| Wizard integer stages | Acceptable for V1 with gated transitions: result handling occurs only after the active process handle signals. Retry/cancel close/join the previous child before proceeding. | Real-prefix cancel/retry, failure, CPU fallback, selected-model tests and registered uninstall UI test; no synthetic image counted as execution evidence. |
| Probe extraction timing | Driver timeout is bounded; complete disk extraction time is not inferred from it. | Owner ThinkPad successfully reached pre-selected Turbo; no precise total latency was supplied. Owner records unexpectedly slow clean-machine behavior; no fabricated timing. |
| License-view links | Acceptable explicit user action in Setup: bundled full texts are readable locally; clicking an upstream link may open the user's browser. This is not a background processing connection. | Pinned RichEditViewer source reviewed. WFP attribution does not claim to include the external browser. About's new repository address is selectable plain text, not an active link. |
| Ignored partial-removal failure | Fixed: boolean/nonzero helper result, checked Inno outcome and specific Model Manager retained-prefix reason. | Actual exclusive Windows handle test, post-release deletion and generator test. A normally closed app cannot promise OS-denied deletion succeeded; documented retained public prefix. |
| Handle-relative mutation races | Static reparse checks remain; same-account malicious replacement between checks is outside SPEC 9.1. No claim of resistance to that attacker. | Junction/symlink, locks, read-only files and abrupt-exit matrix. New OS lease prevents ordinary concurrent startup cleanup from removing a live instance's work. |
| Concurrent instances | Work cleanup is protected by an OS-held lease, released on crash. Shared settings/queue remain a single-profile workflow; two windows are not a concurrent queue editor. | Real second-process preservation, actual interpreter kill and orphan recovery test. Do not imply independent shared-profile queues are supported. |
| Restored relative_dir | Fixed: reject parent traversal, rooted and drive-relative paths in load and output planning. | Quarantine/no-output tests; Windows root-without-drive covered explicitly. One early test attempted outside-root mkdir; sandbox denied it and no file was created; corrected regression uses pure planning. |
| Qt 0x8001010d | Unresolved, ISSUE-027 S2. Three isolated M6 runs did not reproduce it. HRESULT name is not its native producer or a root cause. | Passive native module/offset observer leaves dispatch/faulthandler unchanged. Report actual captures/results; no suppression, invented cause or false closure. |
| Older uninstall after interrupted upgrade | Acceptable conservative V1 residue: public license/ownership recovery metadata can remain if the user uninstalls the old version instead of resuming the interrupted upgrade. Removing uncertain contents is worse than retaining them. | Actual os._exit between unlinks and safe retry tests; normal completed upgrade/uninstall still require clean owned inventory. Document retention rather than sweeping directories. |
| Crash .dusty-tmp | Acceptable V1 safety tradeoff: a crash before atomic replace can leave an exclusive temporary beside a destination; final file stays old-complete or new-complete. No suffix-based deletion in transcript folders. | Before/after replace crash tests and locked/read-only original preservation; privacy guide documents local retention and no secure erasure. |

No decision here permits new dependencies, broad network/PE/license exceptions,
source-recording deletion or automatic output-folder sweeps. The unresolved
native engine activation (ISSUE-026) and Qt producer (ISSUE-027), plus Owner
hardware/VM sign-off, remain explicit report gaps.
