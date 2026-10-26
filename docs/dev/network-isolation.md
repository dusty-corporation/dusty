# Windows offline audit

Every push and PR runs the separate `offline` job in `ci.yml`. It fetches the
verified assets before blocking networking. The audit harness refuses to run
outside a disposable GitHub runner or without administrator rights.

The harness saves the audit policy inside ignored `build/`, enables Filtering
Platform Connection success/failure auditing by GUID, and creates outbound block
rules for the venv and base Python images, both whisper-cli packages, FFmpeg,
and FFprobe. It restores audit policy and removes only its own named rules in
a `finally` block. It does not change repository settings or local desktop
firewall settings.

A separate control process, which never imports Dusty, attempts TCP to TEST-NET
192.0.2.1 port 9. The harness requires a matching blocked event 5157 before
testing Dusty. This proves that both blocking and auditing are active; lack of
events cannot silently count as a passing test. The control PID and its audit
window are excluded from Dusty's window.

The real guarded entry point runs `--self-test` and `--headless-batch` directly
under Python, with verified models and the public JFK fixture. Events 5156 and
5157 after the audit marker are matched against the complete image path suffix,
including Windows device-style paths. Any matching processing connection is
an S0 failure. Only counts and pass/fail status are emitted; no address, path,
raw event XML, transcript, or native stderr is printed or uploaded. The event
parser is checked with synthetic allowed, blocked, unrelated-image, old-record,
and control-PID cases before the real audit.

Microsoft references verified for this implementation:

- [WFP audit events and subcategory GUID](https://learn.microsoft.com/en-us/windows/win32/fwp/auditing-and-logging)
- [Blocked connection event fields](https://learn.microsoft.com/nl-nl/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-5157)

The Python variant is M2's pre-packaging acceptance. M5 must apply the same
test to the installed `dusty.exe` bundle. A successful parser test alone is
not evidence that the dynamic audit passed; record the workflow run ID.
