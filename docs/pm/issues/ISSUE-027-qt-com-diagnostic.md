# ISSUE-027 - Historical Qt COM diagnostic needs native producer evidence

- Severity: S2, tooling diagnostic; no demonstrated app crash
- Milestone: M6
- Status: Investigation, not resolved
- Environment: Owner desktop, Python 3.12.11, PySide6 6.9.2

## Evidence

Historical M5 pytest stderr reported Windows code 0x8001010d during qtbot.wait
in test_real_batch_event_loop_gap_never_exceeds_200ms. The test and process
finished successfully. The Python stack identifies the message pump, not the
native producer. Three M6 isolated comparisons (native, offscreen, sandbox)
passed without that diagnostic. Nothing has been suppressed or disabled.

Microsoft names the code RPC_E_CANTCALLOUT_ININPUTSYNCCALL: a COM outgoing call
while dispatching an input-synchronous call. This is the meaning of the HRESULT,
not a proven explanation of which Qt/Windows component produced it:
[Winerror reference](https://learn.microsoft.com/en-us/windows/win32/com/com-error-codes-3),
checked 2026-10-24.

## Investigation and remaining evidence

tools/trace_qt_hresult.py passively captures native module/offset frames if the
same exception recurs during pytest. It returns EXCEPTION_CONTINUE_SEARCH,
leaves faulthandler enabled, and records no arguments, paths or user content.
An empty capture is not a root-cause finding. Do not close this issue based on
the HRESULT's name, an unreproduced run or a hypothesis about COM/accessibility.
M6 report must name this unresolved item and any needed follow-up. Continue
independent M6 work per the PM's autonomous instruction.

## PM decision, 2026-10-24

Keep open, S2. Add automatic passive recurrence capture of the producing module
and native call context, with no user data and no exception suppression. A
synthetic capture test proves the observer, never the actual diagnostic cause.
Include its startup, storage and privacy boundaries in AUDIT-PACKET.md.
