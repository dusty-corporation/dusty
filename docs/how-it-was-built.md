# How Dusty was built

Dusty was built with AI-assisted engineering and human review. Work proceeded
through milestone gates: native engine measurements, an offline processing
pipeline, GUI testing, a separate downloader, packaging, installation, hardening
and release review. A passing build alone was never the acceptance criterion.

Independent reviews examined security, privacy and licensing. Findings led to
changes in file cleanup boundaries, process isolation, state persistence,
crash-report exclusions, release evidence, RTL document generation and bundled
license notices. A privacy review led to separate private development history
and clean public release snapshots. These reviews reduce risk; they do not prove
that the software is free of defects or suitable for every confidential workflow.

The intended audience is a non-technical adult who records lectures and
conversations, sometimes in languages other than English, on a typical Windows
laptop. Public-domain fixtures cover decoding, timestamps and translation.
Windows VM and laptop checks complement CI. Untested hardware remains a risk;
Setup tests the selected model and CPU fallback, and failures are shown plainly.

CI evidence includes unit and real-pipeline tests, strict coverage, Qt GUI
checks, static network guards, executable import inventories, exact hash pins,
bundled license gates, calibrated Windows Filtering Platform observations,
real-store crash observations on disposable runners, installer lifecycle checks
and checksum manifests. See [build instructions](dev/build-from-source.md),
[release gates](dev/release-process.md) and [process boundaries](dev/process-hardening.md).

The public repository contains one reviewed snapshot commit per release. Its
own CI rebuilds and gates each release. Model and engine inputs retain their
original hashes and provenance. The maintainer alone publishes releases after
reviewing the exact draft installer. No automatic update check is performed.
