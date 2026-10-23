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
CI 40036996425 compiled the font/layout repair; final result and screenshot
asset are being collected in the continuing overnight session.

## Pages requested for review

Welcome; combined license agreement; separate third-party and Microsoft views;
Choose model; low-RAM warning; install folder; shortcuts; ready; file installation;
inline consent; download; per-model test progress; download failure; graphics-test
failure with CPU retry; successful checks; Finish without acknowledgment;
normal finish; finish after failed model setup; uninstall model-size checkbox.

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
