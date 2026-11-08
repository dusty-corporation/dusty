"""Plan collision-safe names and atomically publish rendered outputs."""

import errno
import hashlib
import os
import tempfile
from pathlib import Path

from dusty.core import BatchOptions, Job, Transcript
from dusty.export import render_docx, render_json, render_srt, render_txt, render_vtt
from dusty.work_area import canonical, linked

RENDERERS = {
    "txt": render_txt,
    "srt": render_srt,
    "vtt": render_vtt,
}


class OutputExistsError(Exception):
    """A collision requires a user decision or a skip."""


# FAT32 and exFAT volumes have no hard links: macOS reports ENOTSUP and Linux
# vfat reports EPERM. These volumes publish through an exclusive reservation.
_NO_HARD_LINKS = frozenset({errno.ENOTSUP, errno.EOPNOTSUPP, errno.EPERM})


def _publish_exclusive(temporary: Path, target: Path) -> None:
    """Give a complete POSIX file its final name without replacing any file."""
    try:
        os.link(temporary, target)
    except OSError as error:
        if error.errno not in _NO_HARD_LINKS:
            raise
    else:
        temporary.unlink()
        return
    # O_EXCL claims the free name, so a file that already exists is never
    # replaced. The rename then swaps only that empty reservation for the
    # complete file in one step, as the hard link does on other volumes.
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        reserved = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.rename(temporary, target)
    except BaseException:
        try:
            current = os.lstat(target)
            if (current.st_dev, current.st_ino, current.st_size) == (
                reserved.st_dev,
                reserved.st_ino,
                0,
            ):
                os.unlink(target)
        except OSError:
            pass
        raise


def output_targets(job: Job, options: BatchOptions) -> list[Path]:
    """Plan all batch formats with one shared Keep both suffix."""
    folder = job.source.parent if options.same_folder else options.output_dir
    if folder is None:
        raise ValueError("Output directory required")
    if options.keep_structure and job.relative_dir and not options.same_folder:
        if job.relative_dir.root or job.relative_dir.drive or ".." in job.relative_dir.parts:
            raise ValueError("Invalid relative output directory")
        folder /= job.relative_dir
    suffix = ".en" if options.task == "translate" else ""

    def candidate(number: int) -> list[Path]:
        postfix = f" ({number})" if number else ""
        return [folder / f"{job.source.stem}{postfix}{suffix}.{fmt}" for fmt in options.formats]

    targets = candidate(0)
    if options.collision == "keep_both":
        number = 0
        while any(path.exists() for path in targets):
            number += 1
            targets = candidate(number)
    elif options.collision != "overwrite" and any(path.exists() for path in targets):
        raise OutputExistsError("Output exists")
    if any(canonical(path) == canonical(job.source) for path in targets):
        raise OutputExistsError("Output would replace source")
    return targets


def write_outputs(job: Job, options: BatchOptions, transcript: Transcript) -> list[Path]:
    """Render formats then publish each complete file without silent replacement."""
    targets = output_targets(job, options)
    published: list[Path] = []
    identities: dict[Path, str] = {}
    try:
        for fmt, target in zip(options.formats, targets, strict=True):
            if linked(target.parent, name_surrogates_only=True):
                raise OSError("Linked output folder")
            target.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "json":
                content = render_json(transcript, job.source)
            elif fmt == "docx":
                content = render_docx(transcript, job.source)
            else:
                content = RENDERERS[fmt](transcript)
            descriptor, name = tempfile.mkstemp(suffix=".dusty-tmp", dir=target.parent)
            temporary = Path(name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if options.collision == "overwrite":
                    os.replace(temporary, target)
                else:
                    if os.name == "nt":
                        os.rename(temporary, target)
                    else:
                        _publish_exclusive(temporary, target)
                published.append(target)
                identities[target] = hashlib.sha256(content).hexdigest()
            finally:
                temporary.unlink(missing_ok=True)
        return published
    except BaseException:
        if options.collision != "overwrite":
            for target in published:
                if not linked(target, name_surrogates_only=True) and target.is_file():
                    with target.open("rb") as stream:
                        unchanged = (
                            hashlib.file_digest(stream, "sha256").hexdigest() == identities[target]
                        )
                    if unchanged:
                        target.unlink(missing_ok=True)
        raise
