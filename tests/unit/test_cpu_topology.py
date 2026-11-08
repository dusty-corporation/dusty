"""Validate platform CPU queries and bounded thread defaults without shell probes."""

import ctypes
import sys
from types import SimpleNamespace

import pytest

from dusty.platform import cpu_topology as cpu


class Function:
    def __init__(self, call):
        self.call = call

    def __call__(self, *args):
        return self.call(*args)


def test_windows_query_counts_only_core_records_and_sets_signatures(monkeypatch):
    records = b"".join(kind.to_bytes(4, "little") + (8).to_bytes(4, "little") for kind in [0, 1, 0])

    def query(relationship, buffer, size):
        assert relationship == 0
        size._obj.value = len(records)
        if buffer is not None:
            ctypes.memmove(buffer, records, len(records))
            return 1
        return 0

    function = Function(query)
    monkeypatch.setattr(cpu.sys, "platform", "win32")
    monkeypatch.setattr(
        cpu.ctypes,
        "WinDLL",
        lambda *a, **k: SimpleNamespace(GetLogicalProcessorInformationEx=function),
        raising=False,
    )
    assert cpu.physical_core_count() == 2
    assert function.restype is ctypes.c_int32
    assert function.argtypes[-1] == ctypes.POINTER(ctypes.c_uint32)


@pytest.mark.parametrize(
    "records",
    [
        b"\0" * 7,
        b"\0" * 4 + (0).to_bytes(4, "little"),
        b"\0" * 4 + (16).to_bytes(4, "little"),
        b"\0" * 4 + (8).to_bytes(4, "little") + b"x",
    ],
)
def test_windows_rejects_truncated_or_invalid_records(monkeypatch, records):
    def query(relationship, buffer, size):
        size._obj.value = len(records)
        if buffer is not None:
            ctypes.memmove(buffer, records, len(records))
        return bool(buffer)

    monkeypatch.setattr(cpu.sys, "platform", "win32")
    monkeypatch.setattr(
        cpu.ctypes,
        "WinDLL",
        lambda *a, **k: SimpleNamespace(GetLogicalProcessorInformationEx=Function(query)),
        raising=False,
    )
    assert cpu.physical_core_count() == 0


@pytest.mark.parametrize(
    ("status", "value", "size", "expected"),
    [(0, 8, 4, 8), (-1, 8, 4, 0), (0, 8, 2, 0), (0, 0, 4, 0), (0, -1, 4, 0)],
)
def test_darwin_query_checks_status_size_and_value(monkeypatch, status, value, size, expected):
    def query(name, output, output_size, new, new_size):
        assert name == b"hw.physicalcpu"
        assert new is None and new_size == 0
        output._obj.value = value
        output_size._obj.value = size
        return status

    function = Function(query)
    monkeypatch.setattr(cpu.sys, "platform", "darwin")
    monkeypatch.setattr(cpu.ctypes, "CDLL", lambda *a, **k: SimpleNamespace(sysctlbyname=function))
    assert cpu.physical_core_count() == expected
    assert function.restype is ctypes.c_int
    assert function.argtypes[2] == ctypes.POINTER(ctypes.c_size_t)


def test_query_unavailable_does_not_prevent_thread_default(monkeypatch):
    monkeypatch.setattr(cpu.sys, "platform", "darwin")

    def unavailable(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(cpu.ctypes, "CDLL", unavailable)
    monkeypatch.setattr(cpu.os, "cpu_count", lambda: 6)
    assert cpu.physical_core_count() == 0
    assert cpu.default_threads() == 3


@pytest.mark.parametrize(
    ("physical", "logical", "expected"),
    [(12, 24, 8), (6, 8, 6), (0, 3, 2), (0, None, 2), (0, 1, 1), (0, 64, 8), (-1, 0, 2)],
)
def test_thread_defaults_remain_positive_bounded(monkeypatch, physical, logical, expected):
    monkeypatch.setattr(cpu, "performance_core_count", lambda: 0)
    monkeypatch.setattr(cpu, "physical_core_count", lambda: physical)
    monkeypatch.setattr(cpu.os, "cpu_count", lambda: logical)
    assert cpu.default_threads() == expected


def test_other_platform_has_safe_fallback(monkeypatch):
    monkeypatch.setattr(cpu.sys, "platform", "other")
    assert cpu.physical_core_count() == 0


@pytest.mark.skipif(sys.platform != "darwin", reason="real Darwin sysctl API")
def test_real_darwin_physical_cpu_query():
    assert 1 <= cpu.physical_core_count() <= (cpu.os.cpu_count() or 1024)


def test_windows_failed_second_query_returns_unknown(monkeypatch):
    def query(relationship, buffer, size):
        size._obj.value = 8
        return 0

    monkeypatch.setattr(cpu.sys, "platform", "win32")
    monkeypatch.setattr(
        cpu.ctypes,
        "WinDLL",
        lambda *a, **k: SimpleNamespace(GetLogicalProcessorInformationEx=Function(query)),
        raising=False,
    )
    assert cpu.physical_core_count() == 0


def test_cpu_count_failure_has_bounded_fallback(monkeypatch):
    monkeypatch.setattr(cpu, "performance_core_count", lambda: 0)
    monkeypatch.setattr(cpu, "physical_core_count", lambda: 0)

    def unavailable():
        raise OSError("unavailable")

    monkeypatch.setattr(cpu.os, "cpu_count", unavailable)
    assert cpu.default_threads() == 2


def test_import_does_not_load_native_libraries(monkeypatch):
    import importlib

    def forbidden(*args, **kwargs):
        raise AssertionError("Import must not load native libraries")

    monkeypatch.setattr(cpu.ctypes, "CDLL", forbidden)
    monkeypatch.setattr(cpu.ctypes, "WinDLL", forbidden, raising=False)
    importlib.reload(cpu)


# Apple Silicon: performance cores only (D-MAC-021)


def _sysctl(monkeypatch, values, *, platform="darwin", machine="arm64"):
    """Answer sysctlbyname from a dict; a missing key fails like the real ENOENT."""
    asked = []

    def query(name, output, output_size, new, new_size):
        asked.append(name)
        assert new is None and new_size == 0
        if name not in values:
            return -1
        output._obj.value = values[name]
        output_size._obj.value = 4
        return 0

    monkeypatch.setattr(cpu.sys, "platform", platform)
    monkeypatch.setattr(cpu.os, "uname", lambda: SimpleNamespace(machine=machine), raising=False)
    monkeypatch.setattr(
        cpu.ctypes, "CDLL", lambda *a, **k: SimpleNamespace(sysctlbyname=Function(query))
    )
    monkeypatch.setattr(cpu.os, "cpu_count", lambda: 8)
    return asked


def test_apple_silicon_default_uses_performance_cores(monkeypatch):
    asked = _sysctl(monkeypatch, {b"hw.perflevel0.physicalcpu": 4, b"hw.physicalcpu": 8})
    assert cpu.performance_core_count() == 4
    assert cpu.default_threads() == 4
    assert asked[-1] == b"hw.perflevel0.physicalcpu"
    assert b"hw.physicalcpu" not in asked


def test_apple_silicon_performance_cores_are_capped_at_eight(monkeypatch):
    _sysctl(monkeypatch, {b"hw.perflevel0.physicalcpu": 12, b"hw.physicalcpu": 16})
    assert cpu.default_threads() == 8


@pytest.mark.parametrize("performance", [None, 0])
def test_apple_silicon_without_performance_key_uses_physical_cores(monkeypatch, performance):
    values = {b"hw.physicalcpu": 6}
    if performance is not None:
        values[b"hw.perflevel0.physicalcpu"] = performance
    asked = _sysctl(monkeypatch, values)
    assert cpu.performance_core_count() == 0
    assert cpu.default_threads() == 6
    assert asked[-1] == b"hw.physicalcpu"


def test_intel_mac_keeps_physical_core_default(monkeypatch):
    asked = _sysctl(
        monkeypatch,
        {b"hw.perflevel0.physicalcpu": 2, b"hw.physicalcpu": 6},
        machine="x86_64",
    )
    assert cpu.performance_core_count() == 0
    assert cpu.default_threads() == 6
    assert asked == [b"hw.physicalcpu"]


def test_windows_never_queries_performance_cores(monkeypatch):
    monkeypatch.setattr(cpu.sys, "platform", "win32")
    monkeypatch.setattr(cpu.ctypes, "CDLL", lambda *a, **k: pytest.fail("Darwin API used"))
    monkeypatch.setattr(cpu, "physical_core_count", lambda: 6)
    assert cpu.performance_core_count() == 0
    assert cpu.default_threads() == 6


def test_performance_query_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr(cpu.sys, "platform", "darwin")
    monkeypatch.setattr(cpu.os, "uname", lambda: SimpleNamespace(machine="arm64"), raising=False)

    def unavailable(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(cpu.ctypes, "CDLL", unavailable)
    monkeypatch.setattr(cpu.os, "cpu_count", lambda: 6)
    assert cpu.performance_core_count() == 0
    assert cpu.default_threads() == 3


@pytest.mark.skipif(
    sys.platform != "darwin" or cpu.os.uname().machine != "arm64",
    reason="real Apple Silicon sysctl API",
)
def test_real_apple_silicon_performance_core_query():
    performance = cpu.performance_core_count()
    assert 1 <= performance <= cpu.physical_core_count()
    assert cpu.default_threads() == min(8, performance)
