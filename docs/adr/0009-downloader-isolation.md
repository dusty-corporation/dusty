# 0009 - Downloader isolation
- Status: Accepted
- Date: 2026-10-21
## Context
Processing components must have no network code.
## Decision
Put all network operations in `dusty-fetch`, a separate package and executable. The main app must not import it.
## Consequences
Static and dynamic isolation checks are required.
## Alternatives considered
An in-process download library; weakens the isolation boundary.
