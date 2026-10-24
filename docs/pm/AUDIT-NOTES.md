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
