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


@pytest.fixture(scope="session")
def mac_gpu(tmp_path_factory) -> SimpleNamespace:
    """What Dusty's own GPU check finds on this Mac, run once with the staged engine.

    Inside a virtual Mac (GitHub's Mac runners) Dusty never starts the Metal
    engine and uses the CPU: ``backend`` is then "cpu" and ``reason`` says why
    tests of the Metal engine itself skip. Every other result expects Metal,
    including a failed check on a real Mac, so a broken Metal engine fails the
    tests instead.
    """
    from dusty.engine.backend import probe_gpu
    from dusty.models import ModelRegistry, load_manifest
    from dusty.queue.storage import load_settings
    from dusty.runtime_paths import RuntimePaths, resolve_paths

    dev = resolve_paths(repo_root=Path(__file__).resolve().parents[1], frozen=False)
    user = tmp_path_factory.mktemp("gpu-check") / "user"
    user.mkdir(mode=0o700)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, user)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    probe_gpu(paths, registry, refresh=True)
    probe = load_settings(user / "settings.json").get("backend_probe") or {}
    if probe.get("unsupported") is True and probe.get("virtual_mac") is True:
        reason = (
            "Dusty does not use the GPU inside a virtual Mac, such as GitHub's Mac runners, "
            "where the Metal engine stalls or reports missing features"
        )
        return SimpleNamespace(backend="cpu", reason=reason, probe=probe)
    return SimpleNamespace(backend="metal", reason=None, probe=probe)


@pytest.fixture
def metal_gpu(mac_gpu: SimpleNamespace) -> None:
    """Skip a test of the Metal engine itself inside a virtual Mac, where it never starts."""
    if mac_gpu.reason:
        pytest.skip(mac_gpu.reason)


@pytest.fixture(autouse=True)
def isolate_application_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Subprocesses inherit this too; tests must not write the maintainer's app data."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
