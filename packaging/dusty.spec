# PyInstaller 6.16.0: two onedir executables, one shared COLLECT.
import json
from pathlib import Path

root = Path(SPECPATH).parent
qt = root / '.venv/Lib/site-packages/PySide6'
unused_qt = [
    'PySide6.' + path.stem for path in qt.glob('Qt*.pyd')
    if path.stem not in {'QtCore', 'QtGui', 'QtWidgets'}
]
gui = Analysis(
    [str(root / 'packaging/dusty_entry.py')], pathex=[str(root / 'src')],
    hookspath=[str(root / 'packaging/hooks')],
    excludes=['dusty_fetch', *unused_qt, 'PySide6.QtNetwork',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtWebEngineQuick'],
    runtime_hooks=[str(root / 'packaging/runtime_guard.py')],
)
fetch = Analysis(
    [str(root / 'packaging/fetch_entry.py')], pathex=[str(root / 'src')],
    excludes=['dusty', 'PySide6', 'shiboken6'],
)
# Fail rather than silently choose a different binary at the same destination.
destinations = {}
for destination, source, kind in [*gui.binaries, *gui.datas, *fetch.binaries, *fetch.datas]:
    key = destination.lower()
    previous = destinations.get(key)
    if previous and Path(previous).read_bytes() != Path(source).read_bytes():
        raise ValueError('Conflicting shared runtime destination: ' + destination)
    destinations[key] = source
audit = root / 'build/packaging'
audit.mkdir(parents=True, exist_ok=True)
(audit / 'analysis.json').write_text(json.dumps({
    'pure': [*gui.pure, *fetch.pure],
    'gui_pure': gui.pure,
    'fetch_pure': fetch.pure,
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
COLLECT(app, downloader, gui.binaries, gui.datas, fetch.binaries, fetch.datas,
        name='Dusty')
