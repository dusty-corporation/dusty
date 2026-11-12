"""Plan collision-safe names and atomically publish rendered outputs."""

import errno
import hashlib
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from dusty.core import BatchOptions, Job, Transcript
from dusty.export import render_docx, render_json, render_srt, render_txt, render_vtt
from dusty.export.formats import TextExtras, labels_for
from dusty.work_area import canonical, linked

RENDERERS = {
    "srt": render_srt,
    "vtt": render_vtt,
}


class OutputExistsError(Exception):
    """A collision requires a user decision or a skip."""


class OutputChangedError(Exception):
    """A file Dusty wrote was changed or removed since, so it is not replaced."""


class OutputInUseError(Exception):
    """A file Dusty wrote is open in another program and cannot be read or replaced."""


class PartialRewriteError(Exception):
    """Some files were replaced before one failed.

    ``updated`` holds the new identities of the files already replaced, so the
    caller can keep track of what each file now contains; ``in_use`` tells
    whether the failure was a file held open by another program.
    """

    def __init__(self, updated: dict[Path, str], *, in_use: bool):
        super().__init__("Only some outputs were rewritten")
        self.updated = updated
        self.in_use = in_use


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


def _render(fmt: str, job: Job, options: BatchOptions, transcript: Transcript) -> bytes:
    """One format, with the decorations of extensions that apply to this transcript."""
    from dusty import extensions

    decorations = extensions.active().decorations_for(transcript)
    labels = labels_for(transcript, decorations)
    if fmt == "json":
        return render_json(transcript, job.source, decorations=decorations)
    extras = TextExtras.choose(
        time_markers=options.time_markers,
        marker_minutes=options.marker_minutes,
        mark_unsure=options.mark_unsure,
        unsure_level=options.unsure_level,
    )
    if labels is not None:
        extras = replace(extras, labels=labels)
    if fmt == "docx":
        return render_docx(transcript, job.source, extras=extras)
    if fmt == "txt":
        return render_txt(transcript, extras)
    return RENDERERS[fmt](transcript, labels=labels)


def write_outputs(
    job: Job,
    options: BatchOptions,
    transcript: Transcript,
    *,
    identities: dict[Path, str] | None = None,
) -> list[Path]:
    """Render formats then publish each complete file without silent replacement.

    ``identities``, when given, receives the SHA-256 of each published file.
    """
    targets = output_targets(job, options)
    published: list[Path] = []
    written: dict[Path, str] = {}
    try:
        for fmt, target in zip(options.formats, targets, strict=True):
            if linked(target.parent, name_surrogates_only=True):
                raise OSError("Linked output folder")
            target.parent.mkdir(parents=True, exist_ok=True)
            content = _render(fmt, job, options, transcript)
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
                written[target] = hashlib.sha256(content).hexdigest()
            finally:
                temporary.unlink(missing_ok=True)
        if identities is not None:
            identities.update(written)
        return published
    except BaseException:
        if options.collision != "overwrite":
            for target in published:
                if not linked(target, name_surrogates_only=True) and target.is_file():
                    with target.open("rb") as stream:
                        unchanged = (
                            hashlib.file_digest(stream, "sha256").hexdigest() == written[target]
                        )
                    if unchanged:
                        target.unlink(missing_ok=True)
        raise


def rewrite_outputs(
    job: Job, options: BatchOptions, transcript: Transcript, identities: dict[Path, str]
) -> dict[Path, str]:
    """Render again into the files Dusty wrote for this job, for an extension action.

    Every file must still have exactly the bytes Dusty wrote (``identities``);
    otherwise nothing is replaced. All new contents are written to temporary
    files first, so a full disk or a render error replaces nothing. Each file is
    then replaced atomically; if one replacement fails, PartialRewriteError
    reports the files already replaced. Returns the new identities.
    """
    pairs = list(zip(options.formats, job.outputs, strict=True))
    for _fmt, target in pairs:
        if target not in identities or linked(target, name_surrogates_only=True):
            raise OutputChangedError("Output not written by Dusty in this session")
        try:
            with target.open("rb") as stream:
                current = hashlib.file_digest(stream, "sha256").hexdigest()
        except PermissionError as error:
            raise OutputInUseError("Output is open in another program") from error
        except OSError as error:
            raise OutputChangedError("Output missing") from error
        if current != identities[target]:
            raise OutputChangedError("Output changed since Dusty wrote it")
    staged: list[tuple[Path, Path, str]] = []
    try:
        for fmt, target in pairs:
            content = _render(fmt, job, options, transcript)
            descriptor, name = tempfile.mkstemp(suffix=".dusty-tmp", dir=target.parent)
            temporary = Path(name)
            staged.append((temporary, target, hashlib.sha256(content).hexdigest()))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        updated: dict[Path, str] = {}
        for temporary, target, digest in staged:
            try:
                os.replace(temporary, target)
            except OSError as error:
                raise PartialRewriteError(
                    updated, in_use=isinstance(error, PermissionError)
                ) from error
            updated[target] = digest
        return updated
    finally:
        for temporary, _target, _digest in staged:
            temporary.unlink(missing_ok=True)
