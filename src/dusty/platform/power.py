"""Request Windows idle-sleep prevention for the lifetime of a batch."""

import ctypes
import os
from collections.abc import Iterator
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _set_execution_state(flags: int) -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32
    return int(kernel.SetThreadExecutionState(flags))


@contextmanager
def prevent_sleep() -> Iterator[None]:
    """Keep the system awake, allow display sleep, and restore the prior state."""
    previous = _set_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) if os.name == "nt" else 0
    try:
        yield
    finally:
        if previous:
            _set_execution_state(previous | ES_CONTINUOUS)
