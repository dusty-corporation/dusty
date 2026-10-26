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
During initial acquisition, automatic approval review rejected HTTP retrieval
and a crt.sh retrieval; those requests did not run. Authenticated support.sectigo.com attachments were inspected, including a
USERTrust RSA root matching the selected fingerprint. The bundled USERTrust roots
were instead copied exactly from pre-existing trusted Windows ROOT entries,
with their official CA reference URLs recorded, without altering that store.
ISRG roots were downloaded from its official HTTPS URLs with certificate checks.
No claim is made that USERTrust bytes were downloaded from the reference URL.
Automatic approval review accepted this safer local-store/HTTPS acquisition. No rejected acquisition transport was worked around.

## Runtime and canary

The downloader creates its normal Windows/OpenSSL default context, adds the
hash/fingerprint-checked bundled PEMs and retains CERT_REQUIRED, hostname checks
and minimum TLS 1.2. Proxy behavior, exact two-host allowlist, redirect validation,
model size/SHA-256 checks, cancellation and resume are unchanged. Setup and Model
Manager both launch this same dusty-fetch executable. The offline app imports
neither the downloader nor TLS modules.

Local TLS tests remove all system roots: a fresh temporary local test root permits
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


## Official fingerprint comparison, 2026-10-24

All four bundled **certificate DER SHA-256 fingerprints** were recomputed and
compared with fingerprint fields published by the CAs, over verified HTTPS.
These are certificate fingerprints, not hashes of PEM text, public keys or
cross-signed versions. Every comparison is equal; bundled files/pins unchanged.

| Root | Bundled DER and CA-published SHA-256 (identical) | Official source |
|---|---|---|
| USERTrust ECC | `4ff460d54b9c86dabfbcfc5712e0400d2bed3fbc4d4fbdaa86e06adcd2a9ad7a` | [CA fingerprint record](https://crt.sh/?id=2841410) |
| USERTrust RSA | `e793c9b02fd8aa13e21c31228accb08119643b749c898964b1746d46c3d4cbd2` | [CA fingerprint record](https://crt.sh/?id=1199354) |
| ISRG Root X1 | `96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6` | [CA fingerprint record](https://letsencrypt.org/documents/isrg-cp-cps-v6.2/) |
| ISRG Root X2 | `69729b8e15a86efc177a57afb7171dfc64add28c2fca8cf1507e34453ccb1470` | [CA fingerprint record](https://letsencrypt.org/documents/isrg-cp-cps-v6.2/) |

ISRG CP/CPS v6.2 section 1.1 explicitly lists both self-signed root fingerprints.
For USERTrust, Sectigo's canonical records 2841410 and 1199354 explicitly show
Certificate Fingerprints / SHA-256, independently of a hash-search query.
[Sectigo's official terms](https://www.sectigo.com/terms-of-use) identify crt.sh
as a website it operates. The Owner's later explicit official-CA cross-check
request and that ownership evidence supported this read-only HTTPS verification;
it is separate from the initially rejected acquisition requests above.
No certificate was replaced or installed into Windows, no insecure transport
was used, and crt.sh is NOT added to the app/downloader host allowlist.
Raw public pages/comparison stay ignored under build/m6-official-root-comparison;
only this compact result and primary-source links are committed.
