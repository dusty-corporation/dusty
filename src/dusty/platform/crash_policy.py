"""Request process-local crash mitigations; Setup separately registers WER exclusions."""

import sys


def install_crash_policy() -> None:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetErrorMode.restype = wintypes.UINT
        kernel.SetErrorMode.argtypes = [wintypes.UINT]
        kernel.SetErrorMode.restype = wintypes.UINT
        # Preserve inherited flags for ordinary unhandled crashes. This is not
        # sufficient for CRT abort/fail-fast; Setup adds per-user WER exclusions.
        kernel.SetErrorMode(kernel.GetErrorMode() | 0x0001 | 0x0002)
