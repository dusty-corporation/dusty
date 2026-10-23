# M5 draft release pipeline

`release.yml` handles tag pushes through the same reusable `ci.yml` as branch
checks. Only PM-authorized `v0.5.0-m5.N` test tags currently pass validation.
Python metadata becomes `0.5.0.devN`, the displayed version `0.5.0-m5.N`, and
Inno's four-part version `0.5.0.N`. The disposable checkout alone is stamped;
source history is not rewritten. Native inputs stay pinned by SHA-256 in
native/versions.toml. No portable release bundle is produced.

The complete source, offline, negative-upload, split-layout PE/license, GUI,
packaged WFP and installed lifecycle gates must succeed before the unsigned
installer artifact becomes available. The release job depends on that complete
reusable workflow. It stages exactly four payload assets plus SHA256SUMS:

- Dusty-0.5.0-m5.N-draft-unsigned.exe
- THIRD_PARTY_NOTICES.md (app and installer components)
- dusty-0.5.0-m5.N-sbom.json (CycloneDX)
- installer-jedi-source.zip (retained reviewed MPL source and notices)
- SHA256SUMS.txt (SHA-256 of the four assets above)

`gh release create --verify-tag --draft --prerelease` creates a draft only.
There is no publishing, merging, tag replacement or deletion step. The upload
failure regression from ISSUE-019 remains in the reusable workflow. Release
staging rejects unexpected/duplicate inputs and cannot reuse an existing staging
directory. The negative checks include missing assets and unapproved tags.

Starting with N=2, acceptance obtains the preceding draft's installer using the
runner token, requires a strictly increasing numeric version, installs the old
build, then upgrades with the new build. The downloader is blocked during upgrade;
verified model hashes and write times must remain unchanged. This exercises two
builds, rather than installing one executable twice. A failed/missing preceding
draft prevents the new release. The Owner never needs to publish a test build.

The installer download WFP audit calibrates with a deliberately blocked control,
then observes Setup's original EXE and extracted runtime, Dusty/probe and native
processes, and separately counts dusty-fetch allowed/blocked events. Any
processing/Setup event fails; at least one allowed fetch event and zero blocked
fetch events are required. Summaries contain counts, not connection addresses.
The installed-app processing-only audit also blocks processing executables.

Clean Windows 11 standard-user testing and SmartScreen remain Owner actions in
[the checklist](../pm/M5-checklist.md). Native page-review screenshots are layout
evidence with synthetic progress/errors, not a substitute for lifecycle tests.
