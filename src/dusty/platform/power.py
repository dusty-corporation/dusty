"""Best-effort idle-sleep prevention scoped to a processing batch."""

import ctypes
import logging
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
_LOG = logging.getLogger("dusty")


def _set_execution_state(flags: int) -> int:
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise OSError("Windows API unavailable")
    kernel = loader("kernel32", use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32
    return int(kernel.SetThreadExecutionState(flags))


def _darwin_assertion() -> tuple[int, Callable[[int], int]]:
    # Absolute system-framework paths avoid library discovery subprocesses.
    core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    make_string = core.CFStringCreateWithCString
    make_string.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    make_string.restype = ctypes.c_void_p
    free_string = core.CFRelease
    free_string.argtypes = [ctypes.c_void_p]
    free_string.restype = None
    create = io.IOPMAssertionCreateWithName
    create.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    create.restype = ctypes.c_int32
    release = io.IOPMAssertionRelease
    release.argtypes = [ctypes.c_uint32]
    release.restype = ctypes.c_int32
    owned = []
    try:
        for text in (b"PreventUserIdleSystemSleep", b"Dusty transcription"):
            value = make_string(None, text, 0x08000100)  # kCFStringEncodingUTF8
            if not value:
                raise OSError("Power assertion string allocation failed")
            owned.append(value)
        identity = ctypes.c_uint32(0)
        # kIOPMAssertionLevelOn=255; do not prevent ordinary display sleep.
        if create(owned[0], 255, owned[1], ctypes.byref(identity)) != 0 or not identity.value:
            raise OSError("Power assertion acquisition failed")
        return identity.value, release
    finally:
        for value in reversed(owned):
            free_string(value)


@contextmanager
def prevent_sleep() -> Iterator[None]:
    """Prevent idle system sleep when possible, without changing user settings."""
    if sys.platform == "win32":
        previous = _set_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        try:
            yield
        finally:
            if previous:
                _set_execution_state(previous | ES_CONTINUOUS)
    elif sys.platform == "darwin":
        try:
            assertion = _darwin_assertion()
        except (OSError, AttributeError):
            _LOG.warning("POWER_ACQUIRE_FAILED")
            assertion = None
        try:
            yield
        finally:
            if assertion is not None:
                identity, release = assertion
                try:
                    status = release(identity)
                except (OSError, AttributeError):
                    status = -1
                if status != 0:
                    # Never mask a processing exception with a power API failure.
                    _LOG.warning("POWER_RELEASE_FAILED")
    else:
        yield
