"""Verify model files locally before their first use in each app session."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from .catalog import ModelManifest


class ModelMissing(Exception):
    """A required local model file is absent."""


class ModelCorrupt(Exception):
    """A local model file does not match the bundled trust anchor."""


@dataclass
class ModelRegistry:
    manifest: ModelManifest
    directory: Path
    _verified: dict[Path, tuple[int, int]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def invalidate(self, *, file_name: str | None = None) -> None:
        """Forget one catalog file, or all hashes, before an explicit recheck.

        Workers share this registry. Invalidation and verification serialize so
        a verification cannot repopulate a cache entry after invalidation.
        """
        with self._lock:
            if file_name is None:
                self._verified.clear()
            else:
                names = {model.file_name for model in self.manifest.models.values()}
                names.add(self.manifest.vad_file_name)
                if file_name not in names:
                    raise ValueError("Unknown catalog file")
                self._verified.pop(self.directory / file_name, None)

    def _verify(self, file_name: str, expected_size: int, expected_hash: str) -> Path:
        with self._lock:
            return self._verify_locked(file_name, expected_size, expected_hash)

    def _verify_locked(self, file_name: str, expected_size: int, expected_hash: str) -> Path:
        path = self.directory / file_name
        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise ModelMissing("Model file is missing") from exc
        if stat.st_size != expected_size:
            raise ModelCorrupt("Model file size does not match manifest")
        identity = (stat.st_size, stat.st_mtime_ns)
        if self._verified.get(path) != identity:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected_hash:
                raise ModelCorrupt("Model file hash does not match manifest")
            self._verified[path] = identity
        return path

    def model_path(self, model_id: str) -> Path:
        model = self.manifest.models[model_id]
        return self._verify(model.file_name, model.size_bytes, model.sha256)

    def vad_path(self) -> Path:
        return self._verify(
            self.manifest.vad_file_name,
            self.manifest.vad_size_bytes,
            self.manifest.vad_sha256,
        )
