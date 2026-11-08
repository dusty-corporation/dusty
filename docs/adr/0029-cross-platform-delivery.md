# 0029 - Shared source and separate Windows/macOS delivery

- Status: Accepted by PM for source/delivery boundaries; technical Mac runner,
  sandbox, signing and minimum OS decisions remain pending feasibility evidence.
- Date: 2026-10-30
- Authority: Owner requested full Mac parity and clean Windows/Mac coexistence in
  private development and later public publication, with the Easter egg excluded.

## Context

Current main is a Windows product. Its process APIs, native pins, packaging,
PE/WFP checks, release tag grammar and public export manifest assume Windows.
The public repository is dusty-corporation/dusty, specified by export.py;
repository.json pins the separate development identity. Historical SPEC and
accepted Windows evidence remain preserved. MAC-AI establishes PM-led teamwork.

## Decision

One application and shared source tree. No permanent Mac fork, duplicated
business logic or platform-specific main branches. Short-lived feature branches
are reviewed into private development main. Public snapshots contain the shared
source and every file needed to build each declared supported platform, while
excluding private PM records and history through the existing reviewed allowlist.

Keep domain types, exporters, model trust and queue behavior shared. Isolate OS
APIs behind explicit platform interfaces. Windows keeps Vulkan/CPU; Mac targets
Metal/CPU with real backend reporting. Existing five models and VAD remain the
initial shared catalog; format compatibility must be demonstrated before reuse.
Do not expand model downloads or change trust hashes without evidence.

Use separate platform build/package recipes and evidence. Add Mac-specific paths
alongside stable Windows entry points; no cosmetic mass move of existing scripts.
When an existing path must change, update all callers, tests, license source
references and the export manifest in a separately reviewed change. Separate
output/cache directories by OS, architecture, backend, pins and build variant.

The release target identity is explicit: windows-x86_64 and macos-arm64 initially
as development targets. These labels are not support claims. Owner selected Apple Silicon first and Intel later. No Intel/universal2 package
is in first-release scope; minimum OS still needs dependency/hardware proof. No new source/runtime
package dependency or shipped helper is approved by this boundary ADR alone.

Use one application version and reviewed source snapshot for a combined release,
with independently built Windows and Mac deliverables. Keep existing published
Windows names and upgrade URLs compatible. Mac assets use an explicit suffix,
e.g. Dusty-<version>-macos-arm64.dmg. Platform-specific SBOM, notices, provenance,
receipts and test results cannot overwrite each other. The final checksum index
covers the exact signed/packaged bytes; a release assembler validates the complete
expected artifact set before creating a draft.

Before Mac shipping, retain Windows-only servicing. Adding an unfinished Mac job
must not break existing Windows patch releases or declare Mac supported. A future
release-target contract will explicitly select targets and required gates; unknown
or missing targets fail closed. For a declared combined release, a failed required
platform gate blocks the combined draft. Do not silently publish a partial set.

## Safety and verification

Windows source/GUI/native/PE/WFP/installed/upgrade gates remain Windows checks;
Mac gets separate source/Mach-O/privacy/bundle/signing/lifecycle checks. A shared
matrix is appropriate for truly portable tests, not a forced uniform packaging
command. A Linux source check cannot stand in for either platform's acceptance.
Runner OS/architecture, cache and artifact identities must be explicit and pinned
where practical. Keep the existing private CI no-overage budget and no private
release behavior. Heavy runner/signing jobs need a deliberate budget decision.

Public publication continues through the approved exporter and a separate clean
clone, with reviewed normalized tree receipts, repository identity/visibility
checks and Owner authorization. Never push private development branches/history,
AGENTS or PM records to the public repository. Unknown source files fail export;
new Mac production files must be explicitly added and tested in a self-sufficient
export before release. Planning docs in docs/dev can contain private references
and are not automatically public-safe merely because of their directory name.

No existing release/tag/asset is mutated to make room for Mac. No remote action,
signing account purchase, secret, workflow dispatch or public push is performed
by this ADR. Owner retains merge and publication authority.

## Consequences and open decisions

Separate platform packages share one behavior contract and version, reducing
fork drift while preserving OS-specific auditing and distribution requirements.
Native process supervision, network isolation observation, App Sandbox, minimum
macOS, signing identity and performance recommendations need MAC-0 evidence or
later ADRs. Mac's first version number is not selected here. Historical v1.0.x
release scripts remain unchanged until a tested migration is approved.

## Alternatives considered

- Independent Mac repository/long-lived branch: rejected for duplicated fixes,
  mismatched models and divergent product behavior.
- Duplicate application code per OS: rejected; adapt only actual platform APIs.
- Rename every Windows script now: rejected; unnecessary compatibility and
  publication-source risk without functional benefit.
- Enable Mac release jobs before acceptance: rejected; risks Windows servicing
  and misleading platform support claims.

## References

- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations
- https://github.com/actions/upload-artifact/blob/main/README.md
- https://pyinstaller.org/en/v6.16.0/feature-notes.html
- ADR 0028 and the existing private/public export policy.
