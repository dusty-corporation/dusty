"""Read local GPU identity for backend probe invalidation, without logging it.

Windows hashes installed display driver IDs and versions from the registry.
macOS hashes the hardware model, CPU brand and OS version, because the Metal
driver ships with the OS. Neither path starts a process.
"""

import ctypes
import hashlib
import platform as _platform
import sys

_DISPLAY_CLASS = "SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}"
_MAC_KEYS = (b"hw.model", b"machdep.cpu.brand_string", b"kern.osversion")


def _windows_display_driver_signature() -> str:
    if sys.platform != "win32":
        raise OSError("Windows registry unavailable on this platform")
    import winreg

    entries: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _DISPLAY_CLASS) as parent:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(parent, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(parent, name) as child:
                        values = []
                        for key in ("MatchingDeviceId", "DriverVersion", "DriverDate"):
                            try:
                                value, _kind = winreg.QueryValueEx(child, key)
                                values.append(str(value))
                            except OSError:
                                values.append("")
                        if any(values):
                            entries.append("|".join(values))
                except OSError:
                    continue
    except OSError:
        return "unavailable"
    return hashlib.sha256("\n".join(sorted(entries)).encode()).hexdigest()


def _sysctl_string(name: bytes) -> str:
    """Read one string sysctl through libSystem; discovery tools may spawn shells."""
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
    length = ctypes.c_size_t(0)
    if query(name, None, ctypes.byref(length), None, 0) != 0 or not 0 < length.value <= 4096:
        return ""
    buffer = ctypes.create_string_buffer(length.value)
    if query(name, buffer, ctypes.byref(length), None, 0) != 0:
        return ""
    return buffer.value.decode("utf-8", "replace")


def _mac_gpu_signature() -> str:
    values = []
    for key in _MAC_KEYS:
        try:
            values.append(_sysctl_string(key))
        except (AttributeError, OSError, ValueError):
            values.append("")
    try:
        values.append(_platform.mac_ver()[0])
    except (OSError, ValueError):
        values.append("")
    if not any(values):
        return "unavailable"
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def display_driver_signature(platform: str | None = None) -> str:
    """Hash this platform's GPU identity; return "unavailable" when it cannot be read."""
    selected = sys.platform if platform is None else platform
    if selected == "win32":
        return _windows_display_driver_signature()
    if selected == "darwin":
        return _mac_gpu_signature()
    return "unavailable"
