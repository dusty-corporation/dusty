"""Parse the bundled trust anchor and enforce PM-approved V1 model rules."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Backend = Literal["cpu", "vulkan"]
Task = Literal["transcribe", "translate"]
EXPECTED_IDS = frozenset({"large-v3-turbo-q8_0", "small", "medium", "small.en", "tiny"})
# Files of extension models (docs/dev/extensions.md). Their catalog files say
# "kind": "extension", and dusty_fetch accepts this name only from those.
EXTRA_FILE_NAME = r"dusty-[a-z0-9._-]+\.onnx"
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
    # Extension models by id, each from its own catalog file.
    extra: dict[str, "ExtraFile"] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtraFile:
    file_name: str
    size_bytes: int
    sha256: str


def _valid_hash(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def load_extra(path: Path, model_id: str) -> ExtraFile:
    """One extension model from its catalog file next to the bundled manifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    extension = data.get("schema_version") == 1 and data.get("kind") == "extension"
    entries = data.get("models") if extension else None
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError("Invalid extension model catalog")
    entry = entries[0]
    if (
        entry.get("id") != model_id
        or not isinstance(entry.get("sha256"), str)
        or not _valid_hash(entry["sha256"])
        or not isinstance(entry.get("file_name"), str)
        or not re.fullmatch(EXTRA_FILE_NAME, entry["file_name"])
        or type(entry.get("size_bytes")) is not int
        or entry["size_bytes"] <= 0
    ):
        raise ValueError("Invalid extension model catalog")
    return ExtraFile(entry["file_name"], entry["size_bytes"], entry["sha256"])


def load_manifest(path: Path) -> ModelManifest:
    """Load exactly the approved V1 catalog from a local bundled manifest.

    Models of installed extensions come from their own catalog files in the
    same folder; without extensions the manifest is exactly the V1 catalog. A
    catalog file that is not there leaves its model out; one that is there must
    be valid.
    """
    from dusty import extensions

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
    extra = {
        model.id: load_extra(path.parent / model.catalog, model.id)
        for model in extensions.active().models
        if (path.parent / model.catalog).is_file()
    }
    if set(extra) & (set(models) | {"silero-vad"}):
        raise ValueError("An extension model reuses a model id")
    return ModelManifest(
        release_tag=data["release_tag"],
        models=models,
        vad_file_name=vad[0]["file_name"],
        vad_sha256=vad[0]["sha256"],
        vad_size_bytes=vad[0]["size_bytes"],
        extra=extra,
    )


def can_translate(model: Model) -> bool:
    return model.supports_translate and not model.english_only


def recommend_model(
    *, task: Task, gpu_ok: bool | None = None, vulkan_ok: bool | None = None
) -> str:
    """Select the approved default, without inferring capability from a filename.

    gpu_ok means the platform GPU probe passed and the GPU is not switched off:
    Vulkan on Windows, Metal on Mac. vulkan_ok is the older name for the same fact.
    The rule is the same on both platforms. With a working GPU, Large v3 Turbo
    transcribes with the best catalog quality; measured with Metal on an M2 it took
    8.4 s for a 120 s clip (Small 5.0 s, Medium 12.4 s). Without a GPU, Small is
    the faster processor choice (11.5 s against 32 s for Turbo on that M2 when
    idle). Turbo cannot translate, so Medium is the translation choice everywhere.
    Every catalog model lists the same 8 GB memory minimum, which supported Apple
    silicon Macs meet, so memory does not change the choice; the Windows installer
    only shows a low-memory notice.
    """
    if (gpu_ok is None) == (vulkan_ok is None):
        raise TypeError("Pass exactly one of gpu_ok or vulkan_ok")
    working_gpu = bool(gpu_ok if gpu_ok is not None else vulkan_ok)
    if task == "translate":
        return "medium"
    return "large-v3-turbo-q8_0" if working_gpu else "small"


def gpu_presumed(platform: str | None = None, machine: str | None = None) -> bool:
    """Whether a working GPU may be assumed before any model allows a real probe.

    Dusty for Mac supports only Apple silicon, and every Apple silicon Mac has a
    Metal GPU, so a new Mac user is recommended the GPU model before the first
    download. The real probe result replaces this as soon as a model exists.
    Windows never presumes a GPU.
    """
    import os
    import sys

    selected = sys.platform if platform is None else platform
    arch = machine
    # os.uname exists only on POSIX hosts. The host check comes first so that
    # type checkers on Windows treat this branch as macOS only.
    if sys.platform != "win32" and arch is None and selected == "darwin":
        arch = os.uname().machine
    return selected == "darwin" and arch == "arm64"


def slow_warning(model: Model, backend: Backend) -> str | None:
    speed = model.speed_cpu if backend == "cpu" else model.speed_vulkan
    return SLOW_WARNING if speed == "slow" else None
