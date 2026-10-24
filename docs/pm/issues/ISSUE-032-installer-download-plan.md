# ISSUE-032 - Setup counts already installed models as downloads

- Severity: S2
- Milestone: M6
- Status: In progress
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
