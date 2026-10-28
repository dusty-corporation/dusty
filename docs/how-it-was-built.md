# How Dusty was built

Dusty was designed and built by its maintainer with the help of AI coding tools.

The maintainer set the requirements and made the architecture decisions: local
transcription, a separate model downloader, bounded native processes and a
Windows installer. Work moved through measured milestones for the engine,
processing pipeline, interface, packaging and release. A passing build alone
was never enough to accept a milestone.

Privacy and security shaped the design. Recordings and transcripts stay on the
computer. The app's processing code has no network path, while the downloader
uses restricted hosts and verifies each model's hash. Cleanup checks ownership
and protected folders before removing temporary files.

Independent security, privacy and licensing reviews found issues that were
fixed or recorded as release risks. The fixes included safer file cleanup,
process isolation, state persistence, crash-report controls, release evidence,
document formatting and bundled license notices. The public repository is a
reviewed source snapshot without private development history.

CI checks source tests, strict coverage, interface behavior, network isolation,
binary imports, licenses, installer behavior and release checksums. Windows VM
and laptop tests add real installation and transcription evidence. Hardware
that was not tested remains a risk, so Setup tests the chosen model and a CPU
fallback. See the [build instructions](dev/build-from-source.md) and
[release gates](dev/release-process.md) for reproducible steps.

The public repository receives one reviewed source snapshot per release. Its
own CI builds the draft installer. The maintainer reviews that exact build and
publishes it after the release checks pass.
