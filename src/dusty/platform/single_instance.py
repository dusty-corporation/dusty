"""Lazy platform selection for GUI ownership and content-free activation."""

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .windows_instance import GuiInstance as GuiInstance

__all__ = ["GuiInstance", "activate_window"]


def __getattr__(name: str) -> Any:
    if name != "GuiInstance":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if sys.platform == "darwin":
        from .mac_instance import GuiInstance
    elif sys.platform == "win32":
        from .windows_instance import GuiInstance
    else:
        raise OSError("GUI instance ownership is unavailable on this platform")
    return GuiInstance


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


def activate_window(window) -> None:
    if window.isMinimized():
        window.showNormal()
    window.show()
    window.raise_()
    window.activateWindow()
