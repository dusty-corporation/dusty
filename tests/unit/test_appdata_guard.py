"""Prove the session guard rejects protected file access before opening a file."""

import subprocess
import sys
from pathlib import Path


def test_real_appdata_guard_rejects_reads_writes_and_listing(tmp_path: Path) -> None:
    script = """
import sys
from pathlib import Path
from tools.test_appdata_guard import install_guard
root = Path(sys.argv[1])
install_guard(root)
attempts = [lambda: (root/'settings.json').read_text(),
            lambda: (root/'settings.json').write_text('forbidden'),
            lambda: list(root.iterdir()), lambda: root.mkdir(),
            lambda: (root/'settings.json').unlink()]
for attempt in attempts:
    try:
        attempt()
    except PermissionError:
        continue
    raise AssertionError('Guard did not reject access')
print('protected_operations=5')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "protected")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "protected_operations=5"
    assert not (tmp_path / "protected").exists()
