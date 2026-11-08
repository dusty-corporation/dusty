"""Launch the isolated downloader on macOS exactly as the guarded app does.

A guarded parent Python plays the app: it installs the network guard and calls
dusty.platform.process.run_job_process with the downloader command, the same
arguments and callbacks model_manager uses. The downloader is a grandchild of
pytest under the dusty-lifeline helper. The only server is the loopback HTTPS
fixture from test_downloader with its throwaway certificate.

The production CLI has no trust or host override, so it can only verify a file
or refuse the loopback URL. The full transfer and cancel checks run the
test-only fetch_child.py adapter, which injects the certificate and the
loopback host policy as a library caller, through the same runner.
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

if sys.platform != "darwin":
    pytest.skip("The lifeline runner exists only on macOS", allow_module_level=True)
if shutil.which("xcrun") is None:
    pytest.skip("Building the lifeline needs the Xcode command line tools", allow_module_level=True)

from test_downloader import CHUNK, DATA, args  # noqa: E402
from test_downloader import tls as tls_fixture  # noqa: E402

from dusty.runtime_paths import resolve_fetch_command  # noqa: E402

tls = tls_fixture
ROOT = Path(__file__).resolve().parents[2]
FETCH_CHILD = ROOT / "tests/fixtures/https/fetch_child.py"

# The guarded parent mirrors DownloadWorker.run: same runner, same command
# prefix, same model_manager style arguments and a cancel event.
APP = """
import json, sys, threading
from dusty.privacy.network_guard import NetworkBlockedError, install_guard
install_guard()
import socket
try:
    socket.socket()
except NetworkBlockedError:
    pass
else:
    raise AssertionError("guard inactive")
from dusty.platform.process import run_job_process
command, cancel_at = json.loads(sys.argv[1]), int(sys.argv[2])
cancel = threading.Event()
events = []

def receive(line):
    event = json.loads(line)
    events.append(event)
    if cancel_at and event.get("event") == "downloading" and event["bytes"] >= cancel_at:
        cancel.set()

result = run_job_process(command, on_stdout=receive, cancel=cancel, timeout_sec=60)
print(json.dumps({
    "exit_code": result.exit_code,
    "cancelled": result.cancelled,
    "events": events,
    "app_pid": __import__("os").getpid(),
}))
"""


@pytest.fixture(scope="module")
def lifeline_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    bin_dir = tmp_path_factory.mktemp("mac-fetch").resolve() / "bin"
    subprocess.run(
        ["/bin/bash", str(ROOT / "native/macos/build_lifeline.sh"), str(bin_dir)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return bin_dir


def run_app(command: list[str], bin_dir: Path, cancel_at: int = 0) -> dict:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["DUSTY_BIN_DIR"] = str(bin_dir)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(APP), json.dumps(command), str(cancel_at)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


def model_manager_arguments(tls, log: Path) -> list[str]:
    return [*args(tls), "--failure-log", str(log)]


def test_source_command_is_the_real_interpreter_without_site_or_cwd() -> None:
    command = resolve_fetch_command()
    assert command[1:] == ["-S", "-P", "-m", "dusty_fetch"]
    assert Path(command[0]) == Path(sys.executable).resolve()
    assert not Path(command[0]).is_symlink()


def test_downloader_style_launch_sees_only_its_environment(
    lifeline_bin: Path, tmp_path: Path
) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import json, os, sys\n"
        "print(json.dumps({'event': 'probe', 'environ': dict(os.environ), 'path': sys.path,"
        " 'site': 'site' in sys.modules, 'utf8': sys.flags.utf8_mode}))\n",
        encoding="utf-8",
    )
    interpreter = resolve_fetch_command()[0]
    outcome = run_app([interpreter, "-S", "-P", str(probe)], lifeline_bin)
    assert outcome["exit_code"] == 0 and not outcome["cancelled"]
    probe_event = outcome["events"][0]
    environ = probe_event["environ"]
    # CoreFoundation, loaded by the interpreter, sets this one itself at start.
    environ.pop("__CF_USER_TEXT_ENCODING", None)
    assert environ == {"LC_ALL": "C", "PYTHONPATH": str(ROOT / "src")}
    assert probe_event["site"] is False and probe_event["utf8"] == 1
    assert str(ROOT / "src") in probe_event["path"]
    assert not any("site-packages" in entry for entry in probe_event["path"])


def test_production_command_verifies_through_the_guarded_runner(
    tls, lifeline_bin: Path, tmp_path: Path
) -> None:
    # The production policy accepts only the GitHub release hosts. Verify never
    # connects, so a catalog style URL is safe here.
    manifest = json.loads(tls.manifest.read_text(encoding="utf-8"))
    manifest["models"][0]["url"] = (
        "https://github.com/dusty-corporation/dusty/releases/download/models-v1/ggml-test.bin"
    )
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(manifest), encoding="utf-8")
    tls.dest.mkdir()
    (tls.dest / tls.asset.file_name).write_bytes(DATA)
    verify = ["verify", "--id", "tiny", "--dest", str(tls.dest), "--manifest", str(catalog)]
    outcome = run_app(resolve_fetch_command() + verify, lifeline_bin)
    assert (outcome["exit_code"], outcome["cancelled"]) == (0, False)
    assert [event["event"] for event in outcome["events"]] == ["verified"]
    assert outcome["events"][0]["pid"] != outcome["app_pid"]
    assert tls.requests == []


def test_production_command_refuses_the_loopback_server(tls, lifeline_bin: Path) -> None:
    log = tls.dest.parent / "user/Dusty/logs/dusty.log"
    outcome = run_app(resolve_fetch_command() + model_manager_arguments(tls, log), lifeline_bin)
    assert outcome["exit_code"] == 3 and not outcome["cancelled"]
    error = outcome["events"][-1]
    assert (error["event"], error["code"], error["logged"]) == ("error", "BLOCKED", True)
    assert log.read_text(encoding="utf-8").splitlines() == [
        "download_failure step=next_file class=FetchError winerror=0 code=BLOCKED exit_code=3"
    ]
    assert tls.requests == []
    assert not tls.dest.exists()


def test_library_adapter_downloads_from_the_loopback_server(tls, lifeline_bin: Path) -> None:
    log = tls.dest.parent / "user/Dusty/logs/dusty.log"
    command = [resolve_fetch_command()[0], str(FETCH_CHILD), str(tls.port), str(tls.certificate)]
    outcome = run_app(command + model_manager_arguments(tls, log), lifeline_bin)
    assert (outcome["exit_code"], outcome["cancelled"]) == (0, False)
    names = [event["event"] for event in outcome["events"]]
    assert names[-2:] == ["verifying", "complete"]
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA
    assert not list(tls.dest.glob("*.part"))
    assert not log.exists()
    assert tls.requests == [None]


def test_cancel_kills_the_downloader_and_keeps_no_final_file(tls, lifeline_bin: Path) -> None:
    tls.mode = "slow"
    log = tls.dest.parent / "user/Dusty/logs/dusty.log"
    command = [resolve_fetch_command()[0], str(FETCH_CHILD), str(tls.port), str(tls.certificate)]
    outcome = run_app(command + model_manager_arguments(tls, log), lifeline_bin, 2 * CHUNK)
    assert outcome["cancelled"] and outcome["exit_code"] == 125
    pid = outcome["events"][0]["pid"]
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        pytest.fail("Downloader outlived the cancel")
    assert not (tls.dest / tls.asset.file_name).exists()
    assert not log.exists()
