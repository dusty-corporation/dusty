# 0019 - Standard-library DOCX writer

- Status: Accepted by PM
- Date: 2026-10-22

## Context

The runtime python-docx dependency brings lxml's native XML libraries into the
processing app. The packaging spike found native Winsock imports and unresolved
transitive license notices (ISSUE-014 and ISSUE-013).

## Decision

Replace the runtime DOCX exporter with a standard-library writer using zipfile
and escaped XML templates. Preserve the title, subtitle line, grouped paragraphs,
optional [HH:MM:SS] prefixes, Calibri 11 body font and empty core properties.
Keep python-docx in test dependencies only, to open generated documents and
verify existing semantic goldens. Neither python-docx nor lxml may be bundled.

## Consequences

No new runtime dependency is introduced. Escaping and Unicode content require
regression coverage; existing DOCX goldens must remain unchanged. Implementation
is pending the separate required-platform PE import decision in ISSUE-015.
This ADR records approval, not completion.

## Alternatives considered

Retain or rebuild lxml for the runtime exporter; the PM selected removal instead.
