# ISSUE-016 - Official Microsoft runtime license download returns HTTP 403

- Severity: S1
- Milestone: M5 packaging spike
- Status: Open, awaiting Owner
- Environment: approved network escalation, Python 3.12.11 urllib HTTPS

## Steps to reproduce

Fetch the official document linked by Microsoft's runtime license page:

https://visualstudio.microsoft.com/wp-content/uploads/2021/09/Visual-C-Runtime-2015-2022-License-1.docx

The source link was verified through
https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/ .

## Expected

Obtain the full vendor license text for the approved ADR 0020 notice.

## Actual / exact error

```text
urllib.error.HTTPError: HTTP Error 403: Forbidden
```

The request ran with approved network escalation and still failed. No alternate
host, request-header change, browser download or other workaround was attempted.
Work stopped under the Owner's earlier permission/network-error instruction.

## Root cause

The vendor server rejected the document request. The exact server-side reason
is unknown; this is not attributed to the sandbox without evidence.

## Fix / proposed fix

The Owner can provide the official license document/text inside the repository
or specify an approved way to obtain it. No license text is fabricated, and
the narrow exception is not marked cleared until its required notice is present.

## Regression test added

None for an external vendor access failure. Existing license-gate work remains
pending; no test or allowlist was weakened to conceal the missing license.
