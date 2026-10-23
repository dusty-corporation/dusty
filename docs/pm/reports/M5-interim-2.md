# M5 interim 2 - Native installer page review

## Owner actions for the morning

1. PM: review the native light/100% page bundle linked below. Wording and layout
   are frozen after this delivery pending your response, except correctness fixes.
2. Owner: run docs/pm/M5-checklist.md on the fresh standard-user Windows 11 VM.
   No installer has been run against the Owner's real app profile.

## Summary and evidence

Step B implements the shared catalog/consent, three reachable license views,
physical model-free GPU/RAM pre-selection, Auto testing of every selected model,
one extra smallest-model CPU check, Retry/CPU retry/Finish without, and an
uninstall checkbox with the real installed-model size. Owner ThinkPad Iris Xe
probe PASS on 2026-10-23: `{"real_gpu_found":true,"model_file_opened":false}`.

Local full source: 257 passed/1 expected skip, 94.6% measured core-package
coverage (193.37 s). Ruff/format, mypy and all three policy checks pass.
CI 40036996425, 40039096810 and 40040642247 are green for the native review
builds. [Draft screenshot release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-a1e1f91641e95222b8da):
`m5-installer-pages-step-b-895e199-light-review.zip`, 7,861,054 bytes,
SHA-256 `d09b2e4695fca10c5c0409dcee5cac70121bec5da1e8555b34c68aa57ca0578e`.
The archive gate passes: 21 native PNGs plus README only. Provenance per image
is in README; no source/metadata profiles are in the ZIP.

Scale limitation: host display is 175% and was not changed. A process-only
DPI-unaware compatibility launch reports 96 effective DPI (100%), but Windows
bitmap-scales its captured windows. Images were not resized. This is not native
100%/150% display acceptance; the Owner's VM checklist must supply those checks.
The bundle is ready for wording/layout review, with that explicit remaining gap.

## Pages requested for review

Welcome; combined license agreement; separate third-party and Microsoft views;
Choose model; low-RAM warning; install folder; shortcuts; ready; file installation;
inline consent; download; per-model test progress; download failure; graphics-test
failure with CPU retry; successful checks; Finish without acknowledgment;
normal finish; finish after failed model setup; uninstall model-size checkbox.
An extra scrolled model-list capture shows Tiny's complete note.

The review executable uses real Inno controls with installation disabled.
Progress/error/low-memory and uninstall-size examples are synthetic review states,
not evidence of a real download failure or clean-machine acceptance. The archive
must contain only PNGs and README; profile/metadata files stay outside it.

## Questions for the PM

- Please approve or annotate the page wording/layout. No further cosmetic changes
  will be made before that reply. The larger native model list uses explicit
  wrapped shared descriptions rather than Inno's single-line secondary column.
- Fresh VM testing must measure full model-page entry time, including temporary
  payload extraction. Driver calls themselves have a five-second child deadline
  and seven-second Setup deadline; the standalone probe does not measure disk
  extraction. No unmeasured total-time claim is made.

The old packaging-spike interim 2 is retained as
M5-packaging-spike-interim-2.md. This report is the current M5 page review.
