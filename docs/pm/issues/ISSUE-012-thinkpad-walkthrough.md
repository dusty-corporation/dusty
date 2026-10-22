# ISSUE-012 - ThinkPad M3 walkthrough corrections

- Severity: S2
- Milestone: M3
- Status: Resolved
- Environment: Owner ThinkPad i7-1365U, Iris Xe, Tiny, Vulkan, 150% scaling

## Findings and cause

PM correction: Owner passed 18 original checks, including 6 and 17, and
failed Welcome/output recovery and the English-only task display. Move/Remove
and close/save/resume passed; Tab and the extra Start were separate findings. Modal options
hid the main slow warning, the forced language was not restored, collision
state could retain a previous row, and resumed rows needed another Start.
The initial pipeline collision decision treated outputs made earlier in the
same run like pre-existing transcripts. Native-only M1 coverage missed the
AMR preflight assumption, tracked separately in ISSUE-011.

## Fix and regression

Always-visible output destination with no default; purpose-first model labels
and conservative M1 estimates; explicit unavailable Translate and local slow
warning; prior language restored; same-run outputs numbered even when the
first file kept both against an older transcript; named collision and waiting
state; immediate resume with cleared unfinished elapsed; finished-list hint
and Clear finished; zero-success summary; plural/duplicate highlighting; plain
corrupt-file advice; one folder title; Tab exits list; optional recommended
model fetch. GUI, native pipeline and fetch regressions cover these changes.
Final local suite: 106 passed. PR 39854200159 and push 39854194307 passed
(105 tests, one unavailable-Vulkan skip); WFP GUI/headless processing recorded
zero connections. 136 screenshots uploaded as a new draft asset with verified
digest. The code correction is resolved; human re-test remains M3-retest.md.
