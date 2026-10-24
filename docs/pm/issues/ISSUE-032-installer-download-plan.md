# ISSUE-032 - Setup counts already installed models as downloads

- Severity: S2
- Milestone: M6
- Status: Resolved on m6-hardening; Owner clean-snapshot recheck pending
- Environment: Owner .13/.14 VM, 2026-10-24

Setup described selected Small/Small English/Tiny/Voice detection as a 1.1 GB
download although only Small English was missing. Progress stopped at 487.6 MB
of the inflated total. Upgrade said Downloading Tiny and Voice detection while
only checking. Selection and required-download sets were conflated in generated
consent strings and TotalModelBytes. Model verification itself remained enforced.

PM decision: name/count only required downloads; use A, B and C for three or
more names. If none are missing, explain that selected files are already
downloaded and will be checked/tested; label the button Check and test. Keep
all selected-model/CPU fallback/VAD tests, integrity checks and explicit consent.

## Final regression evidence

CI 40134555055 at 932949e passes all source, packaged, installed WFP, PE, license
and uninstall gates. 423 tests pass, 2 expected skips; no weakened regression.
Source/packaged GUI connection events 0, fetch 4 allowed/0 blocked; installed
processing 0. Final M6-report identifies the gated candidate hash and remaining
clean-snapshot Owner checks. Frozen M5 code/assets unchanged; no distribution.

Generated consent tests cover all 63 needed-file subsets and correct grammar;
VAD installed/missing/same-size hash corruption is verified. Existing-file hash
checks never count as newly transferred bytes. Native all-installed reinstall
passes with fetch blocked and unchanged model hashes/mtimes; every selected
model and VAD still verifies/tests. Recheck mixed-state visible names/amounts on
the clean VM; generator/native evidence is not a fabricated screenshot review.
