"""Read local Windows display-driver identity for Vulkan probe invalidation."""

import hashlib
import winreg

_DISPLAY_CLASS = "SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}"


def display_driver_signature() -> str:
    """Hash installed display adapter driver IDs and versions, without logging them."""
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
