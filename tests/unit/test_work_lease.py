"""A second startup must not remove another live instance's owned work."""

import subprocess
import sys

from dusty.queue import cleanup_orphaned_work


def test_second_process_preserves_live_work_and_cleans_after_owner_crash(tmp_path):
    work = tmp_path / "work"
    child = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            "from pathlib import Path; import sys; from dusty.work_area import OwnedWork; "
            "w=OwnedWork(Path(sys.argv[1]),'job'); "
            "(w.path/'audio.wav').write_bytes(b'public synthetic PCM'); "
            "w.record('audio.wav'); print('ready',flush=True); sys.stdin.read()",
            str(work),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "ready"
        directory = next(work.iterdir())
        cleanup_orphaned_work(work)
        assert (directory / "audio.wav").read_bytes() == b"public synthetic PCM"
        child.kill()  # No Python cleanup can run; the OS releases the lease.
        child.wait(timeout=10)
        cleanup_orphaned_work(work)
        assert not directory.exists()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        child.stdin.close()
        child.stdout.close()
