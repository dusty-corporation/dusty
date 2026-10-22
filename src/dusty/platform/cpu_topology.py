"""Count active physical cores using the Windows processor relationship API."""

import ctypes
import math
import os
from ctypes import wintypes

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_query = _kernel32.GetLogicalProcessorInformationEx
_query.argtypes = [wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
_query.restype = wintypes.BOOL


def physical_core_count() -> int:
    """Count RelationProcessorCore records, including hybrid P and E cores."""
    length = wintypes.DWORD(0)
    _query(0, None, ctypes.byref(length))
    if length.value < 8:
        return 0
    buffer = ctypes.create_string_buffer(length.value)
    if not _query(0, buffer, ctypes.byref(length)):
        return 0
    offset = 0
    count = 0
    while offset + 8 <= length.value:
        relationship = int.from_bytes(buffer.raw[offset : offset + 4], "little")
        size = int.from_bytes(buffer.raw[offset + 4 : offset + 8], "little")
        if size < 8 or offset + size > length.value:
            return 0
        if relationship == 0:
            count += 1
        offset += size
    return count if offset == length.value else 0


def default_threads() -> int:
    """Use physical cores when available and cap the engine default at eight."""
    physical = physical_core_count()
    fallback = math.ceil((os.cpu_count() or 4) / 2)
    return max(1, min(8, physical or fallback))
