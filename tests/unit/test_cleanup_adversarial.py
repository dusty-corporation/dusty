"""M5 second review: real OS locks and isolated cleanup failure injection."""

import os
import time
from pathlib import Path

from dusty.models.partials import cleanup_stale_partials
from dusty_fetch.downloader import download_lock, record_partial


def test_stale_partial_cleanup_respects_active_downloader_lock(tmp_path):
    models = tmp_path / "user/models"
    models.mkdir(parents=True)
    part = models / "ggml-test.bin.part"
    part.write_bytes(b"old resumable bytes")
    record_partial(part)
    old = time.time() - 9 * 24 * 60 * 60
    os.utime(part, (old, old))
    with download_lock(models / "ggml-test.bin.lock"):
        assert cleanup_stale_partials(models) == 0
        assert part.read_bytes() == b"old resumable bytes"
    assert cleanup_stale_partials(models) == 1
