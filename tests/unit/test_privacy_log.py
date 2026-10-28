"""Canary checks for local diagnostic redaction and sync warnings."""

import logging
from pathlib import Path

from dusty.privacy.logging import RedactionFilter, RotatingFileHandler, configure_logger
from dusty.privacy.sync import is_synced, sync_roots


def test_canary_never_reaches_log(tmp_path: Path) -> None:
    logger = configure_logger(tmp_path)
    logger.info("job_id=12345678-1234-1234-1234-123456789abc status=done")
    logger.info("CANARY_PATIENT_JANE_DOE.wav CANARYMEDTERM C:\\Users\\Jane\\clip.wav")
    for handler in logger.handlers:
        handler.flush()
    content = (tmp_path / "logs/dusty.log").read_text(encoding="utf-8")
    assert "job_id=12345678-1234-1234-1234-123456789abc status=done" in content
    assert "CANARY_PATIENT_JANE_DOE" not in content
    assert "CANARYMEDTERM" not in content
    assert not RedactionFilter().filter(
        logging.LogRecord("dusty", logging.INFO, "", 0, "C:\\Users\\Jane\\clip.wav", (), None)
    )


def test_download_process_fallback_is_redacted(tmp_path: Path) -> None:
    logger = configure_logger(tmp_path)
    safe = "download_failure step=next_file class=ProcessError winerror=0 code=PROTOCOL exit_code=7"
    logger.info(safe)
    logger.info(safe + " C:\\Users\\Jane\\meeting.wav")
    for handler in logger.handlers:
        handler.flush()
    assert (tmp_path / "logs/dusty.log").read_text(encoding="utf-8").count(safe) == 1


def test_local_log_rotation_is_bounded_and_retains_filter(tmp_path: Path) -> None:
    handler = RotatingFileHandler(
        tmp_path / "bounded.log", maxBytes=40, backupCount=2, encoding="utf-8"
    )
    handler.addFilter(RedactionFilter())
    try:
        for _ in range(10):
            handler.handle(logging.LogRecord("dusty", logging.INFO, "", 0, "status=done", (), None))
        handler.handle(
            logging.LogRecord("dusty", logging.INFO, "", 0, "CANARY_RECORDING", (), None)
        )
    finally:
        handler.close()
    paths = list(tmp_path.glob("bounded.log*"))
    assert len(paths) == 3
    assert all(path.stat().st_size <= 40 for path in paths)
    assert all("CANARY" not in path.read_text() for path in paths)


def test_sync_root_detection(tmp_path: Path) -> None:
    root = tmp_path / "OneDrive"
    assert is_synced(root / "notes", (root,))
    assert not is_synced(tmp_path / "local", (root,))


def test_sync_root_discovery(tmp_path: Path) -> None:
    appdata = tmp_path / "appdata"
    info = appdata / "Dropbox/info.json"
    info.parent.mkdir(parents=True)
    dropbox = tmp_path / "Dropbox"
    info.write_text('{"personal":{"path":"' + dropbox.as_posix() + '"}}', encoding="utf-8")
    google = tmp_path / "Google Drive"
    google.mkdir()
    env = {
        "OneDrive": str(tmp_path / "OneDrive"),
        "APPDATA": str(appdata),
        "USERPROFILE": str(tmp_path),
    }
    roots = sync_roots(env)
    assert (tmp_path / "OneDrive").resolve() in roots
    assert dropbox.resolve() in roots
    assert google.resolve() in roots
    info.write_text("invalid", encoding="utf-8")
    assert dropbox.resolve() not in sync_roots(env)
    local = tmp_path / "localappdata"
    local_info = local / "Dropbox/info.json"
    local_info.parent.mkdir(parents=True)
    local_info.write_text('{"business":{"path":"' + dropbox.as_posix() + '"}}', encoding="utf-8")
    env["LOCALAPPDATA"] = str(local)
    assert dropbox.resolve() in sync_roots(env)
    local_info.write_text('["malformed"]', encoding="utf-8")
    assert dropbox.resolve() not in sync_roots(env)
