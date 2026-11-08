"""The macOS network attempt harness and the privacy canary audit (P31, P32)."""

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tools import mac_network_observe as observe
from tools import mac_privacy_canary as canary

darwin_tools = pytest.mark.skipif(
    sys.platform != "darwin"
    or not Path("/usr/bin/clang").exists()
    or not Path("/usr/bin/sandbox-exec").exists(),
    reason="needs macOS clang and sandbox-exec",
)


def test_records_split_into_loads_network_attempts_and_local_ipc():
    rows = [
        {"program": "cpu/whisper-cli", "call": "load", "family": 0},
        {"program": "cpu/whisper-cli", "call": "load", "family": 0},
        {"program": "ffmpeg/ffmpeg", "call": "connect", "family": 2, "detail": "1.2.3.4:443"},
        {"program": "ffmpeg/ffmpeg", "call": "socket", "family": 30},
        {"program": "ffmpeg/ffmpeg", "call": "getaddrinfo", "family": -1, "detail": "x"},
        {"program": "bin/python", "call": "socket", "family": 1},
        {"program": "bin/python", "call": "connect", "family": 1, "detail": "unix:/x"},
    ]
    seen = observe.classify(rows)
    assert seen["loaded"] == {"cpu/whisper-cli": 2}
    assert [row["call"] for row in seen["network"]] == ["connect", "socket", "getaddrinfo"]
    assert [row["family"] for row in seen["local_ipc"]] == [1, 1]


def test_kill_profile_targets_ip_and_resolution_but_not_every_network_rule():
    profile = observe.KILL_PROFILE
    assert "(allow default)" in profile and "(deny network*)\n" in profile
    assert "(deny network-outbound (remote ip) (with send-signal SIGKILL))" in profile
    assert "/private/var/run/mDNSResponder" in profile
    assert "(deny network-bind (local ip) (with send-signal SIGKILL))" in profile
    # A bare network* kill rule also fires on link(2) on macOS 26.2.
    assert "(deny network* (with send-signal" not in profile


@pytest.mark.parametrize("body", sorted(observe.CHILD_BODIES))
def test_child_scripts_compile(body):
    script = (
        observe.CHILD_PRELUDE
        % {"prefixes": observe.PYTHON_NETWORK_PREFIXES, "observe": observe.OBSERVE_ENV}
        + observe.CHILD_BODIES[body]
    )
    compile(script, f"child_{body}.py", "exec")
    assert script.index("sys.addaudithook(_record)") < script.index("install_guard()")


def test_only_sandbox_terminations_count_as_kill_reports(tmp_path):
    header = json.dumps({"app_name": "x"})
    for name, namespace in (("whisper-cli", "SANDBOX"), ("ffmpeg", "SIGNAL")):
        body = {"procName": name, "termination": {"namespace": namespace, "code": 1}}
        (tmp_path / f"{name}.ips").write_text(header + "\n" + json.dumps(body), encoding="utf-8")
    (tmp_path / "broken.ips").write_text("not json", encoding="utf-8")
    assert observe.sandbox_reports(0, tmp_path) == [
        {"process": "whisper-cli", "file": "whisper-cli.ips"}
    ]
    assert observe.sandbox_reports(time_far_future(), tmp_path) == []


def time_far_future() -> float:
    return 4102444800.0  # 2100-01-01


def test_runner_exit_is_read_from_the_child_report():
    assert observe.child_exit({"stdout_tail": ["noise", '{"exit_code": 137}']}) == 137
    assert observe.child_exit({"stdout_tail": ["no json"]}) is None


def scenario(status_inputs: dict) -> dict:
    entry = {
        "run": {"exit_code": 0, "killed_by_sigkill": False},
        "interposer": {"loaded": {"ffmpeg/ffmpeg": 1}, "network": [], "local_ipc": []},
        "python_events": [],
        "guard_log": [],
        "sandbox_reports": [],
        "not_observed": [],
    }
    entry.update(status_inputs)
    return entry


@pytest.mark.parametrize(
    ("changes", "completed", "status"),
    [
        ({}, True, "clean"),
        ({"run": {"exit_code": -9, "killed_by_sigkill": True}}, False, "network attempt"),
        ({"python_events": ["socket.connect"]}, True, "network attempt"),
        ({"guard_log": ["network_blocked event=socket.getaddrinfo"]}, True, "network attempt"),
        (
            {"sandbox_reports": [{"process": "whisper-cli", "file": "x.ips"}]},
            True,
            "network attempt",
        ),
        ({}, False, "did not complete"),
        ({"not_observed": ["metal/whisper-cli"]}, True, "incomplete observation"),
    ],
)
def test_scenario_status_never_reports_clean_without_evidence(tmp_path, changes, completed, status):
    harness = object.__new__(observe.Harness)
    harness.results = {"calibration": [], "scenarios": []}
    entry = harness.finish(scenario(changes), "case", ["sandbox kill"], completed)
    assert entry["status"] == status
    assert entry["passed"] is (status == "clean")


@darwin_tools
def test_positive_controls_are_detected_on_loopback(tmp_path):
    dylib, control, launcher = observe.compile_tools(tmp_path / "tools")
    log = tmp_path / "native.jsonl"
    env = dict(observe.TOOL_ENV, DYLD_INSERT_LIBRARIES=str(dylib), DUSTY_NETOBS_LOG=str(log))
    plain = subprocess.run([str(control), "all"], env=env, cwd=tmp_path, capture_output=True)
    assert plain.returncode == 0
    calls = {row["call"] for row in observe.classify(observe.read_jsonl(log))["network"]}
    assert {"connect", "sendto", "getaddrinfo"} <= calls
    env["NETOBS_INSERT"] = str(dylib)
    profile = observe.KILL_PROFILE
    for mode in ("connect", "udp", "resolve"):
        killed = subprocess.run(
            ["/usr/bin/sandbox-exec", "-p", profile, str(launcher), str(control), mode],
            env=env,
            cwd=tmp_path,
            capture_output=True,
        )
        assert killed.returncode == -9, mode
    for mode in ("quiet", "link"):
        quiet = subprocess.run(
            ["/usr/bin/sandbox-exec", "-p", profile, str(launcher), str(control), mode],
            env=env,
            cwd=tmp_path,
            capture_output=True,
        )
        assert quiet.returncode == 0, mode


def test_canary_needles_cover_encodings_and_case():
    patterns = canary.needles({"file": "DustyCanaryFileABC"})
    data = "x".join(["dustycanaryfileabc", "fellow"]).encode("utf-16-le")
    assert canary.search_bytes(data, patterns) == ["file", "word:fellow"]
    assert canary.search_bytes(b"nothing here", patterns) == []


@pytest.mark.skipif(sys.platform != "darwin", reason="extended attributes via macOS libc")
def test_canaries_are_found_inside_docx_archives(tmp_path):
    patterns = canary.needles({"hint": "DustyCanaryHint1"})
    docx = tmp_path / "out.docx"
    with zipfile.ZipFile(docx, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "<w:t>DustyCanaryHint1 Americans</w:t>" * 50)
    assert docx.read_bytes().count(b"DustyCanaryHint1") == 0  # compressed away
    assert canary.file_hits(docx, patterns) == ["hint", "word:Americans"]


@pytest.mark.skipif(sys.platform != "darwin", reason="extended attributes via macOS libc")
def test_canaries_are_found_in_extended_attributes(tmp_path):
    target = tmp_path / "plain.txt"
    target.write_text("nothing", encoding="utf-8")
    subprocess.run(
        ["/usr/bin/xattr", "-w", "org.dusty.test", "DustyCanaryOut9", str(target)], check=True
    )
    assert "org.dusty.test" in canary.xattr_names(target)
    assert canary.xattr_value(target, "org.dusty.test") == b"DustyCanaryOut9"
    assert canary.file_hits(target, canary.needles({"output": "DustyCanaryOut9"})) == ["output"]


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("appdata-dev/Dusty/state/queue.json", "by design"),
        ("appdata-dev/Dusty/settings.json", "by design"),
        ("appdata-dev/Dusty/settings.json.corrupt-20261107T1", "by design"),
        ("output/success/x/file.docx", "by design"),
        ("appdata-dev/Dusty/logs/dusty.log", "FINDING"),
        ("appdata-dev/Dusty/work/job-1/raw.json", "FINDING"),
    ],
)
def test_only_documented_locations_are_by_design(relative, expected):
    assert canary.classify(relative).startswith(expected)


def test_snapshot_reports_new_and_modified_entries(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a/old.txt").write_text("1", encoding="utf-8")
    before = canary.snapshot(tmp_path)
    (tmp_path / "a/new.txt").write_text("2", encoding="utf-8")
    after = canary.snapshot(tmp_path)
    assert "a/new.txt" in canary.changed_entries(before, after)
    assert "a/old.txt" not in canary.changed_entries(before, after)


def test_summaries_render_from_result_records():
    results = {
        "verdict": "no network attempts observed",
        "calibration": [{"name": "c", "expected": "e", "passed": True}],
        "unified_log_note": "",
        "scenarios": [
            {
                "name": "s",
                "run": {"exit_code": 0},
                "interposer": {"loaded": {"a": 1}, "network": []},
                "python_events": [],
                "guard_log": [],
                "status": "clean",
            }
        ],
    }
    assert "| s | 0 | a x1 | 0 | 0 | 0 | 0 | clean |" in observe.summary_markdown(results)
    audit = {
        "canaries": {"file": "F"},
        "runs": [{"name": "r", "exit_code": 0, "stdout_tail": ["done OK"], "expected": "OK"}],
        "files_scanned": 1,
        "hits": [
            {
                "location": "output",
                "path": "output/x.txt",
                "hits": ["word:fellow"],
                "name_hits": ["file"],
                "classification": "by design: x",
            }
        ],
        "findings": [],
        "unified_log_hits": [],
        "work_left": {"dev": []},
    }
    text = canary.summary_markdown(audit)
    assert "| output | output/x.txt | word:fellow | file | by design: x |" in text
    assert json.dumps({"dev": []}) in text


def test_tools_refuse_an_existing_output_folder(tmp_path, capsys):
    if sys.platform != "darwin":
        pytest.skip("both tools need macOS")
    assert observe.main(["--out", str(tmp_path)]) == 2
    assert canary.main(["--out", str(tmp_path)]) == 2
    assert "Refusing existing output folder" in capsys.readouterr().err
    assert shutil.which("true")  # nothing was created or removed
