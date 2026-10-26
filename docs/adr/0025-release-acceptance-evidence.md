# 0025 - Release acceptance evidence

- Status: Accepted by Owner and PM
- Date: 2026-10-24

## Decision

For v1.0.0, waive SPEC M7's supervised primary-user trial. Acceptance uses the
M5 and M6 VM, ThinkPad and CI evidence plus an Owner smoke test of the exact
v1.0.0 draft installer. A separate independent audit follows M7 Phase A.
The intended audience is a non-technical adult who records lectures and
conversations, sometimes in languages other than English, on a typical Windows
laptop.

## Residual risk

The real Surface has not been tested. The ThinkPad uses the same Intel GPU
family; its evidence, the installer self-test and CPU fallback reduce that risk
but do not establish a Surface pass. The Owner accepts this release risk.
No public release is authorized by this ADR. Only the Owner may publish.
