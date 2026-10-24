# Downloader TLS roots (ISSUE-029)

PM approved a small bundled public-root set in addition to roots already present
in the Windows store. No new library, Windows trust installation, AIA/CRL/OCSP
fetch or automatic Microsoft root retrieval. The shared split-layout resources
contain four PEM files, SHA-256 PEM hashes, DER certificate fingerprints and
honest per-file provenance in resources/tls/sources.json. Runtime pins live in
src/dusty_fetch/tls.py, not in a remotely replaceable manifest.

Observed 2026-10-24 using verified TLS, SNI and real certificate chains:

| Host/profile | Chain to bundled root |
|---|---|
| github.com default/ECC | GitHub -> Sectigo DV E36 -> E46 cross-sign -> USERTrust ECC |
| github.com forced TLS 1.2 RSA | GitHub -> Sectigo DV R36 -> R46 cross-sign -> USERTrust RSA |
| release-assets.githubusercontent.com default/RSA | *.github.io -> Let's Encrypt YR1 -> Root YR cross-sign -> ISRG Root X1 |
| release-assets forced TLS 1.2 ECC | Not served: handshake rejected; no claim of an observed ECC leaf. ISRG Root X2 covers its published ECC chain family. |

The four roots are USERTrust ECC/RSA and ISRG X1/X2. No leaf or intermediate is
promoted to a trust anchor. Current cross-signs are supplied by the hosts.
The [Sectigo root reference](https://www.sectigo.com/knowledge-base/detail/Sectigo-Root-Certificates)
and [ISRG chain reference](https://letsencrypt.org/certificates/) describe these
families. Exact official CA download/reference URLs and fingerprints are in
sources.json. These are public certificate data, not Dusty-owned Apache code;
SBOM/notices identify them separately. The license/data gate accepts only the
four exact pinned PEM paths/bytes, never code under a broad data exception.

## Acquisition

Sectigo's published crt.sectigo.com HTTPS endpoint rejected its handshake.
Automatic approval review rejected HTTP retrieval and a crt.sh retrieval; neither
ran. Authenticated support.sectigo.com attachments were inspected, including a
USERTrust RSA root matching the selected fingerprint. The bundled USERTrust roots
were instead copied exactly from pre-existing trusted Windows ROOT entries,
with their official CA reference URLs recorded, without altering that store.
ISRG roots were downloaded from its official HTTPS URLs with certificate checks.
No claim is made that USERTrust bytes were downloaded from the reference URL.
This safer acquisition was approved. No rejected transport was worked around.

## Runtime and canary

The downloader creates its normal Windows/OpenSSL default context, adds the
hash/fingerprint-checked bundled PEMs and retains CERT_REQUIRED, hostname checks
and minimum TLS 1.2. Proxy behavior, exact two-host allowlist, redirect validation,
model size/SHA-256 checks, cancellation and resume are unchanged. Setup and Model
Manager both launch this same dusty-fetch executable. The offline app imports
neither the downloader nor TLS modules.

Local TLS tests remove all system roots: the pinned local fixture root permits
download and final hash verification; the production bundle rejects that root.
Changed/missing PEMs and DER fingerprints fail before a connection. No unit test
uses the public network or edits a Windows root store.

CI runs `python -m dusty_fetch.tls_canary` with DUSTY_CI_CA_CANARY=1. It uses only
the bundled roots, validates both live hostnames, records full verified-chain
fingerprints and fails clearly on a root/chain change. It additionally probes RSA
and ECC TLS 1.2 profiles; an unsupported optional algorithm is labelled not served,
never a certificate-validation bypass. Default chains must always pass. CPython
3.12.11's _sslobj.get_verified_chain/public_bytes API is verified and used only
for CI diagnosis, not the production download path. The captured 2026-10-24
local chain probe is separate from the CI receipt.
