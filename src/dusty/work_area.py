"""Conservative ownership and destination boundaries for disposable work."""

import hashlib
import json
import logging
import stat
from pathlib import Path
from uuid import UUID, uuid4

from dusty.runtime_paths import RuntimePaths

MARKER = ".dusty-owned.json"
_LOG = logging.getLogger("dusty")


def linked(path: Path) -> bool:
    """Check every existing ancestor, including non-symlink Windows reparse points."""
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            return True
    return False


def managed_roots(paths: RuntimePaths) -> tuple[Path, ...]:
    return (
        *(paths.user_dir / name for name in ("work", "models", "state", "logs")),
        paths.models_dir,
        paths.bin_dir.parent,
    )


def managed_destination(path: Path, paths: RuntimePaths) -> bool:
    candidate = path.resolve()
    return any(candidate.is_relative_to(root.resolve()) for root in managed_roots(paths))


def protected_paths(user_dir: Path) -> set[Path] | None:
    """Read protection metadata without quarantining or changing any user file."""
    protected: set[Path] = set()

    def inspect(value: object, key: str = "") -> None:
        if isinstance(value, dict):
            for name, item in value.items():
                inspect(item, name)
        elif isinstance(value, list):
            for item in value:
                inspect(item, key)
        elif key in {"output_dir", "outputs", "source", "preserved_paths"} and isinstance(
            value, str
        ):
            protected.add(Path(value).resolve())

    try:
        files = [user_dir / "settings.json", user_dir / "state/queue.json"]
        files += list(user_dir.glob("settings.json.corrupt-*"))
        files += list((user_dir / "state").glob("queue.json.corrupt-*"))
        for file in files:
            if linked(file):
                return None
            if file.exists():
                value = json.loads(file.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or value.get("schema_version") != 1:
                    return None
                inspect(value)
        return protected
    except (OSError, ValueError, TypeError):
        return None


def _fingerprint(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cleanup_owned(directory: Path, *, protected: set[Path] | None) -> bool:
    """Delete only a fully matching inventory, never recurse or follow a link."""
    try:
        if (
            protected is None
            or linked(directory)
            or any(
                p.is_relative_to(directory.resolve()) or directory.resolve().is_relative_to(p)
                for p in protected
            )
        ):
            raise ValueError
        marker = directory / MARKER
        if linked(marker):
            raise ValueError
        data = json.loads(marker.read_text(encoding="utf-8"))
        if (
            data.get("schema") != 1
            or data.get("directory") != directory.name
            or data.get("purpose") not in {"job", "probe", "selftest", "device-probe"}
            or not isinstance(data.get("files"), dict)
        ):
            raise ValueError
        suffix = directory.name.removeprefix(data["purpose"] + "-")
        if directory.name != f"{data['purpose']}-{UUID(suffix)}":
            raise ValueError
        entries = list(directory.iterdir())
        inventory = data["files"]
        if {p.name for p in entries} != {MARKER, *inventory}:
            raise ValueError
        for entry in entries:
            if linked(entry) or not entry.is_file():
                raise ValueError
            if entry.name != MARKER and _fingerprint(entry) != inventory[entry.name]:
                raise ValueError
        # Recheck the whole inventory before the first removal. Never rmtree.
        for entry in entries:
            if linked(entry):
                raise ValueError
        for entry in entries:
            if entry.name != MARKER:
                entry.unlink()
        marker.unlink()
        directory.rmdir()
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        _LOG.info("work_cleanup=preserved")
        return False


class OwnedWork:
    """A random exclusive directory with an explicit file inventory from creation."""

    def __init__(self, root: Path, purpose: str):
        if linked(root):
            raise ValueError("Unsafe work area")
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"{purpose}-{uuid4()}"
        self.path.mkdir()
        self.purpose = purpose
        self.files: dict[str, str] = {}
        self._write_marker()

    def _write_marker(self) -> None:
        marker = self.path / MARKER
        if linked(marker):
            raise ValueError("Unsafe work marker")
        marker.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "directory": self.path.name,
                    "purpose": self.purpose,
                    "files": self.files,
                }
            ),
            encoding="utf-8",
        )

    def record(self, *names: str) -> None:
        """Record only explicitly named outputs of the operation just performed."""
        for name in names:
            if Path(name).name != name:
                raise ValueError("Work inventory must be flat")
            file = self.path / name
            if file.exists() and not linked(file) and file.is_file():
                self.files[name] = _fingerprint(file)
        self._write_marker()

    def cleanup(self, user_dir: Path) -> bool:
        return cleanup_owned(self.path, protected=protected_paths(user_dir))


def sanitize_output(paths: RuntimePaths) -> bool:
    """Preserve a legacy internal destination forever and clear only its setting."""
    from dusty.queue.storage import load_settings, save_settings

    file = paths.user_dir / "settings.json"
    settings = load_settings(file)
    output = settings.get("output_dir")
    if not output or not managed_destination(Path(output), paths):
        return False
    preserved = set(settings.get("preserved_paths", []))
    preserved.add(str(Path(output).resolve()))
    settings["preserved_paths"] = sorted(preserved)
    settings.pop("output_dir")
    settings["managed_folder_notice"] = True
    save_settings(file, settings)
    return True
