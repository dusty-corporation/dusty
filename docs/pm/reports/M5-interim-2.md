# M5 Interim 2 - Required-platform PE import stop

## 1. Summary

The PM's explicit stop condition is met: the pinned **python312.dll and
Qt6Core.dll both import WS2_32.dll**. Removing lxml and splitting the folders
cannot remove imports inside these required binaries. I stopped after the
read-only preflight and recorded the approved decisions as ADRs 0019/0020.
No allowlist, source code, dependencies, layout or binaries were changed.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Identify required-platform import conflicts before rebuilding | met | 114 candidate PEs checked; five matches, original installed hashes identical. |
| List every checked PE | met | docs/dev/packaging-pe-preflight.md includes all 114 names and five exact import tables/hashes. |
| Standard-library DOCX, test-only python-docx | approved, pending | ADR 0019; no implementation before the explicit stop is resolved. |
| Separate onedir folders and strict offline-folder CI gate | blocked | ISSUE-015: Python and QtCore themselves violate the requested import rule. |
| Narrow Visual C++ exception, no UCRT, complete notices | approved, pending | ADR 0020; no license-checker changes or new clearance claim. |
| Remove Mesa/unused plugins, include libffi MIT notice | pending | No rebuild after the stop finding. |
| Rerun WFP/license gate and close S0 after fix | not met | ISSUE-014 remains open; no fix or new test results are claimed. |

## 3. Evidence

Normal and delayed imports were checked case-insensitively against
ws2_32.dll, wsock32.dll, wininet.dll, winhttp.dll and dnsapi.dll.
All matches below are to **WS2_32.dll**:

| PE | Imported functions |
|---|---|
| python312.dll | getsockopt, send, WSAGetLastError |
| PySide6/Qt6Core.dll | WSACleanup, WSAStartup, WSAAsyncSelect |
| _multiprocessing.pyd | recv, send, closesocket, WSAGetLastError |
| _overlapped.pyd | closesocket, WSASend, ntohl, WSAIoctl, WSASendTo, WSAConnect, socket, ntohs, WSAStringToAddressW, WSARecv, WSARecvFrom, inet_ntop, htons, bind, WSAGetLastError |
| select.pyd | select, __WSAFDIsSet, WSAGetLastError |

This was a preflight of the existing local experimental bundle, Python 3.12.11
and Qt 6.9.2, at code 04e9b5a. lxml, dusty-fetch.exe, _socket/_ssl, OpenSSL and
software OpenGL were excluded from this candidate scan. The complete checked
list also records existing Windows runtime/helper files that the approved new
layout would exclude; this is not evidence of a newly built compliant folder.
All five matching PEs are byte-identical to their original installed sources.
No runtime network event or disclosure was observed.

## 4. Test results

No builds, test suites or WFP runs were launched for the new decisions. The only
new execution was the read-only PE preflight and documentation generation.
Historical test, size and WFP evidence remains in M5-interim-1.md and does not
establish compliance with the PM's new offline-folder import rule.

## 5. Deviations

Implementation paused before the approved DOCX/layout changes because the PM
explicitly said to stop on a legitimate platform binary with a prohibited import.
No exception or upstream binary substitution was made.

## 6. Issues

| Issue | Severity | Status |
|---|---|---|
| ISSUE-014, lxml native networking | S0 | Open; removal approved, not yet implemented. |
| ISSUE-015, Python/QtCore native imports | S1 | Blocked on the explicit required-platform decision. |
| ISSUE-013, native license clearance | S1 | Narrow Visual C++ exception approved; remaining changes pending. |

## 7. Decision needed

Please specify the policy for these required-platform imports. As requested,
I have not treated them as an exception or assumed they are harmless IPC.
A rebuild/substitution or a narrowly justified policy requires PM approval.

## 8. Actions needed from the Owner

Relay the required-platform decision. No new runtime test is requested.
The existing eight-check M3 re-test is the active Owner walkthrough; the old
20-step desktop request is stale and is not being repeated. The ThinkPad's
18 passes/two failures and the implemented fixes remain the recorded history.

## 9. Risks

The requested import-free offline folder cannot currently pass with these
unchanged required platform DLLs. ISSUE-014 cannot honestly be closed until its
approved fix and the revised packaging checks have passed.

## 10. Effort notes

The initial dependency preflight found the blocker before implementation or
another bundle build. Only repository documentation was written.
