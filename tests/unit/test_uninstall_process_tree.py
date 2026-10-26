"""Inno launcher completion must not imply post-uninstall worker completion."""

import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_uninstall_tracker_waits_for_a_worker_after_its_launcher_exits(tmp_path):
    marker = tmp_path / "worker-completed"
    child = (
        "import time; from pathlib import Path; time.sleep(1.5); "
        f"Path({str(marker)!r}).write_bytes(b'complete')"
    )
    parent = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(0.1)"
    )
    encoded = base64.b64encode(parent.encode()).decode()
    script = tmp_path / "wait.ps1"
    script.write_text(
        f"""
$ErrorActionPreference='Stop'
. '{ROOT.as_posix()}/tools/uninstall_process_tree.ps1'
$psi=[Diagnostics.ProcessStartInfo]::new()
$psi.FileName='{Path(sys.executable).as_posix()}'
$psi.UseShellExecute=$false
$psi.CreateNoWindow=$true
[void]$psi.ArgumentList.Add('-c')
[void]$psi.ArgumentList.Add("import base64; exec(base64.b64decode('{encoded}'))")
$p=[Diagnostics.Process]::Start($psi)
$tracker=New-UninstallTracker $p
$deadline=[datetime]::UtcNow.AddSeconds(10)
try {{
 while(Update-UninstallTracker $tracker) {{
  if([datetime]::UtcNow -ge $deadline) {{throw 'worker deadline'}}
  Start-Sleep -Milliseconds 20
 }}
 Assert-UninstallTrackerExit $tracker 0
 if(-not(Test-Path -LiteralPath '{marker.as_posix()}')) {{throw 'returned before actual worker'}}
 if($tracker.Children.Count -lt 1) {{throw 'worker was not tracked'}}
}} finally {{Close-UninstallTracker $tracker; $p.Dispose()}}
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(script)], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.read_bytes() == b"complete"
    for name in ("test_installer.ps1", "test_uninstall_ui.ps1"):
        text = (ROOT / "tools" / name).read_text(encoding="utf-8")
        assert "Update-UninstallTracker" in text and "Assert-UninstallTrackerExit" in text
