# 0017 - Runtime network guard via audit hook

- Status: Accepted by PM
- Date: 2026-10-22

## Context

SPEC 9.2.1 bans `socket` imports throughout the main `dusty` package,
while SPEC 9.2.3 called for that package to monkeypatch three functions
on the `socket` module. The original design conflict
records this conflict. The static ban protects the offline boundary and
must remain unchanged.

## Decision

Install a Python audit hook with `sys.addaudithook` at the first
executable step of the Dusty entry point, including `--self-test`.
It raises `NetworkBlockedError` for socket creation, connection,
binding, send, and name-resolution audit events. It logs only the event
name, never event arguments, addresses, or hostnames. The guard remains
inside `src/dusty/privacy/` without importing any networking module.

This supersedes the socket-function monkeypatch design in SPEC 9.2.3.
The static `check_no_network.py` rule keeps zero exceptions.
`dusty_fetch` is a separate process and does not install the hook.

## Consequences

Python audit hooks cannot be removed. Guard tests must run in child
Python processes and cover every required event, actual startup through
the Dusty entry point, and independent startup of `dusty_fetch`.
The separate Windows WFP audit remains necessary to check native child
processes and network behavior outside Python's audit events.

## Alternatives considered

An exception in the static checker for one monkeypatch module was
rejected by the PM. Import aliases and unscanned helpers would conceal
the import from the policy checker and were not used.


## M7 re-review clarification, 2026-10-25

The audit hook, literal static check, executable restrictions, PE gate and WFP
acceptance are defense in depth, not a sandbox against arbitrary hostile Python
or native code. No product path uses the identified native escapes. os.spawn,
os.exec, os.posix_spawn, os.fork and os.forkpty are blocked. Static checks include
LoadLibraryW/ExW and GetModuleHandleW, plus ANSI equivalents, for literal network
DLL names including mswsock and iphlpapi. Dynamic DLL-name construction and direct
native calls are not comprehensively intercepted by Python audit hooks. The
source rule retains zero networking exceptions; static checks do not prove the
absence of obfuscation or arbitrary native behavior.
