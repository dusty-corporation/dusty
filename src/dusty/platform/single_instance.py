"""Per-user, session-local GUI ownership and a content-free activation signal."""

import ctypes
import hashlib
from ctypes import wintypes
from pathlib import Path

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_kernel.CreateMutexW.restype = wintypes.HANDLE
_kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
_kernel.CreateEventW.restype = wintypes.HANDLE
_kernel.SetEvent.argtypes = [wintypes.HANDLE]
_kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel.CloseHandle.argtypes = [wintypes.HANDLE]


class GuiInstance:
    """Kernel handles disappear after a crash; no lock file or personal data is stored."""

    def __init__(self, user_dir: Path):
        key = hashlib.sha256(str(user_dir.resolve()).casefold().encode()).hexdigest()
        self.event = _kernel.CreateEventW(None, False, False, f"Local\\Dusty-activate-{key}")
        if not self.event:
            raise ctypes.WinError(ctypes.get_last_error())
        self.mutex = _kernel.CreateMutexW(None, False, f"Local\\Dusty-gui-{key}")
        error = ctypes.get_last_error()
        if not self.mutex:
            self.close()
            raise ctypes.WinError(error)
        self.owner = error != 183  # ERROR_ALREADY_EXISTS, captured before another API call.
        if not self.owner:
            # Transfer foreground permission from the user's second launch.
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
            user.AllowSetForegroundWindow(0xFFFFFFFF)
            _kernel.SetEvent(self.event)

    def activation_requested(self) -> bool:
        return _kernel.WaitForSingleObject(self.event, 0) == 0

    def close(self) -> None:
        for name in ("mutex", "event"):
            handle = getattr(self, name, None)
            if handle:
                _kernel.CloseHandle(handle)
                setattr(self, name, None)


def activate_window(window) -> None:
    if window.isMinimized():
        window.showNormal()
    window.show()
    window.raise_()
    window.activateWindow()
