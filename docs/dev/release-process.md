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

## Draft upgrade inputs and release receipts (final M5)

Earlier experiments showed that a read-only repository token does not see draft
release listings. GitHub documents that distinction in its
[release API](https://docs.github.com/en/rest/releases/releases#list-releases).
The final implementation does not broaden validation/build jobs to write access:
it selects an earlier successful tagged release workflow, reads that workflow's
already-gated installer artifact with actions:read, and checks its companion
SHA256SUMS before execution. Checkout credentials are not persisted and GH_TOKEN
is removed before app/test children run. Only the existing draft-creation job
needs contents:write. No repository settings are changed.

For test tags N >= 3, release staging independently requires receipts proving an
increasing-version upgrade, model hash/write-time preservation, current installed
payload/PE/WFP gates, both uninstall choices, unchanged user outputs and a fresh
CURRENT-installer download/probe audit with zero Setup/GUI/native events. Missing
or false receipts prevent draft creation. The first successful build can have no
prior upgrade input. Intermediate experiments are not two-version evidence.

Each calibrated WFP phase uses a unique repository-local audit-policy CSV and
restores its own snapshot. Reusing a file fails auditpol with 0x00000050; the
expanded two-audit lifecycle is the regression for this correction.
