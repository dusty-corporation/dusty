# 0028 - Private development and public release snapshots

- Status: Accepted by PM
- Date: 2026-10-25

## Decision

Development history remains in a private repository. A separate public repository
receives one clean, allowlisted source snapshot commit for each release. Public
CI builds the installer from public source and reruns the source, network,
licensing and installed acceptance gates. Public history never receives a
private development branch or merge. Snapshot author and committer use the
maintainer's GitHub noreply identity and a UTC timestamp.

The initial v1.0.0 gate requires fresh installation, same-version reinstall with
verified model reuse, both uninstall choices and calibrated zero-event WFP
receipts. Earlier distinct-version upgrade evidence remains in the private
archive. Starting with v1.0.1, true upgrade from the preceding public release is
mandatory. Pinned engine and model assets are copied byte-identically into draft
releases; only the maintainer publishes. Public releases use public CI, never a
private prebuilt installer substituted for public-source acceptance.

## Safety and privacy

The maintainer renames the development repository, makes it private, creates the
public repository and configures its protections. Tools verify repository
identity and visibility before upload or push. Export fails on unknown files,
linked paths, private references or personal identifiers. It only writes a new
empty tree. Public pushes use a separate clean clone with no development refs,
without force. Draft creation and publication are separate actions.

Public documentation uses broad descriptions of people and use cases. The
intentional Salam maman greeting stays by the maintainer's decision. Third-party license
and attribution texts remain intact. Hardware benchmarks, public audio sources
and documented test credentials retain their established scope.

## Consequences

The public tree is self-sufficient and tested after export. The private review
archive remains available to the maintainer and auditors. Clean public history
avoids exposing private planning records or old revisions. Changing current
files alone cannot remove personal information from existing Git history.


## PM asset-scope clarification

Copy only the five transcription models and Voice detection in the shipped
catalog, plus the unchanged pinned release manifest required by the build.
Transfer engine-v3 packages and their provenance, license and checksum evidence,
plus the exact pinned FFmpeg source archive and build script. Cut-model weights
and older engine releases remain private. Select assets by explicit names, not
by downloading whole private releases. SHA-256 and draft-only checks remain.


## PM private CI budget and local privacy gate

On GitHub Free, private development has 2000 included Actions minutes monthly
and 500 MB artifact storage. Windows costs more than Linux; quota exhaustion
blocks usage under the maintainer's no-overage budget. Automatic private push/PR
runs therefore execute only source lint, format, types, unit tests and policies,
without model/native downloads, integration/coverage tracing, artifacts or heavy
jobs. The unit suite requires Windows; one bounded Windows source job retains
that coverage. Full manual workflow_dispatch remains available as an explicit
budget choice. Public CI remains fully gated. Private release jobs never run,
even for tags. Guards use event repository visibility, never a repository name.

Private main protection/rulesets are not enforced on Free. The private engineering rules explicitly
forbid direct main pushes; maintainer review/merges remain the procedural control.
Supported heavy checks run locally; disposable-CI-only WFP/WER/installer checks
run in the public repository or an explicitly requested manual private run.

Before transition, a new local bare repository under build/ holds the exact
public snapshot with noreply author/committer and a UTC date. This dry run needs
no network or existing public repository. The maintainer runs the external privacy
audit against it after merging the preparation PR. A later export/push must
match the reviewed Git tree and receipt, including after a squash merge. A
changed tree requires a fresh dry run and privacy review before anything public.
