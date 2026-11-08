"""Offline package imports never reach the isolated downloader."""

import subprocess
import sys
from pathlib import Path

from tools.check_no_network import check


def test_no_downloader_import_static_or_when_loading_all_offline_modules():
    root = Path(__file__).resolve().parents[2]
    assert check(root) == []
    script = """
import importlib, importlib.abc, pkgutil, sys
class RejectDownloader(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'dusty_fetch' or fullname.startswith('dusty_fetch.'):
            raise AssertionError('Offline package imported downloader')
sys.meta_path.insert(0, RejectDownloader())
import ctypes
import dusty
# A module may stop only because it needs a standard module or ctypes loader
# that exists on the other platform. The hook above still raises for any
# downloader import reached before that point, and every other error fails.
WINDOWS = sys.platform == 'win32'
OTHER_PLATFORM_MODULES = (
    {'fcntl', 'termios', 'resource', 'pwd', 'grp'}
    if WINDOWS
    else {'msvcrt', 'winreg', '_winapi', 'winsound'}
)
WINDOWS_ONLY_CTYPES = {'WinDLL', 'windll', 'WINFUNCTYPE', 'WinError', 'get_last_error'}
other_platform = []
for module in pkgutil.walk_packages(dusty.__path__, dusty.__name__ + '.'):
    try:
        importlib.import_module(module.name)
    except ImportError as exc:
        if exc.name not in OTHER_PLATFORM_MODULES:
            raise
        other_platform.append(module.name)
    except AttributeError as exc:
        if WINDOWS or exc.obj is not ctypes or exc.name not in WINDOWS_ONLY_CTYPES:
            raise
        other_platform.append(module.name)
own_runner = 'dusty.platform.' + ('win_process' if WINDOWS else 'mac_process')
assert own_runner not in other_platform and 'dusty.platform.process' not in other_platform
assert not any(name == 'dusty_fetch' or name.startswith('dusty_fetch.') for name in sys.modules)
print('offline_import_boundary=passed')
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=True
    )
    assert result.stdout.strip() == "offline_import_boundary=passed"
