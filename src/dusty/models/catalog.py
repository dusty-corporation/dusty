"""Parse the bundled trust anchor and enforce PM-approved V1 model rules."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Backend = Literal["cpu", "vulkan"]
Task = Literal["transcribe", "translate"]
EXPECTED_IDS = frozenset({"large-v3-turbo-q8_0", "small", "medium", "small.en", "tiny"})
SLOW_WARNING = (
    "Without a compatible graphics processor this model will likely take longer "
    "than the recording itself."
)


@dataclass(frozen=True)
class Model:
    id: str
    release_model_id: str
    file_name: str
    size_bytes: int
    sha256: str
    url: str
    multilingual: bool
    supports_translate: bool
    english_only: bool
    speed_cpu: str
    speed_vulkan: str


@dataclass(frozen=True)
class ModelManifest:
    release_tag: str
    models: dict[str, Model]
    vad_file_name: str
    vad_sha256: str
    vad_size_bytes: int


def _valid_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def load_manifest(path: Path) -> ModelManifest:
    """Load exactly the approved V1 catalog from a local bundled manifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("release_tag") != "models-v1":
        raise ValueError("Unsupported model manifest")
    entries = data["models"]
    if len(entries) != len(EXPECTED_IDS) or {item["id"] for item in entries} != EXPECTED_IDS:
        raise ValueError("Model catalog does not match V1 approval")
    models: dict[str, Model] = {}
    for item in entries:
        speed = item["speed_class"]
        if any(value not in {"fast", "slow"} for value in speed.values()):
            raise ValueError("Invalid model speed class")
        if not _valid_hash(item["sha256"]) or int(item["size_bytes"]) <= 0:
            raise ValueError("Invalid model size or hash")
        file_name = item["file_name"]
        if Path(file_name).name != file_name:
            raise ValueError("Invalid model file name")
        models[item["id"]] = Model(
            id=item["id"],
            release_model_id=item["release_model_id"],
            file_name=file_name,
            size_bytes=item["size_bytes"],
            sha256=item["sha256"],
            url=item["url"],
            multilingual=item["multilingual"],
            supports_translate=item["supports_translate"],
            english_only=item["english_only"],
            speed_cpu=speed["cpu"],
            speed_vulkan=speed["vulkan"],
        )
    vad = data["vad"]
    if len(vad) != 1 or vad[0]["id"] != "silero-vad" or not _valid_hash(vad[0]["sha256"]):
        raise ValueError("Invalid VAD manifest")
    return ModelManifest(
        release_tag=data["release_tag"],
        models=models,
        vad_file_name=vad[0]["file_name"],
        vad_sha256=vad[0]["sha256"],
        vad_size_bytes=vad[0]["size_bytes"],
    )


def can_translate(model: Model) -> bool:
    return model.supports_translate and not model.english_only


def recommend_model(*, vulkan_ok: bool, task: Task) -> str:
    """Select the approved default, without inferring capability from a filename."""
    if task == "translate":
        return "medium"
    return "large-v3-turbo-q8_0" if vulkan_ok else "small"


def slow_warning(model: Model, backend: Backend) -> str | None:
    speed = model.speed_cpu if backend == "cpu" else model.speed_vulkan
    return SLOW_WARNING if speed == "slow" else None
