"""Empty-system-store TLS tests never connect beyond the local HTTPS fixture."""

import hashlib
import json
import ssl
from pathlib import Path
from urllib.error import URLError

import pytest
from test_downloader import tls as tls_fixture

from dusty_fetch.downloader import Downloader
from dusty_fetch.tls import ROOTS, bundled_pem, create_context, resource_dir

tls = tls_fixture


def local_bundle(tmp_path, tls_certificate):
    folder = tmp_path / "roots"
    folder.mkdir()
    data = tls_certificate.cert.read_bytes()
    (folder / "local.pem").write_bytes(data)
    pins = {
        "local.pem": (
            hashlib.sha256(data).hexdigest(),
            hashlib.sha256(ssl.PEM_cert_to_DER_cert(data.decode())).hexdigest(),
        )
    }
    return folder, pins


def test_empty_system_store_plus_bundled_root_downloads_and_verifies(
    tls, tmp_path, monkeypatch, tls_certificate
):
    monkeypatch.setattr(
        ssl, "create_default_context", lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    )
    folder, pins = local_bundle(tmp_path, tls_certificate)
    context = create_context(directory=folder, pins=pins)
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    client = Downloader(policy=tls.client.policy, context=context)
    client.download(tls.asset, tls.dest, lambda e: None)
    client.verify(tls.asset, tls.dest)


def test_root_neither_system_nor_bundle_is_rejected(tls):
    context = create_context(system=False)  # Production bundle excludes our private fixture CA.
    client = Downloader(policy=tls.client.policy, context=context)
    with pytest.raises(URLError) as failure:
        client.download(tls.asset, tls.dest, lambda e: None)
    assert isinstance(failure.value.reason, ssl.SSLCertVerificationError)
    assert not (tls.dest / tls.asset.file_name).exists()


@pytest.mark.parametrize("damage", ["bytes", "fingerprint", "multiple", "empty", "missing"])
def test_bundled_root_integrity_fails_closed(tmp_path, damage, tls_certificate):
    folder, pins = local_bundle(tmp_path, tls_certificate)
    if damage == "bytes":
        (folder / "local.pem").write_bytes(b"changed")
    elif damage == "fingerprint":
        pins["local.pem"] = (pins["local.pem"][0], "0" * 64)
    elif damage == "multiple":
        data = (folder / "local.pem").read_bytes() * 2
        (folder / "local.pem").write_bytes(data)
        pins["local.pem"] = (hashlib.sha256(data).hexdigest(), pins["local.pem"][1])
    elif damage == "empty":
        pins = {}
    else:
        (folder / "local.pem").unlink()
    with pytest.raises((ssl.SSLError, OSError)):
        create_context(system=False, directory=folder, pins=pins)


def test_production_root_provenance_and_fingerprints_are_exact():
    metadata = json.loads((resource_dir() / "sources.json").read_text(encoding="utf-8"))
    assert {v["file"] for v in metadata["roots"]} == set(ROOTS)
    assert ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).cert_store_stats()["x509_ca"] == 0
    for root in metadata["roots"]:
        assert ROOTS[root["file"]] == (root["pem_sha256"], root["der_sha256"])
        assert root["official_ca_download_url"].startswith(
            ("https://letsencrypt.org/", "http://crt.sectigo.com/")
        )
    assert len(create_context(system=False).get_ca_certs()) == 4
    assert bundled_pem()


def test_trust_data_attribution_cannot_cover_code_or_changed_roots(tmp_path):
    import shutil

    from tools.check_licenses import check_trust_data

    shutil.copytree(resource_dir(), tmp_path / "resources/tls")
    inventory = {
        "files": [
            {"path": "resources/tls/" + name, "components": ["public-ca-certificates"]}
            for name in ROOTS
        ]
    }
    assert check_trust_data(tmp_path, inventory)
    inventory["files"].append({"path": "evil.exe", "components": ["public-ca-certificates"]})
    assert not check_trust_data(tmp_path, inventory)
    inventory["files"].pop()
    (tmp_path / "resources/tls/usertrust-ecc.pem").write_bytes(b"changed")
    assert not check_trust_data(tmp_path, inventory)


def test_empty_system_store_still_holds_every_pinned_root(monkeypatch):
    """macOS OpenSSL may start with no roots; the pinned bundle alone remains."""
    monkeypatch.setattr(
        ssl, "create_default_context", lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    )
    context = create_context()
    assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    held = {hashlib.sha256(der).hexdigest() for der in context.get_ca_certs(binary_form=True)}
    assert held == {der for _, der in ROOTS.values()}


def test_frozen_root_folders_follow_each_platform_layout(tmp_path):
    bundle = tmp_path / "Apps/Dusty Copy.app"
    helper = bundle / "Contents/Helpers/dusty-fetch/dusty-fetch"
    assert resource_dir(frozen=True, executable=helper, platform="darwin") == (
        bundle / "Contents/Resources/tls"
    )
    windows = tmp_path / "install/dusty-fetch/dusty-fetch.exe"
    assert resource_dir(frozen=True, executable=windows, platform="win32") == (
        tmp_path / "install/resources/tls"
    )
    source = resource_dir(frozen=False)
    assert source == Path(__file__).resolve().parents[2] / "resources/tls"
    assert not bundle.exists()


@pytest.mark.parametrize(
    "helper",
    [
        "Dusty.app/Contents/MacOS/dusty-fetch",
        "Dusty.app/Contents/Helpers/other/dusty-fetch",
        "Dusty/Contents/Helpers/dusty-fetch/dusty-fetch",
        "Dusty.app/Wrong/Helpers/dusty-fetch/dusty-fetch",
    ],
)
def test_frozen_mac_root_folder_rejects_other_shapes(tmp_path, helper):
    with pytest.raises(ssl.SSLError):
        resource_dir(frozen=True, executable=tmp_path / helper, platform="darwin")
    with pytest.raises(ssl.SSLError):
        resource_dir(frozen=True, executable=Path(helper), platform="darwin")
