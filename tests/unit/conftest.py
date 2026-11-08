"""Defaults for the unit tests in this folder."""

import pytest


@pytest.fixture(autouse=True)
def real_mac_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake engines here stand for a real Mac's GPU, even when this host is a virtual Mac.

    GitHub's Mac runners are virtual Macs, where Dusty never starts the Metal
    engine. Tests of that path set it explicitly.
    """
    monkeypatch.setattr("dusty.platform.virtual_mac.is_virtual_mac", lambda: False)
