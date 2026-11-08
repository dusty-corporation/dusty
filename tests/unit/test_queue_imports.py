"""Prove portable queue imports and actual file operations in fresh interpreters."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run_probe(source: str, *arguments: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", source, *(str(value) for value in arguments)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("module", ["storage", "scanning"])
def test_pure_queue_import_does_not_load_coordinator_or_windows_runtime(module):
    run_probe(f"""
import importlib
import sys
from pathlib import Path
from dusty.privacy.network_guard import install_guard
install_guard()
import dusty.queue as queue
assert Path(queue.__file__).is_relative_to(Path.cwd())
assert 'Coordinator' in dir(queue)
assert 'clear_history' in dir(queue)
try:
    queue.not_an_export
except AttributeError:
    pass
else:
    raise AssertionError('unknown export accepted')
importlib.import_module('dusty.queue.{module}')
for name in ('dusty.queue.coordinator', 'dusty.platform.win_process', 'msvcrt',
             'dusty.engine.ffmpeg', 'dusty.engine.whisper'):
    assert name not in sys.modules, name
""")


def test_storage_exports_round_trip_real_batch_without_coordinator(tmp_path):
    run_probe(
        """
import sys
from pathlib import Path
from dusty.core import BatchOptions, Job, JobStatus
from dusty.privacy.network_guard import install_guard
from dusty.queue import clear_history, load_batch, save_batch
import dusty.queue as queue
from dusty.queue import storage
install_guard()
root = Path(sys.argv[1])
state = root / 'state/queue.json'
options = BatchOptions('tiny', root / 'outputs', formats=('txt',), vad=False)
jobs = [Job(root / 'synthetic.wav', status=JobStatus.TRANSCRIBING)]
save_batch(state, options, jobs)
loaded_options, loaded_jobs = load_batch(state)
assert loaded_options == options
assert loaded_jobs[0].id == jobs[0].id
assert loaded_jobs[0].status == JobStatus.QUEUED
for name in ('clear_history', 'load_batch', 'save_batch'):
    assert getattr(queue, name) is getattr(storage, name)
    assert queue.__dict__[name] is getattr(storage, name)
clear_history(state)
assert not state.exists()
assert 'dusty.queue.coordinator' not in sys.modules
assert 'dusty.platform.win_process' not in sys.modules
assert 'msvcrt' not in sys.modules
""",
        tmp_path,
    )


def test_scanning_finds_nested_duplicates_and_rejects_links_under_guard(tmp_path):
    run_probe(
        """
import sys
from pathlib import Path
from dusty.privacy.network_guard import install_guard
from dusty.queue.scanning import scan_inputs
install_guard()
root = Path(sys.argv[1])
(root / 'nested').mkdir()
(root / 'first.wav').write_bytes(b'synthetic scanning fixture')
(root / 'nested/second.mp3').write_bytes(b'synthetic scanning fixture')
(root / 'notes.txt').write_text('not audio')
first = scan_inputs([root])
assert len(first.jobs) == 1
assert first.unsupported == 1
recursive = scan_inputs([root], recursive=True, existing=first.jobs)
assert len(recursive.jobs) == 1
assert recursive.jobs[0].source == root / 'nested/second.mp3'
assert recursive.jobs[0].relative_dir == Path('nested')
assert recursive.duplicates == 1
assert recursive.unsupported == 1
if sys.platform != 'win32':
    alias = root / 'alias.wav'
    alias.symlink_to(root / 'first.wav')
    rejected = scan_inputs([alias])
    assert not rejected.jobs and rejected.rejected == 1
assert 'dusty.queue.coordinator' not in sys.modules
assert 'dusty.platform.win_process' not in sys.modules
assert 'msvcrt' not in sys.modules
""",
        tmp_path,
    )


def test_all_public_exports_keep_real_api_identity_and_coordinator_is_deferred():
    run_probe("""
import sys
import dusty.queue as queue
assert queue.__all__ == ['Coordinator', 'cleanup_orphaned_work', 'clear_history',
                         'load_batch', 'save_batch']
assert 'dusty.queue.coordinator' not in sys.modules
assert 'Coordinator' not in queue.__dict__
namespace = {}
exec('from dusty.queue import *', namespace)
from dusty.queue import coordinator, storage
for name in queue.__all__:
    module = coordinator if name in ('Coordinator', 'cleanup_orphaned_work') else storage
    assert namespace[name] is getattr(module, name)
    assert getattr(queue, name) is getattr(module, name)
    assert queue.__dict__[name] is getattr(module, name)
assert 'dusty.platform.win_process' not in sys.modules
assert 'msvcrt' not in sys.modules
""")


def test_first_settings_publication_preserves_a_real_concurrent_writer(tmp_path):
    run_probe(
        """
import json
import os
import sys
from pathlib import Path
from dusty.privacy.network_guard import install_guard
from dusty.queue.storage import load_settings, save_settings
install_guard()
path = Path(sys.argv[1]) / 'settings.json'
snapshot = load_settings(path)
snapshot['backend_probe'] = {'ok': False}
original = {'schema_version': 1, 'prompt': 'synthetic concurrent hints', 'model_id': 'small'}
appeared = []
operation_name = 'rename' if os.name == 'nt' else 'link'
operation = getattr(os, operation_name)
def publish(source, target):
    if Path(target) == path and not appeared:
        appeared.append(True)
        path.write_text(json.dumps(original))
    return operation(source, target)
setattr(os, operation_name, publish)
try:
    save_settings(path, snapshot)
finally:
    setattr(os, operation_name, operation)
assert appeared == [True]
assert load_settings(path) == {**original, 'backend_probe': {'ok': False}}
assert not list(path.parent.glob('*.dusty-tmp'))
assert 'dusty.queue.coordinator' not in sys.modules
""",
        tmp_path,
    )
