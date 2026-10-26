"""Windows system trust plus exact bundled public CA roots, never online repair."""

import hashlib
import ssl
import sys
from pathlib import Path

ROOTS = {
    "usertrust-ecc.pem": (
        "08fb40ba4144166f6ae80c7ab60be23e97e5083836d45fa85a33a5d0bfec10f8",
        "4ff460d54b9c86dabfbcfc5712e0400d2bed3fbc4d4fbdaa86e06adcd2a9ad7a",
    ),
    "usertrust-rsa.pem": (
        "8a3dbcb92ab1c6277647fe2ab8536b5c982abbfdb1f1df5728e01b906aba953a",
        "e793c9b02fd8aa13e21c31228accb08119643b749c898964b1746d46c3d4cbd2",
    ),
    "isrg-x1.pem": (
        "22b557a27055b33606b6559f37703928d3e4ad79f110b407d04986e1843543d1",
        "96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6",
    ),
    "isrg-x2.pem": (
        "a13d881e11fe6df181b53841f9fa738a2d7ca9ae7be3d53c866f722b4242b013",
        "69729b8e15a86efc177a57afb7171dfc64add28c2fca8cf1507e34453ccb1470",
    ),
}


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.parent / "resources/tls"
    return Path(__file__).resolve().parents[2] / "resources/tls"


def bundled_pem(directory: Path | None = None, *, pins=ROOTS) -> str:
    """Injection is library-test only; the CLI offers no trust/host override."""
    folder = directory if directory is not None else resource_dir()
    parts = []
    for name, (pem_hash, der_hash) in pins.items():
        data = (folder / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != pem_hash:
            raise ssl.SSLError("Bundled certificate integrity check failed")
        text = data.decode("ascii")
        if text.count("-----BEGIN CERTIFICATE-----") != 1:
            raise ssl.SSLError("Invalid bundled certificate count")
        der = ssl.PEM_cert_to_DER_cert(text)
        if hashlib.sha256(der).hexdigest() != der_hash:
            raise ssl.SSLError("Bundled certificate fingerprint mismatch")
        parts.append(text)
    if not parts:
        raise ssl.SSLError("Bundled certificates missing")
    return "\n".join(parts)


def create_context(
    *, system: bool = True, directory: Path | None = None, pins=ROOTS
) -> ssl.SSLContext:
    # CPython/OpenSSL enumerates present Windows roots. No Crypt32 chain builder,
    # AIA/OCSP/CRL download, or Windows automatic root update is invoked.
    context = ssl.create_default_context() if system else ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_verify_locations(cadata=bundled_pem(directory, pins=pins))
    return context
