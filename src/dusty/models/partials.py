"""Age out abandoned model download prefixes without following links."""

import hashlib
import json
import stat
import time
from pathlib import Path

from dusty.work_area import linked, protected_paths

PARTIAL_MAX_AGE_SEC = 7 * 24 * 60 * 60


def cleanup_stale_partials(directory: Path, *, now: float | None = None) -> int:
    """Remove regular .part files older than seven days, directly in the model folder.

    A locked/removed file is left alone; cleanup is retried at the next startup.
    Recent prefixes remain eligible for the downloader's full size/hash checks.
    """
    cutoff = (time.time() if now is None else now) - PARTIAL_MAX_AGE_SEC
    removed = 0
    try:
        protected = protected_paths(directory.parent)
        if (
            linked(directory)
            or protected is None
            or any(
                p.is_relative_to(directory.resolve()) or directory.resolve().is_relative_to(p)
                for p in protected
            )
        ):
            return 0
        entries = list(directory.iterdir())
    except OSError:
        return 0
    for path in entries:
        if not path.name.lower().endswith(".part"):
            continue
        try:
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or info.st_mtime >= cutoff
            ):
                continue
            receipt = path.with_name(path.name.removesuffix(".part") + ".lock")
            if linked(receipt):
                continue
            try:
                data = json.loads(receipt.read_bytes()[1:])
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if data != {
                    "schema": 1,
                    "purpose": "model-download",
                    "file": path.name,
                    "sha256": digest,
                }:
                    continue
            except (OSError, ValueError):
                continue
            path.unlink()
            removed += 1
        except OSError:
            # Never turn a busy prefix into an app-startup failure or log its name.
            continue
    return removed
