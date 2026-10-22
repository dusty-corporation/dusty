# ISSUE-006 - Runtime network guard conflicts with static import rule

- Severity: S1
- Milestone: M2
- Status: Resolved 2026-10-22
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

## Resolution

The PM accepted Option 2: use `sys.addaudithook` to block Python socket
operations without importing `socket` inside `src/dusty`. ADR 0017
supersedes the monkeypatch design in SPEC 9.2.3. The static check keeps
zero exceptions. The hook is installed before other Dusty entry-point
imports, including the `--self-test` path. `dusty_fetch` remains a
separate process without the hook.

## Regression test added

Subprocess tests cover every required audit event, real Dusty entry-point
startup, and independent `dusty_fetch` process startup. Static negative
tests remain enabled, and `check_no_network.py` remains unchanged.
