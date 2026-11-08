"""Private regular-file leases and a content-free, coalescing activation bit."""

import errno
import fcntl
import os
import stat
import sys
import time
from pathlib import Path

# macOS only. On Windows the fcntl import above already fails; this check also
# tells type checkers on Windows that the rest of the module is macOS only.
if sys.platform == "win32":
    raise ImportError("dusty.platform.mac_instance is macOS only")

_DIRECTORY = ".gui-instance"
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
_CONTENTION_SECONDS = 0.5


def _private_directory(fd: int) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise OSError("Unsafe instance directory")


def _open_profile(path: Path, *, create: bool = True) -> int:
    """Walk pinned directory handles; never traverse a symlink while creating parents."""
    if not path.is_absolute() or ".." in path.parts or path == Path("/"):
        raise OSError("Invalid instance directory")
    current = os.open("/", _DIRECTORY_FLAGS)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
            following = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = following
        _private_directory(current)
        return current
    except BaseException:
        os.close(current)
        raise


def _open_control(directory: int, name: str) -> int:
    """Separate creation from opening an existing control during concurrent startup."""
    deadline = time.monotonic() + _CONTENTION_SECONDS
    while True:
        try:
            try:
                return os.open(name, _FILE_FLAGS | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
            except FileExistsError:
                return os.open(name, _FILE_FLAGS, dir_fd=directory)
        except FileNotFoundError:
            if time.monotonic() >= deadline:
                raise OSError("Instance control creation did not settle") from None
            time.sleep(0.005)


class GuiInstance:
    """Ownership is held by flock, not a stale PID; control files are never unlinked."""

    def __init__(self, user_dir: Path):
        self.owner = False
        self._path = user_dir
        self._root: int | None = None
        self._directory: int | None = None
        self._ownership: int | None = None
        self._event: int | None = None
        try:
            self._root = _open_profile(user_dir)
            try:
                os.mkdir(_DIRECTORY, mode=0o700, dir_fd=self._root)
            except FileExistsError:
                pass
            self._directory = os.open(_DIRECTORY, _DIRECTORY_FLAGS, dir_fd=self._root)
            _private_directory(self._directory)
            self._ownership = _open_control(self._directory, "owner")
            self._event = _open_control(self._directory, "activation")
            self._validate()
            self._lock_event(wait=True)
            try:
                self._validate()
                self._read_event()
                try:
                    fcntl.flock(self._ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.owner = True
                except BlockingIOError:
                    self.owner = False
                # Clear stale state only after ownership wins, within the same
                # transaction that duplicates use to request activation.
                self._write_event(b"0" if self.owner else b"1")
                self._validate()
            finally:
                fcntl.flock(self._event, fcntl.LOCK_UN)
        except (OSError, ValueError):
            self.close()
            raise OSError("GUI instance control state is unavailable or unsafe") from None
        except BaseException:
            self.close()
            raise

    def _validate(self) -> None:
        assert self._root is not None and self._directory is not None
        # An open directory FD remains valid after its pathname was moved or
        # replaced. Re-open without creation to detect that namespace change.
        current_root = _open_profile(self._path, create=False)
        try:
            named_root = os.fstat(current_root)
            held_root = os.fstat(self._root)
            if (named_root.st_dev, named_root.st_ino) != (held_root.st_dev, held_root.st_ino):
                raise OSError("Instance profile identity changed")
        finally:
            os.close(current_root)
        _private_directory(self._root)
        _private_directory(self._directory)
        current = os.stat(_DIRECTORY, dir_fd=self._root, follow_symlinks=False)
        held = os.fstat(self._directory)
        if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
            raise OSError("Instance directory identity changed")
        for name, fd in (("owner", self._ownership), ("activation", self._event)):
            assert fd is not None
            held = os.fstat(fd)
            named = os.stat(name, dir_fd=self._directory, follow_symlinks=False)
            if (
                not stat.S_ISREG(held.st_mode)
                or held.st_uid != os.getuid()
                or held.st_mode & 0o077
                or held.st_nlink != 1
                or (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino)
                or held.st_size > (0 if name == "owner" else 1)
            ):
                raise OSError("Unsafe instance control file")

    def _lock_event(self, *, wait: bool) -> bool:
        assert self._event is not None
        deadline = time.monotonic() + _CONTENTION_SECONDS
        while True:
            try:
                fcntl.flock(self._event, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except OSError as error:
                if error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                    raise
                if not wait:
                    return False
                if time.monotonic() >= deadline:
                    raise OSError("Instance activation is busy") from None
                time.sleep(0.005)

    def _read_event(self) -> bytes:
        assert self._event is not None
        value = os.pread(self._event, 2, 0)
        if value not in (b"", b"0", b"1"):
            raise OSError("Unknown instance activation state")
        return value

    def _write_event(self, value: bytes) -> None:
        assert self._event is not None
        if os.pwrite(self._event, value, 0) != 1:
            raise OSError("Instance activation write failed")

    def activation_requested(self) -> bool:
        if not self.owner or self._event is None:
            return False
        try:
            self._validate()
            if not self._lock_event(wait=False):
                return False
            try:
                self._validate()
                requested = self._read_event() == b"1"
                if requested:
                    self._write_event(b"0")
                return requested
            finally:
                fcntl.flock(self._event, fcntl.LOCK_UN)
        except (OSError, ValueError):
            raise OSError("GUI instance control state is unavailable or unsafe") from None

    def close(self) -> None:
        for name in ("_event", "_ownership", "_directory", "_root"):
            descriptor = getattr(self, name, None)
            if descriptor is not None:
                setattr(self, name, None)
                try:
                    os.close(descriptor)
                except OSError:
                    # Continue closing the ownership lease even if another
                    # descriptor was already closed or reported a close error.
                    pass
