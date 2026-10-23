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
import dusty
for module in pkgutil.walk_packages(dusty.__path__, dusty.__name__ + '.'):
    importlib.import_module(module.name)
assert not any(name == 'dusty_fetch' or name.startswith('dusty_fetch.') for name in sys.modules)
print('offline_import_boundary=passed')
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=30, check=True
    )
    assert result.stdout.strip() == "offline_import_boundary=passed"
