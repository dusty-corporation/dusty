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
