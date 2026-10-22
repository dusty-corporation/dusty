# ISSUE-006 - Runtime network guard conflicts with static import rule

- Severity: S1
- Milestone: M2
- Status: Open
- Environment: `src/dusty/privacy/` design, SPEC 9.2, `tools/check_no_network.py`

## Steps to reproduce

Implement the runtime guard exactly as SPEC 9.2.3 states by importing
Python's `socket` module in `src/dusty/privacy/network_guard.py` and
replacing `socket.socket`, `socket.create_connection`, and
`socket.getaddrinfo`. Run `uv run python tools/check_no_network.py`.

## Expected

The main app installs the specified runtime guard at startup and the
required static network isolation check passes without exceptions that
conceal networking code.

## Actual

SPEC 9.2.1 requires the AST check to fail any `socket` import in any
`src/dusty/**` module. The existing checker implements that rule.
SPEC 9.2.3 simultaneously requires a module in the main app to replace
three functions on `socket`. A direct import is rejected. Indirectly
loading `socket` to bypass the checker would undermine the static rule.

## Evidence

`tools/check_no_network.py` includes `socket` in `FORBIDDEN` and scans
every Python file under `src/dusty`. Its M0 negative tests require
forbidden imports to fail. Both conflicting requirements are in SPEC 9.2.
No networking import has been added to the main app.

## Root cause

The static rule was written without an explicit exception for the
runtime guard that the same section requires. M0 tests correctly tested
the static ban, while the runtime guard was scheduled for M2, so the
contradiction was not exercised earlier.

## Fix / proposed fix

PM approval is needed for one design:

1. Recommended: allow `import socket` in exactly one audited guard module,
   while the static checker still rejects it everywhere else. Require a
   negative test proving all other main-app modules are blocked, tests of
   the guard's three replacements, and the M2 WFP runtime audit.
2. Alternative: replace the specified monkeypatch with a Python audit
   hook that blocks socket operations without importing `socket`. This
   changes the literal guard design in SPEC 9.2.3 and needs PM approval.

Do not use an unscanned helper module or an import alias as a workaround.

## Regression test added

Pending PM design decision. Existing static negative tests remain enabled.
