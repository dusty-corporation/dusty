"""Bounded, passive first-chance HRESULT capture with no user-content fields.

Observe only ISSUE-027's exact exception. Always continue normal dispatch;
neither this hook nor capture failure handles or suppresses an exception.
"""

import atexit
import ctypes as C
import json
import re
import sys
from ctypes import wintypes as W
from pathlib import Path

LIMIT = 128 * 1024
HEADER = b'{"schema":1,"purpose":"native-diagnostic"}\n'
EVENT = 0x8001010D
CONTEXTS = {"startup", "qt-startup", "event-loop", "self-test", "batch", "gui-check", "ci-fixture"}
_active = None


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


class Capture:
    def __init__(self, path: Path):
        self.phase = "startup"
        self.busy = False
        self.kernel = kernel = C.WinDLL("kernel32", use_last_error=True)
        callback_type = C.WINFUNCTYPE(W.LONG, C.POINTER(Pointers))
        kernel.AddVectoredExceptionHandler.argtypes = [W.ULONG, callback_type]
        kernel.AddVectoredExceptionHandler.restype = C.c_void_p
        kernel.RemoveVectoredExceptionHandler.argtypes = [C.c_void_p]
        kernel.RtlCaptureStackBackTrace.argtypes = [
            W.ULONG,
            W.ULONG,
            C.POINTER(C.c_void_p),
            C.c_void_p,
        ]
        kernel.RtlCaptureStackBackTrace.restype = W.USHORT
        kernel.GetModuleHandleExW.argtypes = [W.DWORD, C.c_void_p, C.POINTER(W.HMODULE)]
        kernel.GetModuleHandleExW.restype = W.BOOL
        kernel.GetModuleFileNameW.argtypes = [W.HMODULE, W.LPWSTR, W.DWORD]
        kernel.GetModuleFileNameW.restype = W.DWORD
        kernel.GetCurrentThreadId.restype = W.DWORD
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(HEADER)
        self.stream = path.open("ab", buffering=0)
        self.size = self.stream.tell()
        self.callback = callback_type(self._observe)  # Retain for the full registration lifetime.
        self.registration = kernel.AddVectoredExceptionHandler(1, self.callback)
        if not self.registration:
            self.stream.close()
            raise OSError("Native diagnostic registration failed")

    def frame(self, address):
        if address is None:
            return {"module": "unknown", "offset": "0x0"}
        module = W.HMODULE()
        if self.kernel.GetModuleHandleExW(6, address, C.byref(module)):
            name = C.create_unicode_buffer(32768)
            base = module.value
            if base is not None and self.kernel.GetModuleFileNameW(module, name, len(name)):
                basename = Path(name.value).name
                if re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", basename):
                    return {"module": basename, "offset": hex(address - base)}
        return {"module": "unknown", "offset": "0x0"}

    def _observe(self, pointers):
        if self.busy:
            return 0
        try:
            if pointers.contents.record.contents.code != EVENT or self.size >= LIMIT:
                return 0
            self.busy = True
            addresses = (C.c_void_p * 32)()
            count = self.kernel.RtlCaptureStackBackTrace(0, 32, addresses, None)
            event = {
                "exception": "0x8001010d",
                "instruction": self.frame(pointers.contents.record.contents.address),
                "frames": [self.frame(address) for address in addresses[:count]],
                "thread": int(self.kernel.GetCurrentThreadId()),
                "phase": self.phase,
            }
            # Never inspect EXCEPTION_INFORMATION, CPU context, Python frames,
            # message arguments, locals, file names or recording/model state.
            data = (json.dumps(event, separators=(",", ":")) + "\n").encode("ascii")
            if self.size + len(data) <= LIMIT:
                self.size += self.stream.write(data)
        except BaseException:
            pass  # Observation cannot change exception dispatch, even on full disk.
        finally:
            self.busy = False
        return 0  # EXCEPTION_CONTINUE_SEARCH, also for the observed HRESULT.

    def close(self) -> None:
        if self.registration:
            self.kernel.RemoveVectoredExceptionHandler(self.registration)
            self.registration = None
            self.stream.close()


def close_capture() -> None:
    global _active
    if _active is not None:
        _active.close()
        _active = None


def is_installed() -> bool:
    return _active is not None


def set_context(phase: str) -> None:
    if phase not in CONTEXTS:
        raise ValueError("Unknown native diagnostic context")
    if _active is not None:
        _active.phase = phase


def valid_capture(path: Path) -> bool:
    """Recognize only the owned header and bounded, fixed-schema diagnostic data."""
    try:
        if path.stat().st_size > LIMIT:
            return False
        data = path.read_bytes()
        if not data.startswith(HEADER):
            return False
        for line in data[len(HEADER) :].splitlines():
            value = json.loads(line)
            if set(value) != {"exception", "instruction", "frames", "thread", "phase"}:
                return False
            if value["exception"] != "0x8001010d" or value["phase"] not in CONTEXTS:
                return False
            frames = [value["instruction"], *value["frames"]]
            if len(frames) > 33 or type(value["thread"]) is not int:
                return False
            for frame in frames:
                if set(frame) != {"module", "offset"}:
                    return False
                if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", frame["module"]):
                    return False
                if not re.fullmatch(r"0x[0-9a-f]+", frame["offset"]):
                    return False
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def install_capture(user_dir: Path) -> bool:
    """Best effort, before Qt loads; retain protected/unfamiliar files unchanged."""
    global _active
    if sys.platform != "win32":
        return False
    close_capture()
    from dusty.work_area import canonical, linked, protected_paths

    logs = user_dir / "logs"
    target = logs / "native-diagnostic.jsonl"
    try:
        protected = protected_paths(user_dir)
        if (
            protected is None
            or linked(target)
            or any(
                canonical(p).is_relative_to(canonical(logs))
                or canonical(logs).is_relative_to(canonical(p))
                for p in protected
            )
        ):
            return False
        if target.exists():
            if target.stat().st_size >= LIMIT or not valid_capture(target):
                return False
        logs.mkdir(parents=True, exist_ok=True)
        _active = Capture(target)
        return True
    except (OSError, ValueError, TypeError, UnicodeError):
        return False


atexit.register(close_capture)
