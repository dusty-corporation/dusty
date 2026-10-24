# ISSUE-029 - Fresh Windows missing public TLS roots

- Severity: S1
- Milestone: M6
- Status: In progress, PM-approved bundled-root repair
- Environment: Owner fresh Windows 11 Home VM, M5 Setup; Model Manager shares downloader

## Owner evidence, 2026-10-24

Setup failed immediately at 0.0 MB with The download or file check did not finish.
Fresh LocalMachine\Root contained 23 roots and no USERTrust/Sectigo root.
The observed github.com chain ended at USERTrust ECC. Visiting github.com in
Edge did not populate the Windows store. Invoke-WebRequest triggered Windows
automatic root retrieval: 24 roots including USERTrust ECC, then Retry succeeded.
No claim that this was a model SHA-256 failure or an application connection.

## Root cause and test gap

Python's OpenSSL verifier used only roots already present in the Windows store.
A fresh image may not yet contain a required public CA root. Existing local TLS
fixtures explicitly supplied their test root; hosted CI already had public roots.
Neither represented this fresh-store condition. Setup and Model Manager both
use dusty-fetch, so both are exposed. M5 remains frozen and not for distribution.

## PM decision

Use the Windows system store plus a small bundled root set for actual current
chains of github.com and release-assets.githubusercontent.com, including ECC
and RSA variants. Pin certificate SHA-256/fingerprints and official CA provenance.
No new dependency, certifi/truststore or automatic Windows root retrieval.
Keep hostname verification, minimum TLS, exact two-host/redirect policy and model
hash checks unchanged. Add isolated TLS positive/negative/integrity cases and a
CI-only live bundled-root canary. Also show the complete model list immediately
while the existing bounded hardware check runs; Checking this computer... and
Next disabled until completion, then apply the recommendation.

## Repair checkpoint

6346a49 adds the pinned four-root system-plus-bundle context used by the same
Setup/Model Manager fetch executable. USERTrust ECC/RSA and ISRG X1/X2 cover
observed default/ECC/RSA chains. Provenance includes exact acquisition: existing
trusted Windows USERTrust DER copies, official CA reference URLs, and ISRG HTTPS
downloads. Rejected HTTP/crt.sh retrievals did not run; no unverified TLS used.
No Microsoft retrieval, changed host policy, dependency or model-hash bypass.

Local absent-root success, untrusted-root rejection, tampered/missing bundle and
exact data-attribution tests pass; combined original downloader/new TLS tests
31 pass, 36.94 s after fixture registration correction b47e351. Installer page
fully initializes catalog before deferred probe extraction, displays Checking
this computer..., blocks Next until bounded completion/fallback, then selects
recommended/default Small. Full candidate 40130798813 and fresh-VM recheck pending.
