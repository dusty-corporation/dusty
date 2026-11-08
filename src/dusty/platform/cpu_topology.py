"""Query physical CPU cores through the current operating system's native API."""

import ctypes
import math
import os
import sys


def _windows_physical_core_count() -> int:
    # Fixed-width Windows ABI types also allow realistic tests on another OS.
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        raise OSError("Windows API unavailable")
    kernel = loader("kernel32", use_last_error=True)
    query = kernel.GetLogicalProcessorInformationEx
    query.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    query.restype = ctypes.c_int32
    length = ctypes.c_uint32(0)
    query(0, None, ctypes.byref(length))
    if not 8 <= length.value <= 16 * 1024 * 1024:
        return 0
    capacity = length.value
    buffer = ctypes.create_string_buffer(capacity)
    if not query(0, buffer, ctypes.byref(length)) or length.value > capacity:
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


def _darwin_sysctl_count(name: bytes) -> int:
    # Use the system library directly; discovery helpers may spawn shell tools.
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    query = library.sysctlbyname
    query.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
        ctypes.c_size_t,
    ]
    query.restype = ctypes.c_int
    count = ctypes.c_int(0)
    length = ctypes.c_size_t(ctypes.sizeof(count))
    result = query(name, ctypes.byref(count), ctypes.byref(length), None, 0)
    if result != 0 or length.value != ctypes.sizeof(count):
        return 0
    return max(0, count.value)


def _darwin_physical_core_count() -> int:
    return _darwin_sysctl_count(b"hw.physicalcpu")


def physical_core_count() -> int:
    """Return active physical cores, or zero when no trustworthy query is available."""
    try:
        if sys.platform == "win32":
            return _windows_physical_core_count()
        if sys.platform == "darwin":
            return _darwin_physical_core_count()
    except (AttributeError, OSError, ValueError, OverflowError):
        pass
    return 0


def performance_core_count() -> int:
    """Return Apple Silicon performance cores, or zero when unknown or not Apple Silicon."""
    try:
        if sys.platform == "darwin" and os.uname().machine == "arm64":
            # Missing on older systems; the caller then uses the physical core logic.
            return _darwin_sysctl_count(b"hw.perflevel0.physicalcpu")
    except (AttributeError, OSError, ValueError, OverflowError):
        pass
    return 0


def default_threads() -> int:
    """Prefer Apple Silicon performance cores, else physical cores; cap at eight.

    On Apple Silicon the efficiency cores did not shorten measured CPU runs
    (D-MAC-021), so the default uses only the performance cores.
    """
    performance = performance_core_count()
    if performance > 0:
        return min(8, performance)
    physical = physical_core_count()
    try:
        logical = os.cpu_count() or 4
    except (OSError, ValueError):
        logical = 4
    fallback = math.ceil(max(1, logical) / 2)
    return max(1, min(8, physical if physical > 0 else fallback))
