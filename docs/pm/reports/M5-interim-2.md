# M5 interim 2 - Native installer PM page round

## Owner actions for the morning

1. Review the new page bundle below. No new wording decision is currently needed.
2. Run M5-checklist.md using the repaired drafts named in the final M5 report.
   Genuine native 100%/150% scaling and actual button/X behavior remain VM checks.

## Summary and evidence

The PM page changes are implemented with shared messages and catalog sizes:
Next=Download, pre-start Back/model changes, persistent Downloading heading,
byte totals, processor retry, truthful singular/plural success and Finish without,
checked current-user Open Dusty now, checked desktop shortcut, compact uninstall
and the Voice detection sentence. No close-other-apps sentence remains.

Gated native review: 7b8d28b, CI 40065869279 all jobs green. Packaged/installed
PE/license/GUI/WFP, real-prefix normal cancel, retry and both uninstall variants
passed. Full download Setup/GUI/native 0, fetch allowed 4/blocked 0; cancel audit
0/0/0, fetch 2/0. ISSUE-020 preservation regressions remain enabled and green.
Owner ThinkPad model-free probe PASS, 2026-10-23: real_gpu_found=true,
model_file_opened=false. This is device initialization, not inference evidence.

[Draft m5-screenshots release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-a1e1f91641e95222b8da):
`m5-installer-pages-pm-round-7b8d28b-light.zip`, 7,725,089 bytes,
SHA-256 `27a3731c91478669cc5f13778b8ef432624c404cb2fb2adaf0fccb2905dbe1b0`.
Archive gate passed: 21 actual native-control PNGs plus README only.

Pages: Welcome, three license views, catalog, low-memory warning, folder,
shortcuts, ready, copying files, consent, downloading, model tests, download
failure, graphics failure, success, Finish without acknowledgment, both finish
pages, uninstall and the scrolled catalog. Review controls are disabled or safe
no-ops. Progress/failure/low-memory/model-size states are explicitly synthetic;
these images do not establish real failure-injection or VM acceptance.

Scale limitation: process-effective 96 DPI on the unchanged 175% host display;
Windows bitmap scaling remains visible. Captures were format-converted to PNG,
never resized or edited. No native 100%/150% monitor acceptance is claimed.
No Owner app profile or host settings were changed. Own preview process closed.

The separate `m5-main-output-row-a75f1cf-light-dark-100-150.zip` has 16 real Qt
client captures, both themes at device ratios 1/1.5, four destination states.
It includes only PNGs and README, with source/provenance and synthetic paths noted.

## Remaining evidence

M5's two-version draft run exposed obsolete versioned own-license copies
(ISSUE-022). The strict inventory gate blocked the .8 draft. A narrow guarded
pre-copy repair and preservation regressions are pushed; final tagged reruns
are in progress. See M5-report.md for final runs and safe VM builds.
The Owner still measures total first-page extraction time and native scaling;
probe driver deadlines alone do not establish extraction time.
