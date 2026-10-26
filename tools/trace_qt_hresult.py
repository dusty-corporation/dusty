"""Capture module/offset evidence for a handled Windows COM HRESULT in pytest.

Diagnostic only. Returns EXCEPTION_CONTINUE_SEARCH, never suppresses the event,
never changes faulthandler, and records no paths, arguments or user content.
"""

import ctypes as C
import json
import sys
from ctypes import wintypes as W
from pathlib import Path

import pytest


class Record(C.Structure):
    _fields_ = [
        ("code", W.DWORD),
        ("flags", W.DWORD),
        ("nested", C.c_void_p),
        ("address", C.c_void_p),
        ("count", W.DWORD),
        ("info", C.c_size_t * 15),
    ]


class Pointers(C.Structure):
    _fields_ = [("record", C.POINTER(Record)), ("context", C.c_void_p)]


def main(arguments: list[str]) -> int:
    if sys.platform != "win32":
        return 2
    output = Path(__file__).resolve().parents[1] / "build/m6-qt-native-events.jsonl"
    output.parent.mkdir(exist_ok=True)
    kernel = C.WinDLL("kernel32", use_last_error=True)
    callback_type = C.WINFUNCTYPE(W.LONG, C.POINTER(Pointers))
    kernel.AddVectoredExceptionHandler.argtypes = [W.ULONG, callback_type]
    kernel.AddVectoredExceptionHandler.restype = C.c_void_p
    kernel.RemoveVectoredExceptionHandler.argtypes = [C.c_void_p]
    kernel.RtlCaptureStackBackTrace.argtypes = [W.ULONG, W.ULONG, C.POINTER(C.c_void_p), C.c_void_p]
    kernel.RtlCaptureStackBackTrace.restype = W.USHORT
    kernel.GetModuleHandleExW.argtypes = [W.DWORD, C.c_void_p, C.POINTER(W.HMODULE)]
    kernel.GetModuleHandleExW.restype = W.BOOL
    kernel.GetModuleFileNameW.argtypes = [W.HMODULE, W.LPWSTR, W.DWORD]
    kernel.GetModuleFileNameW.restype = W.DWORD
    with output.open("x", encoding="utf-8") as stream:

        @callback_type
        def observe(pointers):
            try:
                if pointers.contents.record.contents.code != 0x8001010D:
                    return 0
                addresses = (C.c_void_p * 64)()
                count = kernel.RtlCaptureStackBackTrace(0, 64, addresses, None)
                frames = []
                for address in addresses[:count]:
                    if address is None:
                        continue
                    module = W.HMODULE()
                    if kernel.GetModuleHandleExW(6, address, C.byref(module)):
                        name = C.create_unicode_buffer(32768)
                        base = module.value
                        if base is not None and kernel.GetModuleFileNameW(module, name, len(name)):
                            frames.append(
                                {
                                    "module": Path(name.value).name,
                                    "offset": hex(address - base),
                                }
                            )
                stream.write(json.dumps({"exception": "0x8001010d", "frames": frames}) + "\n")
                stream.flush()
            except BaseException:
                pass  # Observation must not affect exception dispatch.
            return 0  # EXCEPTION_CONTINUE_SEARCH, including the observed HRESULT.

        registration = kernel.AddVectoredExceptionHandler(1, observe)
        if not registration:
            raise OSError("Could not register passive exception observer")
        try:
            return int(pytest.main(arguments))
        finally:
            kernel.RemoveVectoredExceptionHandler(registration)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
