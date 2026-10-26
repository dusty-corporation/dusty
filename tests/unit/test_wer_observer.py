"""Real-store observation must fail closed when it cannot inspect an area."""

from pathlib import Path

import pytest

from tools.wer_observer import require_disposable_ci, snapshot


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"GITHUB_ACTIONS": "true"},
        {
            "GITHUB_ACTIONS": "true",
            "RUNNER_ENVIRONMENT": "self-hosted",
            "DUSTY_WER_ACCEPTANCE": "1",
        },
    ],
)
def test_deliberate_crash_guard_refuses_non_disposable_hosts(environment):
    with pytest.raises(RuntimeError):
        require_disposable_ci(environment)


def test_observer_detects_new_reports_and_does_not_ignore_denied_store(tmp_path, monkeypatch):
    roots = (tmp_path / "real-user", tmp_path / "real-machine")
    initial, states = snapshot(roots)
    assert not initial and len(states) == 6
    area = roots[0] / "ReportQueue" / "synthetic"
    area.mkdir(parents=True)
    report = area / "Report.wer"
    report.write_text("public test data")
    changed, states = snapshot(roots)
    assert report in changed and states["user/ReportQueue"] == "readable"
    original = __import__("os").scandir

    def denied(path):
        if Path(path) == roots[0] / "ReportQueue":
            raise PermissionError("cannot inspect")
        return original(path)

    monkeypatch.setattr("os.scandir", denied)
    with pytest.raises(PermissionError):
        snapshot(roots)
