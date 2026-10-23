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
