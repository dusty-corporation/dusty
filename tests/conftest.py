"""Keep test application state inside pytest's repository-local workspace."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.test_appdata_guard import install_guard

# On macOS, synthetic Qt key events abort the process when no interactive
# desktop is available (for example a closed lid or an unattended run). Use
# the offscreen platform unless the developer asks for another one. Real Cocoa
# behavior is covered by the manual and packaged-app smoke checks.
if sys.platform == "darwin":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Capture before the autouse fixture redirects LOCALAPPDATA for app isolation.
_REAL_WER_ROOTS = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    / "Microsoft/Windows/WER",
    Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft/Windows/WER",
)


@pytest.fixture
def real_wer_roots() -> tuple[Path, ...]:
    return _REAL_WER_ROOTS


install_guard(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "Dusty")


# The same throwaway identity generate.ps1 makes on Windows: RSA-2048, SHA-256,
# CN=localhost, SAN DNS localhost and IP 127.0.0.1, critical CA basic
# constraints without a path length, valid for one day. Nothing reads the
# system OpenSSL configuration.
_OPENSSL_CONFIG = """[req]
prompt = no
distinguished_name = subject
x509_extensions = identity

[subject]
CN = localhost

[identity]
subjectAltName = DNS:localhost,IP:127.0.0.1
basicConstraints = critical,CA:TRUE
"""


def generate_tls_identity(folder: Path) -> SimpleNamespace:
    """Write localhost.pem and localhost-key.pem; output is captured, never shown."""
    if sys.platform == "win32":
        subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(Path(__file__).parent / "fixtures/https/generate.ps1"),
                "-Destination",
                str(folder),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
    else:
        config = folder / "localhost-openssl.cnf"
        config.write_text(_OPENSSL_CONFIG, encoding="ascii")
        subprocess.run(
            [
                "/usr/bin/openssl",
                "req",
                "-x509",
                "-config",
                str(config),
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-sha256",
                "-days",
                "1",
                "-keyout",
                str(folder / "localhost-key.pem"),
                "-out",
                str(folder / "localhost.pem"),
            ],
            check=True,
            capture_output=True,
            timeout=30,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        config.unlink()
    return SimpleNamespace(cert=folder / "localhost.pem", key=folder / "localhost-key.pem")


@pytest.fixture(scope="session")
def tls_identity_generator():
    return generate_tls_identity


@pytest.fixture(scope="session")
def tls_certificate(tmp_path_factory):
    """Generate a fresh identity in pytest temp space, never in committed fixtures."""
    return generate_tls_identity(tmp_path_factory.mktemp("localhost-tls"))


@pytest.fixture(autouse=True)
def isolate_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses inherit this too; tests must not write the maintainer's app data."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
