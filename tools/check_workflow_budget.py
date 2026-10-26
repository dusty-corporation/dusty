"""Fail closed if automatic private workflows can run expensive jobs or uploads."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL = "github.event.repository.private == false || github.event_name == 'workflow_dispatch'"
PUBLIC_ONLY = "github.event.repository.private == false"
CHEAP = (
    "github.event.repository.private == true && "
    "(github.event_name == 'push' || github.event_name == 'pull_request')"
)


def jobs(text: str) -> dict[str, str]:
    section = text.split("\njobs:\n", 1)[1]
    return dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)", section, re.M | re.S))


def condition(job: str) -> str:
    match = re.search(r"^    if: (.+)$", job, re.M)
    return match[1] if match else ""


def enabled(expression: str, private: bool, event: str) -> bool:
    """Only the three approved expressions are accepted, no arbitrary evaluator."""
    if expression == FULL:
        return not private or event == "workflow_dispatch"
    if expression == PUBLIC_ONLY:
        return not private
    if expression == CHEAP:
        return private and event in {"push", "pull_request"}
    raise ValueError("Unapproved workflow visibility condition")


def check(root: Path = ROOT) -> list[str]:
    findings = []
    directory = root / ".github/workflows"
    expected = {
        "ci.yml": {
            "source": CHEAP,
            **dict.fromkeys(
                ("checks", "offline", "installer-upload-regression", "packaging-spike"), FULL
            ),
        },
        "release.yml": dict.fromkeys(("validate", "gates", "draft"), PUBLIC_ONLY),
        "native.yml": {"whisper": FULL},
        "ffmpeg.yml": {"ffmpeg": FULL},
        "models.yml": dict.fromkeys(("prepare", "convert", "manifest"), FULL),
    }
    actual_files = {p.name for p in directory.glob("*.yml")} | {
        p.name for p in directory.glob("*.yaml")
    }
    # Additional workflows may run only as public/manual heavy work. The
    # exported tree need not contain any private-only rehearsal workflow.
    for name in actual_files - set(expected):
        actual = jobs((directory / name).read_text(encoding="utf-8"))
        if not actual or any(condition(body) != FULL for body in actual.values()):
            findings.append(f"Additional workflow lacks public/manual guards: {name}")
    for name, allowed in expected.items():
        file = directory / name
        if not file.exists():
            findings.append(f"Missing workflow: {name}")
            continue
        text = file.read_text(encoding="utf-8")
        actual = jobs(text)
        if set(actual) != set(allowed):
            findings.append(f"Unexpected job set: {name}")
        for job, expression in allowed.items():
            if condition(actual.get(job, "")) != expression:
                findings.append(f"Visibility guard mismatch: {name}/{job}")
        if name == "ci.yml":
            source = actual.get("source", "")
            for forbidden in (
                "upload-artifact",
                "actions/cache",
                "fetch_dev_binaries",
                "measure_coverage",
                "build_bundle",
                "build_installer",
                "test_installer.ps1",
                "test_network_isolation",
                "test_model_download_isolation",
                "capture_review_pages",
                "DUSTY_WER_ACCEPTANCE",
            ):
                if forbidden in source:
                    findings.append(f"Private automatic source job contains {forbidden}")
            if "pytest -q tests --ignore=tests/integration" not in source:
                findings.append("Private automatic source job lacks unit tests")
    return findings


if __name__ == "__main__":
    errors = check()
    print("\n".join(errors) if errors else "Workflow visibility/budget policy passed")
    raise SystemExit(bool(errors))
