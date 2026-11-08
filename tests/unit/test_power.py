"""Keep sleep assertions scoped to a batch, including native API failures."""

import ctypes
import logging
import sys
from types import SimpleNamespace

import pytest

from dusty.platform import power


@pytest.fixture(autouse=True)
def isolate_power_log_capture(monkeypatch):
    # Other tests configure the shared logger not to propagate to pytest's root.
    # Restore its original setting after each case; keep production filters intact.
    monkeypatch.setattr(power._LOG, "propagate", True)


class Function:
    def __init__(self, call):
        self.call = call

    def __call__(self, *args):
        return self.call(*args)


def test_batch_power_state_is_restored_after_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(power.sys, "platform", "win32")

    def set_state(flags):
        calls.append(flags)
        return power.ES_CONTINUOUS | 2

    monkeypatch.setattr(power, "_set_execution_state", set_state)
    with pytest.raises(RuntimeError), power.prevent_sleep():
        raise RuntimeError("Batch failed")
    assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED, power.ES_CONTINUOUS | 2]


def test_windows_failed_acquire_does_not_restore_unowned_state(monkeypatch):
    calls = []
    monkeypatch.setattr(power.sys, "platform", "win32")
    monkeypatch.setattr(power, "_set_execution_state", lambda flags: calls.append(flags) or 0)
    with power.prevent_sleep():
        pass
    assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED]


def fake_native(monkeypatch, *, null_at=0, create_status=0, release_status=0, assertion_id=42):
    made = []
    freed = []
    released = []

    def make(allocator, text, encoding):
        assert allocator is None and encoding == 0x08000100
        made.append(text)
        return None if len(made) == null_at else len(made)

    def create(kind, level, name, output):
        assert (kind, level, name) == (1, 255, 2)
        output._obj.value = assertion_id
        return create_status

    def release(value):
        released.append(value)
        return release_status

    cf = SimpleNamespace(
        CFStringCreateWithCString=Function(make),
        CFRelease=Function(lambda value: freed.append(value)),
    )
    io = SimpleNamespace(
        IOPMAssertionCreateWithName=Function(create), IOPMAssertionRelease=Function(release)
    )

    def load(path):
        return cf if "CoreFoundation" in path else io

    monkeypatch.setattr(power.ctypes, "CDLL", load)
    monkeypatch.setattr(power.sys, "platform", "darwin")
    return SimpleNamespace(made=made, freed=freed, released=released, cf=cf, io=io)


def test_darwin_strings_and_assertion_have_checked_ownership(monkeypatch):
    native = fake_native(monkeypatch)
    with power.prevent_sleep():
        assert native.released == []
        assert native.freed == [2, 1]
    assert native.released == [42]
    assert native.made == [b"PreventUserIdleSystemSleep", b"Dusty transcription"]
    assert native.cf.CFStringCreateWithCString.restype is ctypes.c_void_p
    assert native.cf.CFRelease.restype is None
    assert native.io.IOPMAssertionCreateWithName.argtypes[-1] == ctypes.POINTER(ctypes.c_uint32)
    assert native.io.IOPMAssertionRelease.restype is ctypes.c_int32


def test_darwin_releases_after_processing_exception(monkeypatch):
    native = fake_native(monkeypatch)
    with pytest.raises(ValueError, match="processing"), power.prevent_sleep():
        raise ValueError("processing")
    assert native.released == [42]


@pytest.mark.parametrize(("null_at", "freed"), [(1, []), (2, [1])])
def test_darwin_failed_string_allocation_frees_only_owned_strings(
    monkeypatch, caplog, null_at, freed
):
    native = fake_native(monkeypatch, null_at=null_at)
    with caplog.at_level(logging.WARNING), power.prevent_sleep():
        pass
    assert native.freed == freed
    assert native.released == []
    assert "POWER_ACQUIRE_FAILED" in caplog.text


@pytest.mark.parametrize(("status", "identity"), [(5, 42), (0, 0)])
def test_darwin_failed_assertion_does_not_release_unowned_id(monkeypatch, caplog, status, identity):
    native = fake_native(monkeypatch, create_status=status, assertion_id=identity)
    with caplog.at_level(logging.WARNING), power.prevent_sleep():
        pass
    assert native.freed == [2, 1]
    assert native.released == []
    assert "POWER_ACQUIRE_FAILED" in caplog.text


def test_darwin_framework_failure_is_redacted_and_batch_continues(monkeypatch, caplog):
    monkeypatch.setattr(power.sys, "platform", "darwin")

    def unavailable(path):
        raise OSError("/private/input.wav")

    monkeypatch.setattr(power.ctypes, "CDLL", unavailable)
    with caplog.at_level(logging.WARNING), power.prevent_sleep():
        pass
    assert "POWER_ACQUIRE_FAILED" in caplog.text
    assert "/private/input.wav" not in caplog.text


def test_darwin_release_failure_preserves_processing_exception(monkeypatch, caplog):
    native = fake_native(monkeypatch, release_status=5)
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(ValueError, match="processing"),
        power.prevent_sleep(),
    ):
        raise ValueError("processing")
    assert native.released == [42]
    assert "POWER_RELEASE_FAILED" in caplog.text


def test_nested_assertions_have_independent_release(monkeypatch):
    monkeypatch.setattr(power.sys, "platform", "darwin")
    acquired = []
    released = []

    def acquire():
        identity = len(acquired) + 1
        acquired.append(identity)
        return identity, lambda value: released.append(value) or 0

    monkeypatch.setattr(power, "_darwin_assertion", acquire)
    with power.prevent_sleep(), power.prevent_sleep():
        assert released == []
    assert acquired == [1, 2]
    assert released == [2, 1]


def test_darwin_raised_release_error_does_not_fail_successful_batch(monkeypatch, caplog):
    monkeypatch.setattr(power.sys, "platform", "darwin")

    def release(identity):
        raise OSError("private details")

    monkeypatch.setattr(power, "_darwin_assertion", lambda: (42, release))
    with caplog.at_level(logging.WARNING), power.prevent_sleep():
        pass
    assert "POWER_RELEASE_FAILED" in caplog.text
    assert "private details" not in caplog.text


def test_windows_api_signature(monkeypatch):
    function = Function(lambda flags: flags)
    monkeypatch.setattr(
        power.ctypes,
        "WinDLL",
        lambda *a, **k: SimpleNamespace(SetThreadExecutionState=function),
        raising=False,
    )
    assert power._set_execution_state(power.ES_CONTINUOUS) == power.ES_CONTINUOUS
    assert function.argtypes == [ctypes.c_uint32]
    assert function.restype is ctypes.c_uint32


def test_other_platform_is_a_noop(monkeypatch):
    monkeypatch.setattr(power.sys, "platform", "other")
    with power.prevent_sleep():
        pass


@pytest.mark.skipif(sys.platform != "darwin", reason="real IOKit assertion API")
def test_real_darwin_assertion_create_and_release():
    identity, release = power._darwin_assertion()
    assert identity != 0
    assert release(identity) == 0
