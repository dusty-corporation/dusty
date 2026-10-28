# 0012 - License
- Status: Accepted; amended by the maintainer on 2026-10-22
- Date: 2026-10-21
## Context
Dusty must be free and open source.
## Decision
Originally MIT. On 2026-10-22 the maintainer, the sole contributor, authorized
relicensing Dusty's own code under Apache-2.0, providing an explicit patent
grant for future contributors. LICENSE contains the full Apache-2.0 text and
NOTICE records Copyright 2026 Dusty contributors. Project metadata uses the
Apache-2.0 identifier, which is already on the license-checker allowlist.

This maintainer decision supersedes the own-code MIT statements in the unchanged
SPEC. Third-party licenses and the narrow runtime exceptions are unaffected.
## Consequences
Third-party components need separate license checks and notices.
## Alternatives considered
Copyleft for Dusty's own code; not required by the project goals.
