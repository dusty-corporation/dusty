"""Write small, numeric and enumerated diagnostics without user content."""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PATH = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\users\\|\\onedrive\\)")
_FIELDS = re.compile(
    r"^(?:job_id=[0-9a-f-]{36}|status=(?:queued|preflight|decoding|transcribing|"
    r"exporting|done|failed|cancelled|skipped)|model=(?:tiny|small|small\.en|medium|"
    r"large-v3-turbo-q8_0)|backend=(?:cpu|vulkan)|(?:decode_sec|process_sec|"
    r"first_progress_sec|timing_[a-z]+_ms)=[0-9.]+|"
    r"network_blocked event=socket\.[a-z_]+)"
    r"(?: (?:job_id=[0-9a-f-]{36}|status=(?:queued|preflight|decoding|transcribing|"
    r"exporting|done|failed|cancelled|skipped)|model=(?:tiny|small|small\.en|medium|"
    r"large-v3-turbo-q8_0)|backend=(?:cpu|vulkan)|(?:decode_sec|process_sec|"
    r"first_progress_sec|timing_[a-z]+_ms)=[0-9.]+))*$"
)


class RedactionFilter(logging.Filter):
    """Drop messages with path shapes or arbitrary user-supplied characters."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not _PATH.search(message) and bool(_FIELDS.fullmatch(message))


def configure_logger(user_dir: Path) -> logging.Logger:
    """Install one bounded, filtered file handler under the local app directory."""
    logs = user_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dusty")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    target = logs / "dusty.log"
    for existing in list(logger.handlers):
        if isinstance(existing, RotatingFileHandler) and Path(existing.baseFilename) != target:
            logger.removeHandler(existing)
            existing.close()
    if not logger.handlers:
        handler = RotatingFileHandler(
            target, maxBytes=1024 * 1024, backupCount=4, encoding="utf-8"
        )
        handler.addFilter(RedactionFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    return logger
