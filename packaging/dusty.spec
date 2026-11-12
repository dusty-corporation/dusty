# PyInstaller 6.16.0: separate onedir runtimes; shared native/resources parent.
# Add-on helper programs (tools/helper_programs.py) are built the same way; public
# Dusty has none, and its GUI must embed no add-on module.
import json
import shutil
import sys
from pathlib import Path

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from tools.helper_programs import gui_module_findings, load_programs  # noqa: E402

programs = load_programs(root)
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
              'PySide6.QtWebEngineQuick',
              *[name for program in programs for name in program.gui_excludes]],
    runtime_hooks=[str(root / 'packaging/runtime_guard.py')],
)
shutil.copyfile(WARNFILE, warnings / 'warn-gui.txt')
gui_findings = gui_module_findings([name for name, _, _ in gui.pure], programs)
if gui_findings:
    raise SystemExit('\n'.join(gui_findings))
fetch = Analysis(
    [str(root / 'packaging/fetch_entry.py')], pathex=[str(root / 'src')],
    excludes=['dusty', 'PySide6', 'shiboken6'],
    runtime_hooks=[str(root / 'packaging/runtime_fetch_crash.py')],
)
shutil.copyfile(WARNFILE, warnings / 'warn-fetch.txt')
helpers = {}
for program in programs:
    helper = Analysis(
        [str(root / program.entry)], pathex=[str(root / 'src')],
        excludes=program.all_excludes('win32'),
        runtime_hooks=[str(root / 'packaging/runtime_guard.py')],
    )
    # Package metadata is not needed at run time; the inventory keeps the license texts.
    helper.datas = [item for item in helper.datas if '.dist-info' not in item[0]]
    helper.binaries = [item for item in helper.binaries
                       if not program.drops(Path(item[0]).name, 'win32')]
    shutil.copyfile(WARNFILE, warnings / f'warn-{program.name}.txt')
    helpers[program] = helper
# UCRT/API-set files are supplied by the supported Windows 10+ platform.
for analysis in (gui, fetch, *helpers.values()):
    analysis.binaries = [item for item in analysis.binaries
                         if not Path(item[0]).name.lower().startswith('api-ms-win-')
                         and Path(item[0]).name.lower() != 'ucrtbase.dll']
audit.mkdir(parents=True, exist_ok=True)
everything = (gui, fetch, *helpers.values())
record = {
    'pure': [item for analysis in everything for item in analysis.pure],
    'gui_pure': gui.pure,
    'fetch_pure': fetch.pure,
    'gui_binaries': gui.binaries,
    'fetch_binaries': fetch.binaries,
    'gui_datas': gui.datas,
    'fetch_datas': fetch.datas,
    'binaries': [item for analysis in everything for item in analysis.binaries],
    'datas': [item for analysis in everything for item in analysis.datas],
    'gui_scripts': gui.scripts,
    'fetch_scripts': fetch.scripts,
}
for program, helper in helpers.items():
    record.update({
        f'{program.group}_pure': helper.pure,
        f'{program.group}_binaries': helper.binaries,
        f'{program.group}_datas': helper.datas,
        f'{program.group}_scripts': helper.scripts,
    })
(audit / 'analysis.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
app = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
          version=str(audit / 'version.txt'),
          name='dusty', console=False, icon=str(root / 'resources/icons/dusty.ico'))
downloader = EXE(PYZ(fetch.pure), fetch.scripts, [], exclude_binaries=True,
                 version=str(audit / 'version.txt'),
                 name='dusty-fetch', console=True,
                 icon=str(root / 'resources/icons/dusty.ico'))
COLLECT(app, gui.binaries, gui.datas, name='dusty')
COLLECT(downloader, fetch.binaries, fetch.datas, name='dusty-fetch')
for program, helper in helpers.items():
    program_exe = EXE(PYZ(helper.pure), helper.scripts, [], exclude_binaries=True,
                      version=str(audit / 'version.txt'),
                      name=program.name, console=True,
                      icon=str(root / 'resources/icons/dusty.ico'))
    COLLECT(program_exe, helper.binaries, helper.datas, name=program.name)
