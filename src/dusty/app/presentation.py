"""Small, platform-neutral presentation calculations for the Qt view."""

from dusty.core import Job, JobStatus

TERMINAL = {JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.SKIPPED}


def counts(jobs: list[Job]) -> dict[str, int]:
    return {
        name: sum(job.status.value == name for job in jobs)
        for name in ("done", "failed", "skipped", "cancelled")
    }


def overall_progress(jobs: list[Job]) -> float:
    return sum(1.0 if job.status in TERMINAL else job.progress for job in jobs) / max(1, len(jobs))


def eta_seconds(jobs: list[Job], elapsed: float) -> float | None:
    if (
        elapsed < 30
        or not jobs
        or any(job.duration_sec <= 0 for job in jobs if job.status not in TERMINAL)
    ):
        return None
    completed = sum(
        job.duration_sec * (1 if job.status in TERMINAL else job.progress) for job in jobs
    )
    remaining = sum(
        job.duration_sec * (1 - job.progress) for job in jobs if job.status not in TERMINAL
    )
    return remaining * elapsed / completed if completed > 0 else None
