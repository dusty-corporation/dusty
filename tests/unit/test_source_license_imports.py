"""Separate source-license auditing from explicitly requested PE inspection."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DENY_PE_IMPORTS = """
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
        [sys.executable, "-c", DENY_PE_IMPORTS + source, *(str(item) for item in arguments)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_source_modules_and_staging_aliases_import_without_pe_inspection():
    result = run_probe("""
from pathlib import Path
from tools import check_licenses, stage_microsoft_runtime as stage
assert Path(check_licenses.__file__).is_relative_to(Path.cwd())
for name in ('crt_importers', 'runtime_pins', 'valid_source'):
    assert getattr(check_licenses, name) is getattr(stage, name)
assert check_licenses.allowed_license('dusty', 'Apache-2.0')
assert not check_licenses.allowed_license('unrelated', 'GPL-3.0-only')
assert stage.runtime_pins()['files']
assert callable(stage.imports)
assert 'pefile' not in sys.modules
assert 'tools.check_pe_imports' not in sys.modules
""")
    assert result.returncode == 0, result.stderr


def test_actual_source_license_cli_works_with_pe_imports_denied():
    result = run_probe("""
import runpy
sys.argv = ['tools/check_licenses.py']
runpy.run_path('tools/check_licenses.py', run_name='__main__')
""")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Runtime license check passed"


def test_requested_bundle_cli_refuses_without_parser(tmp_path):
    (tmp_path / "inventory.json").write_text('{"components":{},"files":[]}', encoding="utf-8")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    result = run_probe(
        """
from tools import check_licenses
sys.argv = ['tools/check_licenses.py', '--bundle', sys.argv[1], '--inventory', sys.argv[2]]
print('REQUESTED_BUNDLE', flush=True)
raise SystemExit(check_licenses.main())
""",
        bundle,
        tmp_path / "inventory.json",
    )
    assert result.returncode != 0
    assert "REQUESTED_BUNDLE" in result.stdout
    assert "PE inspection deliberately unavailable" in result.stderr
    assert "license check passed" not in result.stdout.lower()


@pytest.mark.parametrize(
    "operation", ["file_version", "microsoft_vendor", "crt_importers", "stage"]
)
def test_requested_pe_staging_operations_fail_before_mutating_inputs(tmp_path, operation):
    candidate = tmp_path / "vcruntime140.dll"
    candidate.write_bytes(b"MZ synthetic invalid PE")
    result = run_probe(
        f"""
from pathlib import Path
from tools import stage_microsoft_runtime as stage
root = Path(sys.argv[1])
assert 'pefile' not in sys.modules
assert 'tools.check_pe_imports' not in sys.modules
operation = {operation!r}
print('REQUESTED_PE', flush=True)
if operation == 'stage':
    stage.stage(root, root / 'unavailable-redist', root / 'receipt.json')
elif operation == 'crt_importers':
    stage.crt_importers(root)
else:
    getattr(stage, operation)(root / 'vcruntime140.dll')
""",
        tmp_path,
    )
    assert result.returncode != 0
    assert "REQUESTED_PE" in result.stdout
    assert "PE inspection deliberately unavailable" in result.stderr
    assert candidate.read_bytes() == b"MZ synthetic invalid PE"
    assert not (tmp_path / "receipt.json").exists()


def test_parser_errors_are_not_silently_treated_as_non_microsoft(tmp_path):
    candidate = tmp_path / "invalid.dll"
    candidate.write_bytes(b"MZ malformed synthetic input")
    result = run_probe(
        """
from pathlib import Path
from types import ModuleType
from tools import stage_microsoft_runtime as stage
parser = ModuleType('pefile')
def invalid(*args, **kwargs):
    raise ValueError('synthetic malformed PE')
parser.PE = invalid
sys.modules['pefile'] = parser
for operation in (stage.file_version, stage.microsoft_vendor):
    try:
        operation(Path(sys.argv[1]))
    except ValueError as error:
        assert str(error) == 'synthetic malformed PE'
    else:
        raise AssertionError('invalid PE accepted')
""",
        candidate,
    )
    assert result.returncode == 0, result.stderr


def test_non_pe_vendor_probe_needs_no_parser(tmp_path):
    candidate = tmp_path / "notice.txt"
    candidate.write_text("synthetic notice", encoding="utf-8")
    result = run_probe(
        """
from pathlib import Path
from tools import stage_microsoft_runtime as stage
assert stage.microsoft_vendor(Path(sys.argv[1])) is False
assert 'pefile' not in sys.modules
assert 'tools.check_pe_imports' not in sys.modules
""",
        candidate,
    )
    assert result.returncode == 0, result.stderr


def test_crt_importer_keeps_existing_override_hook(tmp_path):
    (tmp_path / "dusty").mkdir()
    candidate = tmp_path / "dusty/app.exe"
    candidate.write_bytes(b"MZ synthetic importer")
    result = run_probe(
        """
from pathlib import Path
from types import ModuleType
from tools import stage_microsoft_runtime as stage
inspection = ModuleType('tools.check_pe_imports')
inspection.imports = lambda path: (_ for _ in ()).throw(AssertionError('override bypassed'))
sys.modules[inspection.__name__] = inspection
called = []
def override(path):
    called.append(path.name)
    return {'vcruntime140.dll': ['synthetic_import']}
stage.imports = override
assert stage.crt_importers(Path(sys.argv[1])) == {
    'dusty/vcruntime140.dll': ['dusty/app.exe']
}
assert called == ['app.exe']
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("failure", ["missing", "version"])
def test_source_audit_still_rejects_missing_or_wrong_locked_distribution(
    tmp_path, monkeypatch, failure
):
    from tools import check_licenses

    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname="dusty"\nversion="1.0.0"\n'
        'dependencies=[{name="synthetic-runtime"}]\n'
        '[[package]]\nname="synthetic-runtime"\nversion="1.0.0"\n',
        encoding="utf-8",
    )

    class Distribution:
        version = "2.0.0"
        metadata = {"License": "MIT"}

    def distribution(name):
        if failure == "missing":
            raise check_licenses.importlib.metadata.PackageNotFoundError(name)
        return Distribution()

    monkeypatch.setattr(check_licenses.importlib.metadata, "distribution", distribution)
    findings = check_licenses.check(tmp_path)
    expected = "installed distribution missing" if failure == "missing" else "differs from lockfile"
    assert any(expected in finding for finding in findings)
