"""Write small, numeric and enumerated diagnostics without user content."""

import logging
import re
from pathlib import Path

_PATH = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\users\\|\\onedrive\\)")
_FIELDS = re.compile(
    r"^(?:job_id=[0-9a-f-]{36}|status=(?:queued|preflight|decoding|transcribing|"
    r"exporting|done|failed|cancelled|skipped)|model=(?:tiny|small|small\.en|medium|"
    r"large-v3-turbo-q8_0)|backend=(?:cpu|vulkan)|(?:decode_sec|process_sec|"
    r"first_progress_sec|timing_[a-z]+_ms)=[0-9.]+|"
    r"network_blocked event=socket\.[a-z_]+|work_cleanup=preserved|"
    r"download_failure step=next_file class=(?:ProcessError|ProcessStartError) "
    r"winerror=0 code=(?:IO|PROTOCOL) exit_code=(?:none|-?[0-9]+))"
    r"(?: (?:job_id=[0-9a-f-]{36}|status=(?:queued|preflight|decoding|transcribing|"
    r"exporting|done|failed|cancelled|skipped)|model=(?:tiny|small|small\.en|medium|"
    r"large-v3-turbo-q8_0)|backend=(?:cpu|vulkan)|(?:decode_sec|process_sec|"
    r"first_progress_sec|timing_[a-z]+_ms)=[0-9.]+))*$"
)


class RotatingFileHandler(logging.FileHandler):
    """Bound local files without importing logging.handlers' socket transports."""

    def __init__(self, filename: Path, *, maxBytes: int, backupCount: int, encoding: str):
        super().__init__(filename, encoding=encoding)
        self.maxBytes, self.backupCount = maxBytes, backupCount

    def emit(self, record: logging.LogRecord) -> None:
        if self.stream:
            self.stream.flush()
        path = Path(self.baseFilename)
        size = len((self.format(record) + self.terminator).encode(self.encoding or "utf-8"))
        if path.exists() and path.stat().st_size + size > self.maxBytes:
            if self.stream:
                self.stream.close()
            for index in range(self.backupCount - 1, 0, -1):
                previous = path.with_name(f"{path.name}.{index}")
                if previous.exists():
                    previous.replace(path.with_name(f"{path.name}.{index + 1}"))
            if self.backupCount:
                path.replace(path.with_name(f"{path.name}.1"))
            self.stream = self._open()
        super().emit(record)


class RedactionFilter(logging.Filter):
    """Drop messages with path shapes or arbitrary user-supplied characters."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not _PATH.search(message) and bool(_FIELDS.fullmatch(message))


def configure_logger(user_dir: Path) -> logging.Logger:
    """Install one bounded, filtered file handler under the local app directory."""
    from dusty.work_area import linked, protected_paths

    logs = user_dir / "logs"
    logger = logging.getLogger("dusty")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    target = logs / "dusty.log"
    protected = protected_paths(user_dir)
    blocked = (
        linked(logs)
        or protected is None
        or any(p.is_relative_to(logs.resolve()) for p in protected)
    )
    for existing in list(logger.handlers):
        if isinstance(existing, logging.NullHandler) or (
            isinstance(existing, RotatingFileHandler)
            and (blocked or Path(existing.baseFilename) != target)
        ):
            logger.removeHandler(existing)
            existing.close()
    if blocked:
        logger.addHandler(logging.NullHandler())
        return logger
    logs.mkdir(parents=True, exist_ok=True)
    if not logger.handlers:
        handler = RotatingFileHandler(target, maxBytes=1024 * 1024, backupCount=4, encoding="utf-8")
        handler.addFilter(RedactionFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    return logger
