"""Check live job guards, not a separate unused model of workflow behavior."""

import shutil

import pytest

from tools.check_workflow_budget import ROOT, check, condition, enabled, jobs


def test_all_live_workflows_have_visibility_guards():
    assert check() == []


@pytest.mark.parametrize("private", [True, False])
@pytest.mark.parametrize("event", ["push", "pull_request", "workflow_dispatch"])
def test_ci_visibility_truth_table(private, event):
    actual = jobs((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    running = {name for name, body in actual.items() if enabled(condition(body), private, event)}
    heavy = {"checks", "offline", "installer-upload-regression", "packaging-spike"}
    assert running == ({"source"} if private and event != "workflow_dispatch" else heavy)


@pytest.mark.parametrize("event", ["push", "workflow_dispatch"])
def test_private_release_has_no_runnable_job_even_for_a_tag(event):
    actual = jobs((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    assert not any(enabled(condition(body), True, event) for body in actual.values())
    assert all(enabled(condition(body), False, event) for body in actual.values())


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_every_automatic_private_workflow_has_only_the_source_job(event):
    for file in (ROOT / ".github/workflows").glob("*.yml"):
        actual = jobs(file.read_text(encoding="utf-8"))
        running = {name for name, body in actual.items() if enabled(condition(body), True, event)}
        assert running == ({"source"} if file.name == "ci.yml" else set()), file.name


def test_full_private_dispatch_is_available_except_release_creation():
    for file in (ROOT / ".github/workflows").glob("*.yml"):
        actual = jobs(file.read_text(encoding="utf-8"))
        running = {
            name
            for name, body in actual.items()
            if enabled(condition(body), True, "workflow_dispatch")
        }
        expected = set() if file.name == "release.yml" else set(actual) - {"source"}
        assert running == expected, file.name


@pytest.mark.parametrize("damage", ["missing", "upload", "release", "name"])
def test_visibility_policy_rejects_budget_bypasses(tmp_path, damage):
    shutil.copytree(ROOT / ".github/workflows", tmp_path / ".github/workflows")
    file = tmp_path / ".github/workflows/ci.yml"
    text = file.read_text(encoding="utf-8")
    if damage == "missing":
        text = text.replace("    if:", "    removed:", 1)
    elif damage == "upload":
        text = text.replace("  source:\n", "  source:\n    # upload-artifact\n", 1)
    elif damage == "name":
        text = text.replace("github.event.repository.private == true", "github.repository == 'x/y'")
    else:
        file = tmp_path / ".github/workflows/release.yml"
        text = file.read_text(encoding="utf-8").replace("    if:", "    removed:", 1)
    file.write_text(text, encoding="utf-8")
    assert check(tmp_path)
