# 0024 - Windows native Unicode paths

- Status: Accepted by PM; production activation waits for publication confirmation
- Date: 2026-10-24

## Context

ISSUE-026 demonstrates the pinned CLI receives lossy narrow command-line
arguments on a legacy-code-page Windows installation. This affects ordinary
non-ASCII Windows profile names, model folders and temporary audio paths.

## Decision

Embed activeCodePage=UTF-8 and longPathAware in the existing whisper.cpp EXEs
at link time. Keep all CPU dispatch, no-network and VAD patch settings. Verify
both rebuilt packages and publish a new engine release only through the Owner;
do not alter engine-v2 or frozen M5 .13/.14. No new native component is introduced.

Microsoft's [manifest reference](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests)
documents process UTF-8 from Windows 10 1903, within Dusty's supported Windows
10 22H2/11 baseline. The pinned CLI source at examples/cli/cli.cpp:974 uses
main(char **argv); changing console output encoding alone does not fix argv.
Retrieved 2026-10-24. A copied-EXE manifest-only experiment passes both Unicode
model/audio paths; the original remains unchanged. Native CI is the build proof.

## Consequences and alternatives

New artifact and installed inventory hashes are required. Do not change Windows
system locale, rely on optional 8.3 aliases, relocate private work outside app
data, or modify an executable at runtime. The proposed manifest is build input,
not an application-time workaround. Keep the failing integration test enabled
until the candidate has been activated and the full app gates pass.

## PM approval, 2026-10-24

Prepare engine-v3 as a draft from exact native run 40110881732 at
d0abc304942255a1d30d741fff0ca98c2c1cdf45, already gated by app run 40125892713.
Keep engine-v2 unchanged. Owner publishes engine-v3 as a prerelease, not latest.
Prepare the pin switch only on m6-engine-v3-pins based on m6-hardening; do not
merge it before the PM confirms publication.

## Prepared draft and pin branch

Engine-v3 draft has 12 independently downloaded/checksummed assets, including
both exact gated packages, unchanged FFmpeg, licenses, patch, manifest, caches
and BUILD-PROVENANCE.json. Native source/run remains d0abc30 / 40110881732.
m6-engine-v3-pins 299fea3 changes only production engine pins; no merge before
PM confirms publication. Active m6-hardening pins remain engine-v2. The exact
Owner prerelease publication command is in docs/dev/engine-v3.md and M6-report.md.
