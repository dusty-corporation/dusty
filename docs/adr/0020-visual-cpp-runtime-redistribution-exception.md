# 0020 - Visual C++ runtime redistribution exception

- Status: Accepted by PM
- Date: 2026-10-22

## Context

CPython's Windows distribution needs Microsoft Visual C++ runtime DLLs, whose
vendor redistribution terms are outside the general SPEC 10.2 license allowlist.
The packaging spike identified this as part of ISSUE-013.

## Decision

The PM approves a narrow redistributable exception for required
`vcruntime140*.dll` and `msvcp140*.dll` runtime files. Include the applicable
Microsoft license text in the notices. This is not a general Microsoft binary
or EULA exception. Do not bundle `api-ms-win-crt*` or UCRT DLLs, which are part
of Windows 10 and later.

## Consequences

The bundle inventory and license checker must identify required matching DLLs
explicitly and retain the vendor terms before claiming clearance. No broader
exception is authorized. Implementation and license-text collection remain
pending the required-platform PE import decision in ISSUE-015.

Vendor redistribution reference:
https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files .

## Alternatives considered

Treat every Microsoft runtime as forbidden; the PM instead approved this narrow
exception. Bundling Windows UCRT/API-set runtime files was rejected.
