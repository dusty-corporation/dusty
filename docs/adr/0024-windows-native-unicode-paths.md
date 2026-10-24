# 0024 - Windows native Unicode paths

- Status: Proposed; candidate build, activation pending PM/Owner
- Date: 2026-10-24

## Context

ISSUE-026 demonstrates the pinned CLI receives lossy narrow command-line
arguments on a legacy-code-page Windows installation. This affects ordinary
non-ASCII Windows profile names, model folders and temporary audio paths.

## Proposed decision

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
