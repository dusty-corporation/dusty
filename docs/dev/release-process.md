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

When an earlier successful tagged run exists, acceptance obtains its gated
installer artifact using the read-only runner token, requires a strictly
increasing numeric version, installs the old
build, then upgrades with the new build. The downloader is blocked during upgrade;
verified model hashes and write times must remain unchanged. This exercises two
builds, rather than installing one executable twice. Tags N >= 3 require that
prior successful input. The Owner never needs to publish a test build.

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
or false receipts prevent draft creation. A normal-cancel receipt must also pass:
the real downloader writes a partial, the shared Cancel/X routine stops it,
the active partial is removed, retry succeeds and the output sentinel survives.
The final M5 staging gate also requires both legacy app-data destination and
protected registered-installation receipts. A native uninstaller must stop
before deleting any protected installed payload or its protection metadata.
The first successful build can have no
prior upgrade input. Intermediate experiments are not two-version evidence.

Each calibrated WFP phase uses a unique repository-local audit-policy CSV and
restores its own snapshot. Reusing a file fails auditpol with 0x00000050; the
expanded two-audit lifecycle is the regression for this correction.

## M6 work and frozen M5 artifacts

M5 .13/.14 remain frozen pending Owner VM results. M6 work happens on
m6-hardening and is not permission to push a new test tag or publish a release.
Branch CI can produce gated unsigned review artifacts without a release.
ISSUE-026 / proposed ADR 0024 needs a newly verified UTF-8 native build and
Owner activation; until then public engine-v2 fails its enabled Unicode-profile
regression. Do not call a native-only candidate an app release or green full CI.

## SmartScreen test downloads and internet zone

GitHub CLI downloads and read-only VirtualBox shares may not preserve Mark of
the Web. The Owner's ThinkPad .14 test on 2026-10-24 therefore did not exercise
SmartScreen, although installation/transcription/uninstall and 150% layout passed.
After copying the exact installer into the guest's local NTFS Downloads folder,
verify its SHA-256 and add the internet zone before starting it:

```powershell
Set-Content -LiteralPath <installer> -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"
```

Replace <installer> with the quoted exact local path (or a PowerShell variable
holding it). Verify with Get-Content -LiteralPath <installer> -Stream
Zone.Identifier, and recheck the unchanged installer SHA-256. The alternate
stream does not change the executable bytes. ZoneId=3 makes it eligible for
internet-download checks; policy and reputation still affect the actual prompt.
Record what happens instead of claiming that absence of a warning is a pass.

## M6 registered uninstall entry

Pinned Inno 6.7.3 Setup.Uninstall.pas:696 checks its native Silent/VerySilent
flags before the unconditional generic confirmation, after InitializeUninstall.
There is no script setting to suppress only that question. The public Windows
Apps uninstall registration therefore uses /SILENT /DUSTYCONFIRM=yes. The explicit
Dusty flag still opens our own confirmation; /SILENT suppresses Inno's second
question. Unattended /REMOVEMODELS=yes|no remains an explicit separate route.
The protected-installation preflight runs before both. Registration is written
at ssDone and validated by CI; failure is reported rather than ignored.

Directly running Inno's internal unins*.exe without the registered arguments can
still show its generic question. The supported user route is Windows Settings >
Apps. No runtime binary patch or compiler change is used. CI drives the registered
entry, changes its actual checkbox, confirms once and rejects any generic dialog.
