"""Check the platform-neutral runner contract and its per-platform dispatch."""

import ast
import dataclasses
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.platform import process

ROOT = Path(__file__).resolve().parents[2]


def stub_runner(monkeypatch: pytest.MonkeyPatch, module_name: str) -> list[tuple[object, dict]]:
    calls: list[tuple[object, dict]] = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return "stub result"

    monkeypatch.setitem(sys.modules, module_name, SimpleNamespace(run_job_process=run))
    return calls


def test_unknown_platform_is_refused() -> None:
    with pytest.raises(OSError, match="^Native process runner unavailable on this platform$"):
        process.platform_runner("linux")


@pytest.mark.parametrize(
    ("platform", "module_name"),
    [("win32", "dusty.platform.win_process"), ("darwin", "dusty.platform.mac_process")],
)
def test_each_platform_loads_only_its_runner(
    monkeypatch: pytest.MonkeyPatch, platform: str, module_name: str
) -> None:
    stub_runner(monkeypatch, module_name)
    runner = process.platform_runner(platform)
    assert runner([]) == "stub result"


def test_run_job_process_forwards_every_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, dict]] = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return "forwarded"

    monkeypatch.setattr(process, "platform_runner", lambda: runner)
    arguments = ["absolute executable", "argument with spaces"]
    parameters = dict(
        cwd=Path("folder"),
        on_stderr=lambda _: None,
        on_stdout=lambda _: None,
        cancel=threading.Event(),
        timeout_sec=3.5,
        on_poll=lambda: None,
        environment={"LC_ALL": "C"},
    )
    assert process.run_job_process(arguments, **parameters) == "forwarded"
    assert calls == [(arguments, parameters)]


@pytest.mark.parametrize("name", ["ffmpeg", "whisper"])
@pytest.mark.parametrize(
    ("platform", "module_name"),
    [("win32", "dusty.platform.win_process"), ("darwin", "dusty.platform.mac_process")],
)
def test_engine_shims_dispatch_by_their_platform(
    monkeypatch: pytest.MonkeyPatch, name: str, platform: str, module_name: str
) -> None:
    from dusty.engine import ffmpeg, whisper

    module = ffmpeg if name == "ffmpeg" else whisper
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform=platform))
    calls = stub_runner(monkeypatch, module_name)
    assert module.run_job_process(["executable"], timeout_sec=1.0) == "stub result"
    assert calls == [
        (
            ["executable"],
            dict(
                cwd=None,
                on_stderr=None,
                on_stdout=None,
                cancel=None,
                timeout_sec=1.0,
                on_poll=None,
            ),
        )
    ]


@pytest.mark.parametrize("name", ["ffmpeg", "whisper"])
def test_engine_shims_refuse_other_platforms(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    from dusty.engine import ffmpeg, whisper

    module = ffmpeg if name == "ffmpeg" else whisper
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(OSError, match="^Native process runner unavailable on this platform$"):
        module.run_job_process(["CANARY_SOURCE"])


def test_windows_runner_reuses_the_shared_definitions() -> None:
    tree = ast.parse((ROOT / "src/dusty/platform/win_process.py").read_text(encoding="utf-8"))
    defined = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "dusty.platform.process"
        for alias in node.names
    }
    shared = {"ProcessResult", "approved_executable", "_read_lines"}
    assert shared <= imported
    assert not shared & defined


def test_process_result_is_frozen() -> None:
    result = process.ProcessResult(0, 1.5, False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.exit_code = 1  # type: ignore[misc]


def test_line_reader_splits_on_both_newlines_and_bounds_partial_lines() -> None:
    read_fd, write_fd = os.pipe()
    lines: list[str] = []
    reader = threading.Thread(target=process._read_lines, args=(read_fd, lines.append))
    reader.start()
    with os.fdopen(write_fd, "wb") as stream:
        stream.write(b"first\r\nsecond\rthird\n")
        stream.write(b"x" * 200_000 + b"\nlast without newline")
    reader.join(timeout=10)
    assert not reader.is_alive()
    assert lines[:3] == ["first", "second", "third"]
    assert lines[4] == "last without newline" and len(lines) == 5
    assert set(lines[3]) == {"x"} and len(lines[3]) <= 65536 + 4096
