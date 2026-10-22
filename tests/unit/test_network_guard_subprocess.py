"""Run irreversible audit-hook tests in fresh Python processes."""

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_child(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )


def test_guard_blocks_each_required_event_and_logs_only_name() -> None:
    result = run_child(
        """
        import socket
        import sys
        from dusty.privacy.network_guard import (
            BLOCKED_EVENTS, NetworkBlockedError, install_guard,
        )

        datagram = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        install_guard()
        for event in sorted(BLOCKED_EVENTS):
            try:
                sys.audit(event, "CANARY_HOSTNAME_SECRET")
            except NetworkBlockedError as exc:
                assert str(exc).endswith(event)
            else:
                raise AssertionError(event)

        operations = {
            "socket.__new__": lambda: socket.socket(),
            "socket.connect": lambda: stream.connect(("127.0.0.1", 1)),
            "socket.bind": lambda: datagram.bind(("127.0.0.1", 0)),
            "socket.sendto": lambda: datagram.sendto(b"x", ("127.0.0.1", 1)),
            "socket.getaddrinfo": lambda: socket.getaddrinfo("localhost", 80),
            "socket.gethostbyname": lambda: socket.gethostbyname("localhost"),
            "socket.gethostbyaddr": lambda: socket.gethostbyaddr("127.0.0.1"),
            "socket.getnameinfo": lambda: socket.getnameinfo(("127.0.0.1", 80), 0),
        }
        if hasattr(datagram, "sendmsg"):
            operations["socket.sendmsg"] = lambda: datagram.sendmsg([b"x"])
        for event, operation in operations.items():
            try:
                operation()
            except NetworkBlockedError as exc:
                assert str(exc).endswith(event), (event, str(exc))
            else:
                raise AssertionError(event)
        datagram.close()
        stream.close()
        print("blocked", len(BLOCKED_EVENTS), len(operations))
        """
    )
    assert "blocked 9" in result.stdout
    assert "CANARY_HOSTNAME_SECRET" not in result.stderr
    assert "localhost" not in result.stderr
    assert "127.0.0.1" not in result.stderr
    assert "network_blocked event=socket." in result.stderr


def test_real_dusty_entrypoint_installs_guard_before_app_imports() -> None:
    source = (ROOT / "src/dusty/__main__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_imports = (ast.Import, ast.ImportFrom)
    assert not any(isinstance(node, top_level_imports) for node in tree.body)
    result = run_child(
        """
        import runpy
        import sys
        from dusty.privacy.network_guard import NetworkBlockedError, is_installed
        sys.argv = ["dusty", "--version"]
        try:
            runpy.run_module("dusty", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
        assert is_installed()
        try:
            sys.audit("socket.connect", "CANARY_HOSTNAME_SECRET")
        except NetworkBlockedError:
            print("entrypoint guarded")
        else:
            raise AssertionError("Dusty entry point did not install guard")
        """
    )
    assert "entrypoint guarded" in result.stdout
    assert "CANARY_HOSTNAME_SECRET" not in result.stderr


def test_dusty_fetch_process_does_not_inherit_guard() -> None:
    result = run_child(
        """
        import runpy
        import socket
        import sys
        runpy.run_module("dusty_fetch", run_name="__main__")
        assert "dusty.privacy.network_guard" not in sys.modules
        with socket.socket() as probe:
            assert probe.fileno() >= 0
        print("fetch unguarded")
        """
    )
    assert result.stdout.strip() == "fetch unguarded"


def test_selftest_entrypoint_starts_with_guard(tmp_path: Path) -> None:
    script = """
        import runpy
        import sys
        from dusty.privacy.network_guard import NetworkBlockedError, is_installed
        sys.argv = ["dusty", "--self-test", "--backend", "cpu", "--model", "tiny"]
        try:
            runpy.run_module("dusty", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
        assert is_installed()
        try:
            sys.audit("socket.connect", "CANARY_HOSTNAME_SECRET")
        except NetworkBlockedError:
            print("selftest guarded")
        else:
            raise AssertionError("Self-test did not install guard")
    """
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=ROOT,
        env={**os.environ, "LOCALAPPDATA": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "OK" in result.stdout
    assert "selftest guarded" in result.stdout
    assert "CANARY_HOSTNAME_SECRET" not in result.stderr
