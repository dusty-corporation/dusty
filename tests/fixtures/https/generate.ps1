param([Parameter(Mandatory = $true)][string]$Destination)

# Throwaway loopback identity only. Never open a Windows certificate store.
$ErrorActionPreference = 'Stop'
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$certificate = $null
try {
    $request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
        'CN=localhost', $rsa,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
    $san.AddDnsName('localhost')
    $san.AddIpAddress([System.Net.IPAddress]::Loopback)
    $request.CertificateExtensions.Add($san.Build())
    $request.CertificateExtensions.Add(
        [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new(
            $true, $false, 0, $true))
    $now = [DateTimeOffset]::UtcNow
    $certificate = $request.CreateSelfSigned($now.AddMinutes(-5), $now.AddDays(1))
    [System.IO.File]::WriteAllText(
        (Join-Path $Destination 'localhost.pem'), $certificate.ExportCertificatePem())
    [System.IO.File]::WriteAllText(
        (Join-Path $Destination 'localhost-key.pem'), $rsa.ExportPkcs8PrivateKeyPem())
} finally {
    if ($null -ne $certificate) { $certificate.Dispose() }
    $rsa.Dispose()
}
