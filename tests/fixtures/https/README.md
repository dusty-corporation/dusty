# Local HTTPS test certificate

localhost.pem and localhost-key.pem are public, test-only fixtures. They are
not production credentials and must never be trusted or used outside tests.
The certificate covers localhost and 127.0.0.1, valid 2020-2040. Tests load it
only into an explicitly injected SSLContext; nothing enters a Windows store.
The production CLI has no trust/host override and rejects this certificate.

Generated once in memory with PowerShell/.NET CertificateRequest, RSA 2048,
SHA256/PKCS1, a SubjectAlternativeNameBuilder and a self-signed CA constraint.
CreateSelfSigned was used directly; no certificate/key store was opened.
ExportCertificatePem and RSA.ExportPkcs8PrivateKeyPem wrote only these files.
No extra executable, Python dependency, internet service or native component
is required to run the TLS tests.
