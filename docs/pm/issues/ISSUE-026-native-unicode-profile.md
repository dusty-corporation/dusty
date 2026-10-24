# ISSUE-026 - Engine command-line code page breaks Unicode profiles

- Severity: S1
- Milestone: M6
- Status: Candidate repair; activation needs PM/Owner
- Environment: Windows desktop, engine-v2 v1.9.5, Tiny CPU, synthetic profile

## Root cause

The pinned CLI uses main(char **argv). Its console output is UTF-8, but its
embedded manifest does not opt the process into a UTF-8 active code page.
Windows converts non-ASCII arguments through the legacy process code page
before whisper.cpp receives them. Model and decoded-audio paths can both break.
Existing M5 path tests covered Python writes and cleanup, not native inference
from a non-ASCII profile. M5 branch and drafts are frozen and unchanged.

## Evidence

An isolated real GUI regression fails ENGINE_ERROR after decoding. Direct
same-binary comparisons: ASCII model/audio exit 0 with expected speech;
Unicode model exit 3; Unicode audio exit 2. Raw stderr stayed in memory.
A repo-local copy with only activeCodePage=UTF-8 added succeeds with both paths,
exit 0 and expected speech. The pinned original stayed byte-identical.
Original CPU CLI SHA-256:
8f41b59afd7fda8d62b70806b6d848260195a6ec90c7f9b991f47fc8cd37461b.
Probe copy SHA-256:
b99455571d87a9822fdd6fe6d9cf5a39323911fb656ff58c117022a2dd0da166.

## Candidate and decision

M6 native build embeds the UTF-8/long-path manifest in both existing engine
builds. No new component or dependency. Native CI includes the Unicode-profile
regression. Activation requires verified new artifact hashes and an Owner-published
engine release; never modify engine-v2 or frozen M5 drafts. Recommend approving
that new engine build after CPU/Vulkan, VAD, PE and offline checks.
The required regression remains enabled and fails against the current public
engine-v2. No skip, xfail, test weakening or ASCII-path workaround.

## Regression

test_unicode_profile_models_and_synced_documents_output in
tests/integration/test_m6_hardening.py. Real GUI, Unicode profile/model/audio,
sync warning, TXT/DOCX, original recording unchanged and work cleanup.

## Full candidate validation

Native run 40110881732 produced both exact packages pinned in
native/m6-engine-candidate.json. Candidate app CI 40125892713 at fc2c6e5 passed
all jobs: 392 source tests, strict coverage, packaged/installed canary and WFP,
PE and license gates, protected destinations and complete uninstall lifecycle.
This does not activate engine-v2 replacements. Ordinary production-pin CI
40124502543 still fails the enabled Unicode case. ADR 0024 approval, reviewed
new engine release preparation/publication and production-pin rerun remain.

## PM decision, 2026-10-24

ADR 0024 is approved. Prepare an exact engine-v3 draft and separate production
pin branch m6-engine-v3-pins. Owner publication and PM confirmation are required
before integrating those pins. No engine-v2 mutation and no premature closure.
