"""Run irreversible audit-hook tests in fresh Python processes."""

import ast
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


def test_guard_blocks_dynamic_network_and_shell_delegation(tmp_path):
    result = run_child(f"""
        import ctypes, sys
        from dusty.privacy.network_guard import install_guard, NetworkBlockedError
        install_guard()
        for event, args in [
            ('ctypes.dlopen', ('WS2_32.dll',)),
            ('ctypes.dlopen', (r'C:\\Windows\\System32\\WINHTTP.DLL',)),
            ('ctypes.dlopen', ('wininet',)),
            ('ctypes.dlopen', ('urlmon.dll',)),
            ('ctypes.dlopen', ('mswsock.dll',)),
            ('ctypes.dlopen', ('iphlpapi.dll',)),
            ('ctypes.dlopen', (b'WS2_32.DLL',)),
            ('ctypes.dlopen', ('winhttp.dll. ',)),
            ('os.startfile', ('https://example.invalid/private', 'open')),
            ('os.startfile', ('missing.exe', 'open')),
            ('webbrowser.open', ('https://example.invalid',)),
            ('subprocess.Popen', ('curl.exe', [], None, None)),
            ('os.system', ('curl.exe',)),
        ]:
            try:
                sys.audit(event, *args)
            except NetworkBlockedError:
                pass
            else:
                raise AssertionError(event)
        sys.audit('os.startfile', {str(tmp_path)!r}, 'open')
        ctypes.WinDLL('kernel32')
        print('all blocked, folder allowed')
    """)
    assert "all blocked, folder allowed" in result.stdout
    assert "example.invalid" not in result.stderr
    assert "missing.exe" not in result.stderr


def test_shell_guard_rejects_unc_without_inspecting_the_remote_filesystem():
    result = run_child(r"""
        from pathlib import Path
        from dusty.privacy.network_guard import install_guard, NetworkBlockedError
        import sys
        install_guard()
        def unexpected_stat(*args):
            raise AssertionError('Remote path inspection attempted')
        Path.is_dir = unexpected_stat
        try:
            sys.audit('os.startfile', r'\\CANARY_HOST\share', 'open')
        except NetworkBlockedError:
            print('remote path rejected before stat')
        else:
            raise AssertionError('remote folder allowed')
    """)
    assert "remote path rejected before stat" in result.stdout
    assert "CANARY_HOST" not in result.stderr


def test_dusty_fetch_process_does_not_inherit_guard(tmp_path: Path) -> None:
    child = """
import runpy, socket, sys
sys.argv = ['dusty-fetch', 'verify', '--id', 'tiny', '--dest', sys.argv[1],
            '--manifest', sys.argv[2]]
try:
    runpy.run_module('dusty_fetch', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert 'dusty.privacy.network_guard' not in sys.modules
with socket.socket() as probe:
    assert probe.fileno() >= 0
print('child fetch unguarded')
"""
    result = run_child(f"""
        import hashlib, json, socket, subprocess, sys
        from pathlib import Path
        from dusty.privacy.network_guard import install_guard, NetworkBlockedError
        root = Path({str(tmp_path)!r})
        (root / 'ggml-test.bin').write_bytes(b'test model')
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({{'schema_version': 1, 'models': [{{
            'id': 'tiny', 'file_name': 'ggml-test.bin', 'size_bytes': 10,
            'sha256': hashlib.sha256(b'test model').hexdigest(),
            'url': 'https://github.com/dusty-corporation/dusty/releases/download/models-v1/ggml-test.bin'
        }}]}}), encoding='utf-8')
        install_guard()
        try:
            socket.socket()
        except NetworkBlockedError:
            pass
        else:
            raise AssertionError('Parent guard was not active')
        from dusty.platform.win_process import run_job_process
        lines = []
        separate = run_job_process([sys.executable, '-c', {child!r}, str(root), str(manifest)],
                                  on_stdout=lines.append, timeout_sec=20)
        assert separate.exit_code == 0
        assert 'child fetch unguarded' in lines
        print('fetch unguarded')
    """)
    assert result.stdout.strip() == "fetch unguarded"


def test_os_spawn_and_exec_audit_routes_are_blocked_without_arguments_logged():
    result = run_child("""
        import os, sys
        from dusty.privacy.network_guard import install_guard, NetworkBlockedError
        install_guard()
        for event in ('os.spawn', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'):
            try:
                sys.audit(event, 'CANARY_PRIVATE_ARGUMENT')
            except NetworkBlockedError:
                pass
            else:
                raise AssertionError(event)
        try:
            os.spawnv(os.P_WAIT, sys.executable, [sys.executable, '-c', 'pass'])
        except NetworkBlockedError:
            print('actual spawn blocked')
        else:
            raise AssertionError('actual spawn allowed')
    """)
    assert "actual spawn blocked" in result.stdout
    assert "CANARY_PRIVATE_ARGUMENT" not in result.stderr
