# 0025 - Release acceptance evidence

- Status: Accepted by the maintainer and PM
- Date: 2026-10-24

## Decision

For v1.0.0, waive SPEC M7's supervised user trial. Acceptance uses the
M5 and M6 VM, ThinkPad and CI evidence plus a maintainer smoke test of the exact
v1.0.0 draft installer. A separate independent audit follows M7 Phase A.
Dusty is for anyone who records lectures or conversations, including in
languages other than English, on a supported Windows computer.

## Surface hardware follow-up

At the v1.0.0 gate, the real Surface had not been tested. The ThinkPad used
the same Intel GPU family; its evidence, the installer self-test and CPU
fallback reduced the risk without establishing a Surface pass. That specific
untested-hardware risk is now closed: a Surface Laptop 5 with Iris Xe ran
public v1.0.0 Setup with Large v3 Turbo on Vulkan and transcribed a 1 h 45 min
recording in about 40 minutes. This is one hardware result, not a general
speed guarantee. No public release is authorized by this ADR. Only the
maintainer may publish.
