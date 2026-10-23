# ISSUE-014 - Collected lxml extension imports native network operations

- Severity: S0
- Milestone: M5 packaging spike
- Status: Open
- Environment: Windows x64, lxml 6.1.3 wheel, libxml2 2.11.9,
  Python 3.12.11, PyInstaller 6.16.0

## Steps to reproduce

Inspect the PE import table of the collected
`_internal/lxml/etree.cp312-win_amd64.pyd`, using the already installed pefile
development dependency:

```powershell
@'
import pefile
with pefile.PE('dist/Dusty/_internal/lxml/etree.cp312-win_amd64.pyd') as pe:
    for library in pe.DIRECTORY_ENTRY_IMPORT:
        if library.dll.lower() == b'ws2_32.dll':
            print(','.join(entry.name.decode('ascii') if entry.name else
                           str(entry.ordinal) for entry in library.imports))
'@ | uv run python -
```

## Expected

NN-2: processing components contain no network calls. The Python socket audit
hook cannot intercept arbitrary native Winsock calls in an extension.

## Actual

The collected exporter dependency imports `socket`, `connect`, `send`, `recv`,
`bind`, `listen`, `gethostbyname`, `gethostbyaddr`, `WSAStartup` and other Winsock
operations. This is native network capability outside dusty_fetch, requiring the
NN-2 stop. No connection attempt or data disclosure was observed. The earlier
packaged WFP self-test passed with zero events; that does not prove absence of
native networking code or cover every exporter path.

## Evidence

The exact WS2_32 import names returned were:

```text
getsockname,bind,WSAGetLastError,WSASetLastError,listen,inet_ntop,WSAStartup,
getservbyname,getservbyport,gethostbyname,gethostbyaddr,socket,send,select,recv,
ntohs,inet_ntoa,inet_addr,htons,htonl,getsockopt,ioctlsocket,connect,closesocket,
__WSAFDIsSet
```

The main application loads lxml through its existing python-docx exporter
dependency. No bundle binaries were uploaded or released. Work stopped upon
confirming these imports; only issue/report documentation and its push follow.

## Root cause

The prebuilt lxml wheel contains native XML libraries with Winsock dependencies.
PyInstaller carries the extension into the bundle. The exact native call graph
and build flags have not been investigated after the S0 finding. Earlier static
checks inspect Python imports and named Qt DLLs, while WFP observes calls made
by exercised paths. Neither establishes that lxml's native networking code is
absent. The approved Python audit guard does not interpose on these native APIs.

## Fix / proposed fix

PM decision, 2026-10-22: remove lxml from the shipped app by replacing runtime
python-docx with a standard-library DOCX writer; python-docx stays test-only.
Recorded as ADR 0019. Implementation has not started because the PM's separate
required-platform PE-import stop condition was hit in ISSUE-015. This issue
remains open until the actual fix and its regression checks pass.

The initial proposal to investigate a network-disabled XML dependency is
superseded by the PM's removal decision above. No rebuild, dependency change
or workaround was attempted before that decision.

## Regression test added

None yet: the S0 rule requires stopping implementation. A proposed regression
must check the processing extension's native networking configuration/imports
and exercise packaged Word export under the calibrated WFP audit. Scope it to
processing extensions; the separate downloader legitimately uses TLS/socket code.
