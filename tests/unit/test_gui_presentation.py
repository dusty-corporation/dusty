"""ETA uses measured successful work and avoids estimating before 30 seconds."""

from pathlib import Path

from dusty.app.presentation import counts, eta_seconds, overall_progress
from dusty.core import Job, JobStatus


def test_eta_waits_then_uses_measured_audio_progress() -> None:
    jobs = [
        Job(Path("one.wav"), duration_sec=60, status=JobStatus.DONE, progress=1),
        Job(Path("two.wav"), duration_sec=60),
    ]
    assert eta_seconds(jobs, 29) is None
    assert eta_seconds(jobs, 60) == 60
    jobs.append(Job(Path("bad.wav"), duration_sec=600, status=JobStatus.FAILED))
    assert eta_seconds(jobs, 60) == 60
    assert counts(jobs)["failed"] == 1
    assert abs(overall_progress(jobs) - 2 / 3) < 0.001
    jobs[1].duration_sec = 0
    assert eta_seconds(jobs, 60) is None
