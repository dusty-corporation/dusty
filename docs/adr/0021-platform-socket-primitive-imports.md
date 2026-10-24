# 0021 - Platform socket-primitive imports

- Status: Accepted by PM
- Date: 2026-10-22

## Context

ISSUE-015 found Winsock imports in required CPython and QtCore binaries. The PM
clarified NN-2: no code path Dusty invokes may open a network connection.
Required platform primitives alone do not establish an invoked network path.

## Decision

Only these exact platform binaries and exact WS2_32 function sets are permitted:

| Filename | SHA-256 | WS2_32 functions |
|---|---|---|
| python312.dll | e1643b99a6f7b69410bd941f2bcd03614baa8f4d3eaf6fbe9a29929f5a3bf79e | WSAGetLastError, getsockopt, send |
| Qt6Core.dll | 393833b9d4deef7abd8bf475d38c15126c2f016058b03dd5eb27fa18198cfa75 | WSAAsyncSelect, WSACleanup, WSAStartup |

The machine-readable pins are in packaging/platform-socket-imports.json.
Changed hashes, function sets or another PE importing ws2_32, wsock32, wininet,
winhttp or dnsapi fail CI and require PM review. No ordinal or wildcard exceptions.
Optional _overlapped, _multiprocessing and select extensions are excluded; if
the full suite or packaged self-test/GUI proves one necessary, stop and report
the exact code path rather than extending the allowlist.

## Defense layers and reachability

Separate onedir runtimes keep the downloader's socket/TLS support out of Dusty's
folder. Dusty excludes _socket/_ssl, OpenSSL, Qt Network/WebEngine, lxml and
optional async/process socket helpers. The source static rule keeps zero
exceptions, and the first user runtime hook installs the irreversible socket
audit guard before Qt imports. File logging uses a bounded local FileHandler
instead of importing logging.handlers' socket transports.

These layers remove the application socket/HTTP/DNS entry points that could
reach the platform primitives. Dusty invokes Qt raster widgets and Windows
process/file APIs, not socket objects. The exact PE pins prevent an unreviewed
platform upgrade from changing that assumption. The calibrated WFP test checks
the actual packaged self-test and its native children for zero connection events.
It is evidence for the exercised paths, not proof of every possible upstream
code path; full-suite and GUI smoke evidence are required before closing the issue.

## Consequences

CPython is the exact uv-managed Python 3.12.11 build 20250902 used for the
approved hash. CI must use that binary rather than silently accepting a different
setup-python build. Qt stays pinned at 6.9.2. The two-entry allowlist changes
only by PM review; other defenses remain enabled.

## Alternatives considered

Blanket Winsock allowance, exceptions for optional extensions, and accepting
different Python builds were rejected. Custom platform rebuilds are not required
by this approved decision.
