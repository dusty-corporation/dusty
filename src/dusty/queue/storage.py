"""Schema-versioned atomic local batch storage and restart recovery."""

import json
import os
from dataclasses import asdict, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from dusty.core import BatchOptions, FailureCode, Job, JobStatus


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".dusty-tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path.rename(path.with_name(path.name + ".corrupt-" + suffix))
        return None


def _options_dict(options: BatchOptions) -> dict[str, object]:
    return {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(options).items()
    }


def save_batch(path: Path, options: BatchOptions, jobs: list[Job]) -> None:
    atomic_json(
        path,
        {
            "schema_version": 1,
            "options": _options_dict(options),
            "jobs": [
                {
                    "id": str(job.id),
                    "source": str(job.source),
                    "relative_dir": str(job.relative_dir) if job.relative_dir else None,
                    "status": job.status.value,
                    "failure": job.failure.value if job.failure else None,
                    "progress": job.progress,
                    "outputs": [str(output) for output in job.outputs],
                    "backend_used": job.backend_used,
                    "gpu_fallback": job.gpu_fallback,
                    "duration_sec": job.duration_sec,
                    "elapsed_sec": job.elapsed_sec,
                }
                for job in jobs
            ],
        },
    )


def load_batch(path: Path) -> tuple[BatchOptions, list[Job]] | None:
    data = _read(path)
    if data is None:
        return None
    try:
        if data["schema_version"] != 1:
            raise ValueError("Unknown queue schema")
        raw = data["options"]
        options = BatchOptions(
            model_id=raw["model_id"],
            output_dir=Path(raw["output_dir"]),
            formats=tuple(raw["formats"]),
            language=raw["language"],
            task=raw["task"],
            backend=raw["backend"],
            threads=raw["threads"],
            vad=raw["vad"],
            prompt=raw["prompt"],
            collision=raw["collision"],
            same_folder=raw["same_folder"],
            keep_structure=raw["keep_structure"],
        )
        jobs = []
        for item in data["jobs"]:
            job = Job(
                source=Path(item["source"]),
                id=UUID(item["id"]),
                relative_dir=Path(item["relative_dir"]) if item["relative_dir"] else None,
                status=JobStatus(item["status"]),
                failure=FailureCode(item["failure"]) if item["failure"] else None,
                progress=float(item["progress"]),
                outputs=[Path(value) for value in item["outputs"]],
                backend_used=item["backend_used"],
                gpu_fallback=bool(item["gpu_fallback"]),
                duration_sec=float(item.get("duration_sec", 0.0)),
                elapsed_sec=float(item.get("elapsed_sec", 0.0)),
            )
            if job.status not in {JobStatus.DONE, JobStatus.SKIPPED} or (
                job.status == JobStatus.DONE
                and (not job.outputs or not all(output.is_file() for output in job.outputs))
            ):
                job.status = JobStatus.QUEUED
                job.failure = None
                job.progress = 0.0
                job.elapsed_sec = 0.0
                job.outputs = []
            jobs.append(job)
        return options, jobs
    except (KeyError, TypeError, ValueError):
        suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path.rename(path.with_name(path.name + ".corrupt-" + suffix))
        return None


def clear_history(path: Path) -> None:
    path.unlink(missing_ok=True)


def load_settings(path: Path) -> dict[str, Any]:
    """Return defaults after quarantining malformed or unknown settings."""
    data = _read(path)
    if data is None:
        return {"schema_version": 1}
    try:
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unknown settings schema")
        _validate_settings(data)
        return data
    except (ValueError, TypeError):
        pass
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    path.rename(path.with_name(path.name + ".corrupt-" + suffix))
    return {"schema_version": 1}


def save_settings(path: Path, settings: dict[str, Any]) -> None:
    if settings.get("schema_version") != 1:
        raise ValueError("Unknown settings schema")
    _validate_settings(settings)
    atomic_json(path, settings)


def _validate_settings(settings: dict[str, Any]) -> None:
    """Validate persisted batch preferences; leave UI and probe fields intact."""
    names = {field.name for field in fields(BatchOptions)}
    preferences: dict[str, Any] = {"model_id": "tiny", "output_dir": Path(".")}
    preferences.update({key: value for key, value in settings.items() if key in names})
    if preferences["model_id"] is None:
        # A cleared GUI choice is valid storage, but never a runnable batch.
        preferences["model_id"] = "tiny"
    if "output_dir" in settings:
        if not isinstance(settings["output_dir"], str) or not settings["output_dir"]:
            raise ValueError("Invalid saved output directory")
        preferences["output_dir"] = Path(settings["output_dir"])
    if "formats" in settings:
        if not isinstance(settings["formats"], list):
            raise ValueError("Invalid saved formats")
        preferences["formats"] = tuple(settings["formats"])
    BatchOptions(**preferences)
