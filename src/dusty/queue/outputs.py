"""Plan collision-safe names and atomically publish rendered outputs."""

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


def output_targets(job: Job, options: BatchOptions) -> list[Path]:
    """Plan all batch formats with one shared Keep both suffix."""
    folder = job.source.parent if options.same_folder else options.output_dir
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
            if linked(target.parent):
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
                        os.link(temporary, target)
                        temporary.unlink()
                published.append(target)
                identities[target] = hashlib.sha256(content).hexdigest()
            finally:
                temporary.unlink(missing_ok=True)
        return published
    except BaseException:
        if options.collision != "overwrite":
            for target in published:
                if not linked(target) and target.is_file():
                    with target.open("rb") as stream:
                        unchanged = (
                            hashlib.file_digest(stream, "sha256").hexdigest() == identities[target]
                        )
                    if unchanged:
                        target.unlink(missing_ok=True)
        raise
