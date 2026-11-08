"""Recognizing a virtual Mac from two sysctls, without starting a process."""

import subprocess
import sys

import pytest

from dusty.platform import cpu_topology, gpu_signature

# The real check. tests/unit/conftest.py replaces the module attribute for other
# unit tests, so it is taken before that happens.
from dusty.platform.virtual_mac import is_virtual_mac as detect


def _sysctls(monkeypatch, hypervisor: int, brand: str, read: list[bytes]) -> None:
    def count(name: bytes) -> int:
        read.append(name)
        return hypervisor if name == b"kern.hv_vmm_present" else 0

    def text(name: bytes) -> str:
        read.append(name)
        return brand if name == b"machdep.cpu.brand_string" else ""

    monkeypatch.setattr(cpu_topology, "_darwin_sysctl_count", count)
    monkeypatch.setattr(gpu_signature, "_sysctl_string", text)


@pytest.mark.parametrize(
    ("hypervisor", "brand", "expected"),
    [
        (1, "Apple M2", True),
        (0, "Apple M1 (Virtual)", True),
        (0, "Apple M2 Pro (Virtual)", True),
        (0, "Apple M2", False),
        (0, "Apple M4 Max", False),
        (0, "", False),
    ],
)
def test_a_hypervisor_or_a_virtual_processor_name_means_a_virtual_mac(
    monkeypatch, hypervisor, brand, expected
):
    monkeypatch.setattr(sys, "platform", "darwin")
    _sysctls(monkeypatch, hypervisor, brand, [])
    assert detect() is expected


def test_other_systems_are_not_virtual_macs_and_read_nothing(monkeypatch):
    read: list[bytes] = []
    _sysctls(monkeypatch, 1, "Apple M1 (Virtual)", read)
    monkeypatch.setattr(sys, "platform", "win32")
    assert detect() is False
    assert read == []


def test_unreadable_sysctls_count_as_a_real_mac(monkeypatch):
    def unreadable(name: bytes) -> int:
        raise OSError("sysctl unavailable")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(cpu_topology, "_darwin_sysctl_count", unreadable)
    monkeypatch.setattr(gpu_signature, "_sysctl_string", unreadable)
    assert detect() is False


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only: reads this Mac's own sysctls")
def test_agrees_with_what_sysctl_reports_for_this_mac():
    def sysctl(name: str) -> str:
        run = subprocess.run(
            ["/usr/sbin/sysctl", "-n", name], capture_output=True, text=True, timeout=30
        )
        return run.stdout.strip() if run.returncode == 0 else ""

    expected = sysctl("kern.hv_vmm_present") == "1" or sysctl("machdep.cpu.brand_string").endswith(
        "(Virtual)"
    )
    assert detect() is expected
