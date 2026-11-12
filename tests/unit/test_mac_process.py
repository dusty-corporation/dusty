"""Exercise the macOS runner and the dusty-lifeline helper with real processes.

These tests build the helper with native/macos/build_lifeline.sh and a tiny C
test program into a temporary bin_dir. Copies of Apple system programs cannot
be used as targets because macOS launch constraints kill relocated copies.
"""

import os
import shutil
import signal
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

if sys.platform != "darwin":
    pytest.skip("The lifeline runner exists only on macOS", allow_module_level=True)
if shutil.which("xcrun") is None:
    pytest.skip("Building the lifeline needs the Xcode command line tools", allow_module_level=True)

from dusty.platform import mac_process  # noqa: E402
from dusty.platform.process import ProcessResult, run_job_process  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CANCELLED = 125

PROGRAM = r"""
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void wait_forever(void) {
    for (;;) {
        pause();
    }
}

int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    if (strcmp(mode, "echo") == 0) {
        printf("out one\nout two\n");
        fflush(stdout);
        fprintf(stderr, "err one\rerr two\n");
        return argc > 2 ? atoi(argv[2]) : 0;
    }
    if (strcmp(mode, "signal") == 0) {
        kill(getpid(), SIGTERM);
        return 1;
    }
    if (strcmp(mode, "tree") == 0) {
        pid_t grandchild = fork();
        if (grandchild == 0) {
            wait_forever();
        }
        printf("target %d %d %d\n", getpid(), getpgrp(), getppid());
        printf("grandchild %d %d\n", grandchild, getpgid(grandchild));
        fflush(stdout);
        signal(SIGTERM, SIG_IGN);
        wait_forever();
    }
    if (strcmp(mode, "fds") == 0) {
        for (int fd = 0; fd < 4096; fd++) {
            if (fcntl(fd, F_GETFD) != -1) {
                printf("%d\n", fd);
            }
        }
        return 0;
    }
    if (strcmp(mode, "env") == 0) {
        for (char **item = environ; *item; item++) {
            printf("%s\n", *item);
        }
        return 0;
    }
    if (strcmp(mode, "cwd") == 0) {
        char buffer[4096];
        printf("%s\n", getcwd(buffer, sizeof buffer));
        return 0;
    }
    if (strcmp(mode, "sleep") == 0) {
        wait_forever();
    }
    if (strcmp(mode, "-m") == 0 && argc > 2) {
        /* A whisper-cli stand-in: the model file name picks what the engine
           reports, and then it stalls the way a hung GPU does. */
        if (strstr(argv[2], "virtual-gpu")) {
            fprintf(stderr, "ggml_metal_device_init: GPU name:   "
                            "MTL0 (Apple Paravirtual device)\n");
            fprintf(stderr, "ggml_metal_device_init: simdgroup reduction   = false\n");
            fprintf(stderr, "ggml_metal_device_init: simdgroup matrix mul. = false\n");
        } else if (strstr(argv[2], "failed-command")) {
            fprintf(stderr, "whisper_backend_init_gpu: using MTL0 backend\n");
            fprintf(stderr, "ggml_metal_synchronize: error: "
                            "command buffer 0 failed with status 5\n");
        }
        fflush(stderr);
        wait_forever();
    }
    return 2;
}
"""


@pytest.fixture(scope="session")
def built_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    bin_dir = tmp_path_factory.mktemp("mac-runner").resolve() / "bin"
    subprocess.run(
        ["/bin/bash", str(ROOT / "native/macos/build_lifeline.sh"), str(bin_dir)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    sums = (bin_dir / "SHA256SUMS").read_text(encoding="utf-8")
    assert sums.strip().endswith("  lifeline/dusty-lifeline")
    source = bin_dir.parent / "program.c"
    source.write_text(PROGRAM, encoding="utf-8")
    (bin_dir / "tools").mkdir()
    subprocess.run(
        ["xcrun", "clang", "-O1", "-o", str(bin_dir / "tools/program"), str(source)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return bin_dir


@pytest.fixture
def bin_dir(built_bin: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DUSTY_BIN_DIR", str(built_bin))
    return built_bin


@pytest.fixture
def program(bin_dir: Path) -> str:
    return str(bin_dir / "tools/program")


def run_lines(args: list[str], **kwargs: object) -> tuple[ProcessResult, list[str], list[str]]:
    stdout: list[str] = []
    stderr: list[str] = []
    result = run_job_process(args, on_stdout=stdout.append, on_stderr=stderr.append, **kwargs)
    return result, stdout, stderr


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_gone(pids: list[int], seconds: float = 3.0) -> list[int]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        remaining = [pid for pid in pids if alive(pid)]
        if not remaining:
            return []
        time.sleep(0.02)
    return [pid for pid in pids if alive(pid)]


def child_python(script: str, bin_dir: Path, **kwargs: object) -> subprocess.Popen[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["DUSTY_BIN_DIR"] = str(bin_dir)
    return subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=ROOT,
        env=environment,
        text=True,
        **kwargs,
    )


def test_success_reports_exit_code_and_parses_lines(program: str) -> None:
    result, stdout, stderr = run_lines([program, "echo", "0"])
    assert result.exit_code == 0 and not result.cancelled
    assert 0 <= result.elapsed_sec < 5
    assert stdout == ["out one", "out two"]
    assert stderr == ["err one", "err two"]


def test_stdout_without_callback_is_discarded(program: str) -> None:
    stderr: list[str] = []
    result = run_job_process([program, "echo", "0"], on_stderr=stderr.append)
    assert result == ProcessResult(0, result.elapsed_sec, False)
    assert stderr == ["err one", "err two"]


def test_nonzero_exit_code_is_reported(program: str) -> None:
    result, _, _ = run_lines([program, "echo", "7"])
    assert result.exit_code == 7 and not result.cancelled


def test_signal_exit_is_reported_as_shell_style_code(program: str) -> None:
    result, _, _ = run_lines([program, "signal"])
    assert result.exit_code == 128 + signal.SIGTERM and not result.cancelled


def test_cancel_kills_target_and_grandchild_in_their_own_group(program: str) -> None:
    lines: list[str] = []
    cancel = threading.Event()
    groups: list[tuple[int, int]] = []

    def poll() -> None:
        if len(lines) == 2 and not cancel.is_set():
            helper = int(lines[0].split()[3])
            groups.append((helper, os.getpgid(helper)))
            cancel.set()

    result = run_job_process(
        [program, "tree"], on_stdout=lines.append, cancel=cancel, on_poll=poll, timeout_sec=10
    )
    assert result.cancelled and result.exit_code == CANCELLED
    target, target_group, helper = (int(item) for item in lines[0].split()[1:])
    grandchild, grandchild_group = (int(item) for item in lines[1].split()[1:])
    assert target_group == target == grandchild_group
    assert groups == [(helper, helper)]
    assert helper != os.getpgrp() and target != helper
    assert wait_gone([target, grandchild, helper]) == []


def test_timeout_cancels_quickly(program: str) -> None:
    result, _, _ = run_lines([program, "sleep"], timeout_sec=0.3)
    assert result.cancelled and result.exit_code == CANCELLED
    assert result.elapsed_sec < 2


@pytest.mark.parametrize("report", ["virtual-gpu", "failed-command"])
def test_stalled_metal_run_is_stopped_once_its_stderr_shows_it_cannot_work(
    program: str, tmp_path: Path, report: str
) -> None:
    """On a GPU the engine cannot use, or after a failed Metal command, it stops at once.

    The stand-in never exits by itself, like the engine on a stalled GPU, so this
    finishes only because Dusty stops it through the lifeline.
    """
    from dusty.engine.whisper import EngineError, run_whisper

    started = time.monotonic()
    with pytest.raises(EngineError) as raised:
        run_whisper(
            Path(program),
            tmp_path / f"{report}.bin",
            tmp_path / "audio.wav",
            tmp_path / "raw",
            model_id="tiny",
            task="transcribe",
            language="en",
            threads=1,
            duration_sec=1.0,
            backend="metal",
            vad_model=None,
            prompt="",
        )
    assert time.monotonic() - started < 5
    error = raised.value
    assert error.gpu_error and not error.cancelled
    assert error.unsupported_gpu == (report == "virtual-gpu")


def test_cancel_before_start_still_runs_one_poll(program: str) -> None:
    cancel = threading.Event()
    cancel.set()
    polls: list[int] = []
    result = run_job_process(
        [program, "sleep"], cancel=cancel, on_poll=lambda: polls.append(1), timeout_sec=10
    )
    assert result.cancelled and result.exit_code == CANCELLED
    assert len(polls) >= 2


def test_error_in_poll_callback_still_kills_the_group(program: str) -> None:
    lines: list[str] = []

    def poll() -> None:
        if len(lines) == 2:
            raise RuntimeError("caller failure")

    with pytest.raises(RuntimeError, match="caller failure"):
        run_job_process([program, "tree"], on_stdout=lines.append, on_poll=poll, timeout_sec=10)
    target = int(lines[0].split()[1])
    grandchild = int(lines[1].split()[1])
    helper = int(lines[0].split()[3])
    assert wait_gone([target, grandchild, helper]) == []


def test_parent_sigkill_kills_target_and_grandchild(bin_dir: Path, program: str) -> None:
    parent = child_python(
        f"""
        from dusty.privacy.network_guard import install_guard
        install_guard()
        from dusty.platform.process import run_job_process
        run_job_process([{program!r}, "tree"], on_stdout=lambda line: print(line, flush=True))
        print("returned", flush=True)
        """,
        bin_dir,
        stdout=subprocess.PIPE,
    )
    try:
        assert parent.stdout is not None
        target_line = parent.stdout.readline().split()
        grandchild_line = parent.stdout.readline().split()
        assert target_line[0] == "target" and grandchild_line[0] == "grandchild"
        pids = [int(target_line[1]), int(grandchild_line[1]), int(target_line[3])]
        assert all(alive(pid) for pid in pids)
        parent.send_signal(signal.SIGKILL)
        parent.wait(timeout=5)
        assert wait_gone(pids) == []
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if parent.stdout:
            parent.stdout.close()


def test_guard_blocks_python_spawning_but_not_the_runner(bin_dir: Path, program: str) -> None:
    script = f"""
        import os, subprocess, sys
        from dusty.privacy.network_guard import NetworkBlockedError, install_guard
        install_guard()
        for attempt in (
            lambda: subprocess.Popen([{program!r}, "echo"]),
            lambda: os.posix_spawn({program!r}, [{program!r}, "echo"], {{}}),
        ):
            try:
                attempt()
            except NetworkBlockedError:
                pass
            else:
                raise AssertionError("spawn allowed")
        from dusty.platform.process import run_job_process
        lines = []
        result = run_job_process([{program!r}, "echo", "4"], on_stdout=lines.append)
        assert (result.exit_code, result.cancelled, lines) == (4, False, ["out one", "out two"])
        print("guarded runner ok")
        """
    parent = child_python(script, bin_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = parent.communicate(timeout=20)
    assert parent.returncode == 0, stderr
    assert stdout.strip() == "guarded runner ok"


def test_no_descriptors_leak_into_target(program: str) -> None:
    leaked = os.open(os.devnull, os.O_RDONLY)
    os.set_inheritable(leaked, True)
    try:
        result, stdout, _ = run_lines([program, "fds"])
    finally:
        os.close(leaked)
    assert result.exit_code == 0
    assert stdout == ["0", "1", "2"]


def test_target_gets_minimal_environment(program: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUSTY_TEST_CANARY", "must not reach the target")
    for name in ("HOME", "TMPDIR", "PYTHONPATH", "SSL_CERT_FILE", "https_proxy"):
        monkeypatch.setenv(name, "must not reach the target")
    result, stdout, _ = run_lines([program, "env"])
    assert result.exit_code == 0
    assert stdout == ["LC_ALL=C"]


def test_an_explicit_environment_replaces_the_runners_choice(
    program: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        mac_process, "child_environment", lambda executable: {"LC_ALL": "C", "CHOSEN": "no"}
    )
    monkeypatch.setenv("DUSTY_TEST_CANARY", "must not reach the target")
    result, stdout, _ = run_lines(
        [program, "env"], environment={"LC_ALL": "C", "PYTHONPATH": "/a:/b"}
    )
    assert result.exit_code == 0
    assert sorted(stdout) == ["LC_ALL=C", "PYTHONPATH=/a:/b"]
    with pytest.raises(ValueError):
        run_job_process([program, "env"], environment={"A=B": "x"})


def test_lifeline_passes_the_runner_environment_unchanged(
    program: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = {"LC_ALL": "C", "DUSTY_TEST_VALUE": "a b=c"}
    seen: list[Path] = []

    def choose(executable: Path) -> dict[str, str]:
        seen.append(executable)
        return chosen

    monkeypatch.setattr(mac_process, "child_environment", choose)
    monkeypatch.setenv("DUSTY_TEST_CANARY", "must not reach the target")
    result, stdout, _ = run_lines([program, "env"])
    assert result.exit_code == 0
    assert sorted(stdout) == ["DUSTY_TEST_VALUE=a b=c", "LC_ALL=C"]
    assert seen == [Path(program)]


def test_environment_choice_ignores_the_app_environment(
    bin_dir: Path, program: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dusty.runtime_paths import resolve_fetch_command

    for name in ("HOME", "TMPDIR", "PYTHONPATH", "DUSTY_TEST_CANARY"):
        monkeypatch.setenv(name, "must not reach a child")
    assert mac_process.child_environment(Path(program)) == {"LC_ALL": "C"}
    interpreter = Path(resolve_fetch_command()[0])
    assert mac_process.child_environment(interpreter) == {
        "LC_ALL": "C",
        "PYTHONPATH": str(ROOT / "src"),
    }


def test_environment_entries_are_validated(program: str, monkeypatch: pytest.MonkeyPatch) -> None:
    for bad in ({"A=B": "x"}, {"": "x"}, {"NAME": "a\0b"}):
        monkeypatch.setattr(mac_process, "child_environment", lambda executable, bad=bad: bad)
        with pytest.raises(ValueError):
            run_job_process([program, "env"])


def test_target_runs_in_its_executable_folder(bin_dir: Path, program: str) -> None:
    result, stdout, _ = run_lines([program, "cwd"], cwd=bin_dir / "tools")
    assert result.exit_code == 0
    assert stdout == [str(bin_dir / "tools")]
    with pytest.raises(ValueError, match="executable folder"):
        run_job_process([program, "cwd"], cwd=bin_dir)


def test_relative_and_unapproved_executables_are_rejected(
    bin_dir: Path, program: str, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="absolute path"):
        run_job_process(["tools/program", "echo"])
    with pytest.raises(ValueError, match="absolute path"):
        run_job_process([])
    outside = tmp_path / "program"
    shutil.copy2(program, outside)
    with pytest.raises(ValueError, match="not approved"):
        run_job_process([str(outside), "echo"])


def test_symlinked_executable_is_rejected(bin_dir: Path, program: str) -> None:
    link = bin_dir / "tools/linked-program"
    link.unlink(missing_ok=True)
    link.symlink_to(program)
    try:
        with pytest.raises(ValueError, match="not approved"):
            run_job_process([str(link), "echo"])
    finally:
        link.unlink()


def test_symlinked_or_missing_lifeline_is_rejected(
    built_bin: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "bin"
    (other / "tools").mkdir(parents=True)
    shutil.copy2(built_bin / "tools/program", other / "tools/program")
    monkeypatch.setenv("DUSTY_BIN_DIR", str(other))
    with pytest.raises(FileNotFoundError):
        run_job_process([str(other / "tools/program"), "echo"])
    (other / "lifeline").mkdir()
    (other / "lifeline/dusty-lifeline").symlink_to(built_bin / "lifeline/dusty-lifeline")
    with pytest.raises(ValueError, match="not approved"):
        run_job_process([str(other / "tools/program"), "echo"])


def test_missing_target_and_nul_argument_are_rejected(bin_dir: Path, program: str) -> None:
    with pytest.raises(FileNotFoundError):
        run_job_process([str(bin_dir / "tools/absent")])
    with pytest.raises(ValueError, match="NUL"):
        run_job_process([program, "echo\0hidden"])


def test_runner_closes_its_own_descriptors(program: str) -> None:
    before = set(os.listdir("/dev/fd"))
    for arguments in ([program, "echo", "0"], [program, "sleep"]):
        run_lines(arguments, timeout_sec=0.2)
    with pytest.raises(ValueError):
        run_job_process([program, "echo\0"])
    assert set(os.listdir("/dev/fd")) == before


def test_platform_dispatch_uses_mac_runner() -> None:
    from dusty.platform.process import platform_runner

    assert platform_runner() is mac_process.run_job_process
