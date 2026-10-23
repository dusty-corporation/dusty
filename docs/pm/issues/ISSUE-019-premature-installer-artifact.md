# ISSUE-019 - Installer uploaded before complete license review

- Severity: S0 (NN-5)
- Milestone: M5 installer prework
- Status: Open, all implementation stopped
- Environment: public repository CI, Inno Setup 6.7.3, ac06dad

## Expected

The exact InnoSetup wrapper exception must not clear separately licensed static
components. No installer artifact is uploaded before the complete inventory gate.

## Actual

Commit ac06dad enabled the approved wrapper exception and was pushed before the
installer-wide inventory was added. The old workflow therefore passed its narrow
wrapper gate and uploaded an unsigned installer. Subsequent source review found
the unapproved static licenses listed in ISSUE-018. CI artifacts are distribution
for this policy; being unsigned or unpublished as a release does not clear them.

## Evidence

- Run: https://github.com/dusty-corporation/dusty/actions/runs/39922816919 .
- Artifact: m5-installer-draft-unsigned, ID 12488875272, compressed 34115983 bytes.
  https://github.com/dusty-corporation/dusty/actions/runs/39922816919/artifacts/12488875272
- Installer: 34591385 bytes, SHA-256
  f70f1ede9923d605f3ec1b3d072a1f4ed7c9e3d4da3c7fb2111fb05af64ec14d.
- Read-only API verified the artifact exists and is not expired. Only its audit
  metadata was downloaded for this incident, not the installer binary.
- Later run 39924971496 rejects the five static license records plus unresolved
  Delphi provenance and skips the installer upload. The earlier artifact remains.

## Root cause

The engineer sequenced the wrapper approval before completion of the installer
inventory and published that checkpoint to a workflow with automatic artifact
upload. The unit test covered exact license/context matching, but not the
requirement that the entire installer inventory precede any binary upload.
The approved wrapper license did not authorize its separately licensed units.

## Containment and Owner action

All implementation stopped when the existing upload was discovered. Requested
cancellation of active runs 39925428852 and 39925218957; 39924971496 had already
completed with only the intended license failure. Stopped the remaining local
coverage process tree. Endurance runs had already completed. No PR, merge,
release publication or repository-setting change occurred.

The Owner must remove only artifact 12488875272 from run 39922816919. Deletion
is explicitly Owner-only, so the engineer has not attempted it. Review ISSUE-018
before approving installer distribution, then authorize resumption. Later
workflows already require an installer-wide inventory and reject its unresolved
licenses; the app allowlist remains unchanged.

## Regression status

Current gate requires installer-wide inventory, checks exact static records and
notice hashes, binds the compiled image and app payload to their inventories,
and rejects unapproved identifiers. Negative inventory/notice tests pass.
A CI-ordering regression specifically preventing this sequencing error remains
to be added after PM authorizes work to resume. No S0 resolution is claimed.
