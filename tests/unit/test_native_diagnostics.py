"""Real first-chance observation preserves dispatch and excludes user content."""

import ctypes as C
import json
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from dusty.privacy import native_diagnostics as N


def raise_event(code=N.EVENT, secret="CANARY_PATIENT_JANE_DOE private transcript C:\\secret"):
    kernel = C.WinDLL("kernel32")
    kernel.RaiseException.argtypes = [C.c_ulong, C.c_ulong, C.c_ulong, C.c_void_p]
    text = C.create_unicode_buffer(secret)
    info = (C.c_size_t * 1)(C.addressof(text))
    with pytest.raises(OSError):  # Observer must leave normal SEH/ctypes handling intact.
        kernel.RaiseException(code, 0, 1, info)


def test_real_native_capture_is_bounded_redacted_and_preserves_dispatch(tmp_path):
    try:
        assert N.install_capture(tmp_path)
        assert N.is_installed()
        N.set_context("ci-fixture")
        raise_event()
        path = tmp_path / "logs/native-diagnostic.jsonl"
        first = path.read_text(encoding="ascii")
        event = json.loads(first.splitlines()[-1])
        assert event["exception"] == "0x8001010d"
        assert event["instruction"]["module"].lower() in {"kernelbase.dll", "kernel32.dll"}
        assert event["instruction"]["offset"].startswith("0x")
        assert 0 < len(event["frames"]) <= 32 and event["thread"] > 0
        assert event["phase"] == "ci-fixture"
        assert not any(s in first for s in ("CANARY", "private transcript", "C:\\secret"))
        raise_event(0xE0123456)
        assert path.read_text(encoding="ascii") == first
        with pytest.raises(ValueError):
            N.set_context("CANARY")
        assert N._active.frame(None) == N._active.frame(1) == {"module": "unknown", "offset": "0x0"}
        N._active.size = N.LIMIT
        raise_event()
        assert path.read_text(encoding="ascii") == first
        N._active.size = N.LIMIT - 1
        raise_event()
        assert path.read_text(encoding="ascii") == first
        N.close_capture()
        assert not N.is_installed()
        assert N.install_capture(tmp_path)  # Previous validated records survive restart.
        raise_event()
        assert len(path.read_text(encoding="ascii").splitlines()) == 3
    finally:
        N.close_capture()


@pytest.mark.parametrize(
    "mode", ["unknown", "wrong-event", "wrong-phase", "full", "protected", "link", "denied"]
)
def test_capture_preserves_unsafe_or_unavailable_storage(tmp_path, monkeypatch, mode):
    path = tmp_path / "logs/native-diagnostic.jsonl"
    path.parent.mkdir()
    content = b"not a Dusty diagnostic"
    if mode == "full":
        content = b"x" * N.LIMIT
    elif mode in {"wrong-event", "wrong-phase"}:
        content = json.dumps(
            {
                "exception": "wrong" if mode == "wrong-event" else "0x8001010d",
                "phase": "wrong" if mode == "wrong-phase" else "startup",
                "instruction": {},
                "frames": [],
                "thread": 1,
            }
        ).encode()
        content = N.HEADER + content + b"\n"
    elif mode == "protected":
        (tmp_path / "settings.json").write_text(
            json.dumps({"schema_version": 1, "preserved_paths": [str(path.parent)]}),
            encoding="utf-8",
        )
    elif mode == "link":
        monkeypatch.setattr("dusty.work_area.linked", lambda p: True)
    elif mode == "denied":
        content = N.HEADER

        def denied(*args):
            raise OSError("unwritable")

        monkeypatch.setattr(N, "Capture", denied)
    path.write_bytes(content)
    assert not N.install_capture(tmp_path)
    assert path.read_bytes() == content
    assert not N.is_installed()


def test_capture_failure_does_not_handle_exception_or_replace_faulthandler(tmp_path):
    assert N.install_capture(tmp_path)
    active = N._active
    record = N.Record()
    record.code = N.EVENT
    pointers = N.Pointers(C.pointer(record), None)
    try:
        active.busy = True
        assert active._observe(C.pointer(pointers)) == 0
        active.busy = False
        original = active.stream
        active.stream = MagicMock()
        active.stream.write.side_effect = OSError("disk full")
        assert active._observe(C.pointer(pointers)) == 0
        active.stream = original
        active.close()
        active.close()
    finally:
        N.close_capture()


def test_registration_failure_closes_its_file(tmp_path, monkeypatch):
    fake = MagicMock()
    fake.AddVectoredExceptionHandler.return_value = None
    monkeypatch.setattr(N.C, "WinDLL", lambda *a, **k: fake)
    path = tmp_path / "capture"
    with pytest.raises(OSError):
        N.Capture(path)
    path.unlink()  # Windows denies this if failed registration left an open handle.


@pytest.mark.parametrize("opt_in", [False, True])
def test_real_entry_capture_is_opt_in_before_qt_import(tmp_path, opt_in):
    script = r"""
import importlib.abc, runpy, sys
class Check(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'PySide6':
            from dusty.privacy.native_diagnostics import is_installed
            from dusty.privacy.network_guard import is_installed as guarded
            assert is_installed() is EXPECT_CAPTURE and guarded()
            print('capture and network guard before Qt')
            raise SystemExit(0)
sys.meta_path.insert(0, Check())
sys.argv=['dusty']
runpy.run_module('dusty',run_name='__main__')
"""
    import os

    script = script.replace("EXPECT_CAPTURE", str(opt_in))
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "LOCALAPPDATA": str(tmp_path),
            "DUSTY_NATIVE_DIAGNOSTICS": "1" if opt_in else "0",
        },
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert b"capture and network guard before Qt" in result.stdout
