"""Offline queue APIs, loading coordination only when it is requested."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator import Coordinator as Coordinator
    from .coordinator import cleanup_orphaned_work as cleanup_orphaned_work
    from .storage import clear_history as clear_history
    from .storage import load_batch as load_batch
    from .storage import save_batch as save_batch

__all__ = [
    "Coordinator",
    "cleanup_orphaned_work",
    "clear_history",
    "load_batch",
    "save_batch",
]


def __getattr__(name: str) -> Any:
    """Keep pure scanning/storage imports independent of coordinator loading."""
    if name in {"Coordinator", "cleanup_orphaned_work"}:
        from . import coordinator

        value = getattr(coordinator, name)
    elif name in {"clear_history", "load_batch", "save_batch"}:
        from . import storage

        value = getattr(storage, name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
