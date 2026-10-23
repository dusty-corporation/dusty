# PyInstaller 6.16.0: separate onedir runtimes; shared native/resources parent.
import json
import shutil
from pathlib import Path

root = Path(SPECPATH).parent
audit = root / 'build/packaging'
warnings = audit / 'audit'
warnings.mkdir(parents=True, exist_ok=True)
qt = root / '.venv/Lib/site-packages/PySide6'
unused_qt = [
    'PySide6.' + path.stem for path in qt.glob('Qt*.pyd')
    if path.stem not in {'QtCore', 'QtGui', 'QtWidgets'}
]
gui = Analysis(
    [str(root / 'packaging/dusty_entry.py')], pathex=[str(root / 'src')],
    hookspath=[str(root / 'packaging/hooks')],
    excludes=['dusty_fetch', 'docx', 'lxml', 'socket', 'ssl', '_socket', '_ssl', '_hashlib',
              'select', '_overlapped', '_multiprocessing', 'asyncio', 'multiprocessing',
              *unused_qt, 'PySide6.QtNetwork',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtWebEngineQuick'],
    runtime_hooks=[str(root / 'packaging/runtime_guard.py')],
)
shutil.copyfile(WARNFILE, warnings / 'warn-gui.txt')
fetch = Analysis(
    [str(root / 'packaging/fetch_entry.py')], pathex=[str(root / 'src')],
    excludes=['dusty', 'PySide6', 'shiboken6'],
)
shutil.copyfile(WARNFILE, warnings / 'warn-fetch.txt')
# UCRT/API-set files are supplied by the supported Windows 10+ platform.
for analysis in (gui, fetch):
    analysis.binaries = [item for item in analysis.binaries
                         if not Path(item[0]).name.lower().startswith('api-ms-win-')
                         and Path(item[0]).name.lower() != 'ucrtbase.dll']
audit.mkdir(parents=True, exist_ok=True)
(audit / 'analysis.json').write_text(json.dumps({
    'pure': [*gui.pure, *fetch.pure],
    'gui_pure': gui.pure,
    'fetch_pure': fetch.pure,
    'gui_binaries': gui.binaries,
    'fetch_binaries': fetch.binaries,
    'gui_datas': gui.datas,
    'fetch_datas': fetch.datas,
    'binaries': [*gui.binaries, *fetch.binaries],
    'datas': [*gui.datas, *fetch.datas],
    'gui_scripts': gui.scripts,
    'fetch_scripts': fetch.scripts,
}, indent=2), encoding='utf-8')
app = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
          name='dusty', console=False, icon=str(root / 'resources/icons/dusty.ico'))
downloader = EXE(PYZ(fetch.pure), fetch.scripts, [], exclude_binaries=True,
                 name='dusty-fetch', console=True,
                 icon=str(root / 'resources/icons/dusty.ico'))
COLLECT(app, gui.binaries, gui.datas, name='dusty')
COLLECT(downloader, fetch.binaries, fetch.datas, name='dusty-fetch')
