# Changelog

All notable changes to Dusty will be documented here. This project follows Keep a Changelog.

## [1.0.1] - 2026-10-28

### Fixed

- Model downloads recover automatically from brief connection drops and from
  antivirus software briefly locking a newly downloaded file. If a download
  still fails, Dusty records a privacy-safe reason in its local log.
- Improved cleanup of Dusty's temporary work files after a crash or power loss,
  including files left by Dusty 1.0.0.
- If uninstall keeps app data because it cannot safely remove it, the message
  tells you where to find it.

### Changed

- Updated documentation wording and the description of how Dusty was built.

## [1.0.0]

### Added

- Pinned public TLS roots for fresh Windows downloads, with integrity checks and
  a CI canary for both approved hosts; no automatic root retrieval.
- Bounded passive native-diagnostic capture with redacted module/context data.

- M6 user/privacy/developer guides, documentation consistency gate, manual
  offline checklist and independent-audit packet with explicit evidence gaps.
- Forced-GUI-death recovery, Unicode and long-path processing, disk-exhaustion
  and packaged sensitive-log canary regressions.

- Packaging spike with separate offline GUI and TLS downloader folders, actual
  file inventory, CycloneDX SBOM, runtime notices and calibrated packaged WFP CI.

- M0 project foundation and minimal application window.
- M1 pinned CPU and Vulkan engine builds, minimal FFmpeg, reproducible model
  draft release, and offline benchmark kits.
- Public benchmark WER scoring over Gutenberg-only spans and a focused
  CPU/Vulkan thread sweep.
- M2 offline headless pipeline, five export formats, verified model catalog,
  persistent batch recovery, collision policies, cancellation and progress.
- Runtime audit-hook network guard, redacted logs, Windows firewall/WFP CI
  acceptance, public Persian translation fixture and strict package coverage.
- Repository-local test app data and a PM backlog for deferred work.
- M3 desktop queue with collapsed options, background processing, progress,
  cancellation, safe collision handling, resume, themes and privacy warnings.
- M4 Model Manager with isolated verified downloads, local integrity checks,
  disk-space display and source/packaged network-isolation acceptance.
- Centralized interface copy, real Qt batch acceptance tests and a draft
  screenshot matrix covering light/dark appearance at two display scales.

### Changed

- Voice detection defaults off for new settings. Skip long silences warns that
  quiet or distant speech may be missed; explicit saved choices stay unchanged.
- Installer model cards have separate borders, a checking line above the list,
  and Skip for now for installation without downloading or claiming a passed test.
- Prepare 1.0.0 metadata and real Windows app/installer version resources, untagged.

### Fixed

- Re-adding a Done recording resets only that recording to Waiting with current
  settings; existing transcript files remain subject to the collision choice.
- Per-recording elapsed time excludes time waiting for an existing-transcript choice.

- Activated published engine-v3 with UTF-8/long-path native manifests for
  non-ASCII Windows profile, model and audio paths, without system-locale changes.

- Explicit output-folder choices survive model events, crash recovery and Setup.
- Setup names/counts only needed downloads, supports Check and test for installed
  selections, and shows the full model list before the bounded graphics check.

- Windows namespace aliases now share managed-folder protection comparisons;
  active work leases prevent another instance's startup cleanup removing it.
- Successful Setup preserves a valid model choice or selects its tested default;
  About opens local notices, and the registered uninstall route confirms once.
- Decoder disk-full classification and partial-removal failure reporting avoid
  misleading damaged-recording or successful-cleanup messages.
- Graphics-test failure progress reflects the completed download amount.

- Standard-library DOCX export removes runtime lxml; exact platform PE pins,
  maintainer-sourced Visual C++ runtime copies and license evidence gate the bundle.

- Portable CPU backend dispatch after the CI-native instruction failure.
- Distinct public and private benchmark summary names with overwrite checks.
- Segment and word timestamps across VAD-removed silence, using the approved
  minimal native patch in the published engine-v2 prerelease.
- Explicit replacement choice when a resumed batch model is unavailable;
  Google Drive streaming mount detection for sync-folder warnings.
- PM-reviewed modal options, simpler recording actions and formats, phase labels,
  named collision/error/summary dialogs, and measured light/dark control contrast.
- Valid AMR with missing probe duration now transcribes; same-run names number
  safely, output selection is always visible, model choices explain their
  purpose, and resume starts unfinished recordings directly.
- ThinkPad-reviewed list, duplicate, summary, error and keyboard improvements;
  explicit development fetch option for the recommended Small and Turbo models.
- M4 downloader-only prework: isolated standard-library HTTPS download/verify CLI,
  strict redirect hosts, verified resumable parts, space/cancellation safety and
  local TLS plus explicit CI-only public model integration tests.
- Maintainer-reviewed model deletion and empty selection, fresh downloads after cancel,
  name-first model labels, clearer consent and main prompts, and disabled/selected
  control contrast in both themes.
- Final Model Manager wording, MB/GB sizing, progress labels and explicit
  verification feedback.

### Changed

- Dusty code uses Apache-2.0 with an explicit patent grant (maintainer decision).
