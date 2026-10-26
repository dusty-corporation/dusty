# Local HTTPS test identity

No test key or certificate is committed. The session-scoped tls_certificate
fixture in tests/conftest.py runs generate.ps1 with the existing PowerShell 7
and .NET runtime to create a fresh RSA-2048 key and self-signed SHA-256
certificate in pytest temporary space. Validity is one day, with a five-minute
clock allowance; the SAN covers localhost and 127.0.0.1. The identity is
throwaway, different on every test invocation, and must never be reused.

Tests inject this certificate into their own SSLContext and pass its temporary
path to child processes. No Windows certificate/key store is opened or changed;
the production CLI has no trust/host override and rejects this certificate.
The original trust, hostname, redirect, hash and cancellation assertions remain.
No added dependency, network service or native component is needed.

The generator uses Microsoft's documented
[CertificateRequest.CreateSelfSigned](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.x509certificates.certificaterequest.createselfsigned)
and in-memory PEM exports. Tests exercise the generated pair with real TLS.
