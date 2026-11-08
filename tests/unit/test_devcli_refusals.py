"""devcli refuses model and option combinations with a code, not a traceback."""

from pathlib import Path

import pytest

from dusty import devcli
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    seen: dict[str, list] = {"probe": [], "batch": []}
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    monkeypatch.setattr(devcli, "resolve_paths", lambda: paths)
    monkeypatch.setattr(devcli, "probe_vulkan", lambda *a: seen["probe"].append(a) or False)

    class Coordinator:
        def __init__(self, *args):
            pass

        def run_batch(self, jobs, options, **kwargs):
            seen["batch"].append(options)
            return jobs

    monkeypatch.setattr(devcli, "Coordinator", Coordinator)
    source = tmp_path / "in/clip.wav"
    source.parent.mkdir()
    source.write_bytes(b"RIFF public fixture stand-in")
    seen["argv"] = ["transcribe", str(source), "--out", str(tmp_path / "out"), "--format", "txt"]
    return seen


@pytest.mark.parametrize(
    ("flags", "code"),
    [
        (["--model", "small.en", "--language", "fa"], "LANGUAGE_UNSUPPORTED"),
        (["--model", "small.en", "--language", "de", "--backend", "cpu"], "LANGUAGE_UNSUPPORTED"),
        (["--model", "small.en", "--task", "translate"], "TRANSLATE_UNSUPPORTED"),
        (
            ["--model", "large-v3-turbo-q8_0", "--language", "fa", "--task", "translate"],
            "TRANSLATE_UNSUPPORTED",
        ),
    ],
)
def test_unsupported_choice_prints_a_code_before_any_probe_or_job(cli, capsys, flags, code):
    assert devcli.main([*cli["argv"], *flags]) == 2
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines()[-1] == code
    assert "Traceback" not in captured.out + captured.err
    assert cli["probe"] == [] and cli["batch"] == []


@pytest.mark.parametrize(
    ("model", "language"), [("small.en", "auto"), ("small.en", "en"), ("small", "fa")]
)
def test_supported_language_choices_reach_the_coordinator(cli, capsys, model, language):
    devcli.main([*cli["argv"], "--model", model, "--language", language])
    assert "UNSUPPORTED" not in capsys.readouterr().out
    assert [options.language for options in cli["batch"]] == [language]
    assert len(cli["probe"]) == 1
