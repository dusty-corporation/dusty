"""Conservative ownership and destination boundaries for disposable work."""

import hashlib
import json
import logging
import os
import stat
from pathlib import Path
from uuid import UUID, uuid4

from dusty.platform.work_lease import acquire
from dusty.runtime_paths import RuntimePaths

MARKER = ".dusty-owned.json"
MARKER_TEMP = ".dusty-owned.json.tmp"
LEASE = ".dusty-active.lock"
_LOG = logging.getLogger("dusty")


def canonical(path: Path) -> Path:
    """Use one Windows namespace for comparisons, without changing I/O paths."""
    resolved = path.resolve()
    text = str(resolved)
    if os.name == "nt":
        if text.upper().startswith("\\\\?\\UNC\\"):
            text = "\\\\" + text[8:]
        elif text.startswith(("\\\\?\\", "\\\\.\\")):
            text = text[4:]
            if len(text) < 3 or text[1:3] != ":\\":
                raise ValueError("Unsupported Windows path namespace")
        return Path(text)
    return resolved


def linked(path: Path, *, name_surrogates_only: bool = False) -> bool:
    """Check ancestors; public inputs/outputs allow non-surrogate cloud tags.

    Ownership and deletion callers retain the conservative all-reparse default.
    Windows IsReparseTagNameSurrogate tests bit 0x20000000, not the attribute.
    """
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            and (not name_surrogates_only or getattr(info, "st_reparse_tag", 0) & 0x20000000)
        ):
            return True
    return False


def managed_roots(paths: RuntimePaths) -> tuple[Path, ...]:
    return (
        paths.user_dir,
        *(paths.user_dir / name for name in ("work", "models", "state", "logs")),
        paths.models_dir,
        paths.bin_dir,
        paths.resources_dir,
        *((paths.install_dir,) if paths.install_dir else ()),
    )


def managed_destination(path: Path, paths: RuntimePaths) -> bool:
    try:
        candidate = canonical(path)
        return any(candidate.is_relative_to(canonical(root)) for root in managed_roots(paths))
    except (OSError, ValueError):
        return True


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
            protected.add(canonical(Path(value)))

    try:
        files = [user_dir / "settings.json", user_dir / "state/queue.json"]
        files += list(user_dir.glob("settings.json.corrupt-*"))
        files += list((user_dir / "state").glob("queue.json.corrupt-*"))
        for file in files:
            if linked(file):
                return None
            if file.exists():
                try:
                    value = json.loads(file.read_text(encoding="utf-8"))
                    if not isinstance(value, dict) or value.get("schema_version") != 1:
                        raise ValueError("Unknown protection schema")
                except ValueError:
                    if ".corrupt-" in file.name:
                        # An unreadable backup cannot identify extra protected paths.
                        # Owned cleanup still requires an exact hash inventory.
                        continue
                    return None
                inspect(value)
        return protected
    except (OSError, ValueError, TypeError):
        return None


def _fingerprint(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _durable_marker(path: Path, data: bytes) -> None:
    """Flush a complete marker before an atomic replacement becomes visible."""
    temporary = path.with_name(MARKER_TEMP)
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _sync_and_fingerprint(path: Path) -> str:
    """Persist a generated file before persisting its hash in the marker."""
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())
    return _fingerprint(path)


def cleanup_owned(
    directory: Path, *, protected: set[Path] | None, work_root: Path | None = None
) -> bool:
    """Remove proven disposable work while holding its exclusive OS lease."""
    held_lease = None
    try:
        if (
            protected is None
            or linked(directory)
            or any(canonical(p).is_relative_to(canonical(directory)) for p in protected)
        ):
            raise ValueError
        marker = directory / MARKER
        if linked(marker):
            raise ValueError
        lease = directory / LEASE
        lease_missing = not lease.exists()
        if not lease_missing and (not lease.is_file() or linked(lease)):
            raise ValueError
        if not lease_missing:
            held_lease = acquire(lease)
        marker_bytes = marker.read_bytes()
        zeroed = (
            len(marker_bytes) in {189, 270, 350}
            and not any(marker_bytes)
            and not lease_missing
            and work_root is not None
            and canonical(directory.parent) == canonical(work_root)
        )
        if zeroed:
            # v1.0.0 could leave an allocated, all-zero marker after a host
            # crash. Confine this exception to the exact managed work root.
            purpose = "job"
            inventory: dict[str, str] = {}
        else:
            data = json.loads(marker_bytes)
            if (
                data.get("schema") != 1
                or data.get("directory") != directory.name
                or data.get("purpose") not in {"job", "probe", "selftest", "device-probe"}
                or not isinstance(data.get("files"), dict)
            ):
                raise ValueError
            purpose = data["purpose"]
            inventory = data["files"]
        suffix = directory.name.removeprefix(purpose + "-")
        if directory.name != f"{purpose}-{UUID(suffix)}":
            raise ValueError
        if not zeroed and (
            LEASE not in inventory
            or not all(
                isinstance(name, str)
                and Path(name).name == name
                and isinstance(digest, str)
                and len(digest) == 64
                for name, digest in inventory.items()
            )
        ):
            raise ValueError
        if lease_missing:
            # v1.0.0 removed the lock before its marker. Recreate it only when
            # the marker proves this exact directory and expects our one byte.
            if inventory[LEASE] != hashlib.sha256(b"0").hexdigest():
                raise ValueError
            with lease.open("xb") as stream:
                stream.write(b"0")
                stream.flush()
                os.fsync(stream.fileno())
            held_lease = acquire(lease)
            if marker.read_bytes() != marker_bytes:
                raise ValueError
        if held_lease is None:
            raise ValueError
        # Keep the exclusive lease through validation and removal. A brief
        # availability probe would leave a race before deletion.
        entries = list(directory.iterdir())
        present = {p.name for p in entries}
        if MARKER not in present or LEASE not in present:
            raise ValueError
        # A crash can occur after a known generated file was created but before
        # record() writes its hash, or halfway through an earlier cleanup.
        # Only job outputs with fixed names may be unrecorded, and a recorded
        # file that still exists must retain its exact hash.
        pending = {"audio.wav", "raw.json"} if purpose == "job" else set()
        allowed = {MARKER, LEASE, *inventory, *pending}
        if not zeroed:
            allowed.add(MARKER_TEMP)
        if present - allowed:
            raise ValueError
        for entry in entries:
            if linked(entry) or not entry.is_file():
                raise ValueError
            if entry.name == LEASE:
                held_lease.seek(0)
                content = held_lease.read()
                if zeroed:
                    if content not in {b"0", b"\0"}:
                        raise ValueError
                elif hashlib.sha256(content).hexdigest() != inventory[LEASE] and not (
                    content == b"\0" and inventory[LEASE] == hashlib.sha256(b"0").hexdigest()
                ):
                    raise ValueError
            elif entry.name in inventory and _fingerprint(entry) != inventory[entry.name]:
                raise ValueError
        # Recheck the whole inventory before the first removal. Never rmtree.
        for entry in entries:
            if linked(entry):
                raise ValueError
        for entry in entries:
            if entry.name not in {MARKER, LEASE}:
                entry.unlink()
        # A second cleanup cannot claim the folder after this point. The
        # marker is removed while our lease is still held, then the lease file.
        marker.unlink()
        held_lease.close()
        held_lease = None
        lease.unlink()
        directory.rmdir()
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        _LOG.info("work_cleanup=preserved")
        return False
    finally:
        if held_lease is not None:
            held_lease.close()


class OwnedWork:
    """A random exclusive directory with an explicit file inventory from creation."""

    def __init__(self, root: Path, purpose: str):
        if linked(root):
            raise ValueError("Unsafe work area")
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"{purpose}-{uuid4()}"
        self.path.mkdir()
        self.purpose = purpose
        lease = self.path / LEASE
        with lease.open("xb") as stream:
            stream.write(b"0")
            stream.flush()
            os.fsync(stream.fileno())
        self._lease = acquire(lease)
        self.files: dict[str, str] = {LEASE: hashlib.sha256(b"0").hexdigest()}
        self.valid = True
        self._marker_bytes = self._data()
        _durable_marker(self.path / MARKER, self._marker_bytes)

    def _data(self) -> bytes:
        return json.dumps(
            {
                "schema": 1,
                "directory": self.path.name,
                "purpose": self.purpose,
                "files": self.files,
            }
        ).encode("utf-8")

    def record(self, *names: str) -> None:
        """Record only explicitly named outputs of the operation just performed."""
        try:
            marker = self.path / MARKER
            if not self.valid or linked(marker) or marker.read_bytes() != self._marker_bytes:
                raise ValueError("Work ownership changed")
            for name in names:
                if Path(name).name != name:
                    raise ValueError("Work inventory must be flat")
                file = self.path / name
                if file.exists() and not linked(file) and file.is_file():
                    digest = _sync_and_fingerprint(file)
                    if name in self.files and self.files[name] != digest:
                        raise ValueError("Previously recorded work changed")
                    self.files[name] = digest
            data = self._data()
            _durable_marker(marker, data)
            self._marker_bytes = data
        except (OSError, ValueError):
            self.valid = False
            _LOG.info("work_cleanup=preserved")

    def cleanup(self, user_dir: Path) -> bool:
        self._lease.close()
        try:
            marker = self.path / MARKER
            current = not linked(marker) and marker.read_bytes() == self._marker_bytes
        except OSError:
            current = False
        if not self.valid or not current:
            _LOG.info("work_cleanup=preserved")
            return False
        return cleanup_owned(
            self.path, protected=protected_paths(user_dir), work_root=user_dir / "work"
        )


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
