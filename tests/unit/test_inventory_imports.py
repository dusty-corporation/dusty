"""Keep pure inventory helpers portable while refusing unavailable PE audits."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DENY_PE = """
import sys
class DenyPE:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('pefile', 'tools.check_pe_imports'):
            raise ModuleNotFoundError('PE inspection deliberately unavailable', name=fullname)
sys.meta_path.insert(0, DenyPE())
"""


def run_probe(source: str, *arguments: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
    return subprocess.run(
        [sys.executable, "-c", DENY_PE + source, *(str(value) for value in arguments)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_pure_inventory_helpers_import_without_pe_parser():
    result = run_probe("""
from pathlib import Path
from tools import inventory_bundle as inventory
assert Path(inventory.__file__).is_relative_to(Path.cwd())
banner = 'ffmpeg version n9.0.2\\nconfiguration: --disable-network'
assert inventory.clean_buildconf('wine bootstrap\\n' + banner) == banner
try:
    inventory.clean_buildconf('missing native banner')
except ValueError:
    pass
else:
    raise AssertionError('missing banner accepted')
assert inventory.component('test', '1', 'MIT', 'synthetic')['license'] == 'MIT'
assert 'pefile' not in sys.modules
assert 'tools.check_pe_imports' not in sys.modules
""")
    assert result.returncode == 0, result.stderr


def test_requested_copyright_inspection_requires_parser(tmp_path):
    candidate = tmp_path / "candidate.dll"
    candidate.write_bytes(b"MZ synthetic candidate")
    result = run_probe(
        """
from pathlib import Path
from tools.inventory_bundle import copyright_from_pe
print('REQUESTED_PE', flush=True)
copyright_from_pe(Path(sys.argv[1]))
""",
        candidate,
    )
    assert "REQUESTED_PE" in result.stdout
    assert result.returncode != 0
    assert "PE inspection deliberately unavailable" in result.stderr
    assert candidate.read_bytes() == b"MZ synthetic candidate"


@pytest.mark.parametrize("operation", ["function", "cli"])
@pytest.mark.parametrize("existing_output", [False, True])
def test_requested_inventory_fails_before_any_output_mutation(tmp_path, operation, existing_output):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "sentinel.txt").write_bytes(b"unchanged bundle")
    analysis = tmp_path / "analysis.json"
    analysis.write_text("{}", encoding="utf-8")
    output = tmp_path / "audit"
    if existing_output:
        output.mkdir()
        (output / "inventory.json").write_bytes(b"previous inventory")
        (output / "crt-provenance.json").write_text('{"files":[]}', encoding="utf-8")

    def snapshot():
        return {
            path.relative_to(tmp_path): None if path.is_dir() else path.read_bytes()
            for path in tmp_path.rglob("*")
        }

    before = snapshot()
    result = run_probe(
        f"""
from pathlib import Path
from tools import inventory_bundle as inventory
print('REQUESTED_INVENTORY', flush=True)
if {operation!r} == 'function':
    inventory.generate(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
else:
    sys.argv = ['inventory_bundle', sys.argv[1], '--analysis', sys.argv[2], '--output', sys.argv[3]]
    inventory.main()
""",
        bundle,
        analysis,
        output,
    )
    assert "REQUESTED_INVENTORY" in result.stdout
    assert result.returncode != 0
    assert "PE inspection deliberately unavailable" in result.stderr
    assert "Inventoried" not in result.stdout
    assert snapshot() == before


def test_malformed_pe_error_is_not_replaced_with_copyright_fallback(tmp_path):
    result = run_probe(
        """
from pathlib import Path
from types import ModuleType
from tools.inventory_bundle import copyright_from_pe
parser = ModuleType('pefile')
def invalid(path):
    raise ValueError('synthetic malformed PE')
parser.PE = invalid
sys.modules['pefile'] = parser
try:
    copyright_from_pe(Path(sys.argv[1]))
except ValueError as error:
    assert str(error) == 'synthetic malformed PE'
else:
    raise AssertionError('malformed PE approved')
""",
        tmp_path / "synthetic.dll",
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("present", [False, True])
def test_copyright_reader_preserves_parser_context_and_metadata(present, tmp_path):
    result = run_probe(
        f"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
from tools.inventory_bundle import copyright_from_pe
opened = []
closed = []
class Executable:
    FileInfo = [[SimpleNamespace(StringTable=[SimpleNamespace(entries=
        {{b'LegalCopyright': b'Synthetic copyright'}} if {present!r} else {{}})])]]
    def __init__(self, path):
        opened.append(path)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        closed.append(True)
parser = ModuleType('pefile')
parser.PE = Executable
sys.modules['pefile'] = parser
value = copyright_from_pe(Path(sys.argv[1]))
expected = 'Synthetic copyright' if {present!r} else 'See retained upstream copyright notices'
assert value == expected
assert opened == [sys.argv[1]] and closed == [True]
""",
        tmp_path / "synthetic.dll",
    )
    assert result.returncode == 0, result.stderr
