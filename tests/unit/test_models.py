"""Check the V1 trust anchor against the published model manifest."""

import hashlib
import json
from pathlib import Path

import pytest

from dusty.models import (
    ModelCorrupt,
    ModelMissing,
    ModelRegistry,
    can_translate,
    load_manifest,
    recommend_model,
    slow_warning,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "resources/models.json"
RELEASE = ROOT / "tests/fixtures/models/models-v1.json"


def test_bundled_catalog_matches_pinned_release_manifest() -> None:
    pins = ROOT / "native/versions.toml"
    import tomllib

    expected_digest = tomllib.loads(pins.read_text(encoding="utf-8"))["models_release"][
        "manifest_sha256"
    ]
    assert hashlib.sha256(RELEASE.read_bytes()).hexdigest() == expected_digest
    bundled = json.loads(CATALOG.read_text(encoding="utf-8"))
    published = json.loads(RELEASE.read_text(encoding="utf-8"))
    release_models = {entry["id"]: entry for entry in published["models"]}
    assert len(bundled["models"]) == 5
    assert len(bundled["vad"]) == 1
    for entry in bundled["models"]:
        original = release_models[entry["release_model_id"]]
        for key in (
            "file_name",
            "size_bytes",
            "sha256",
            "url",
            "multilingual",
            "supports_translate",
            "english_only",
            "quantization",
        ):
            assert entry[key] == original[key]
    assert bundled["vad"] == published["vad"]


def test_v1_recommendations_and_task_rules() -> None:
    catalog = load_manifest(CATALOG)
    assert recommend_model(vulkan_ok=True, task="transcribe") == "large-v3-turbo-q8_0"
    assert recommend_model(vulkan_ok=False, task="transcribe") == "small"
    assert recommend_model(vulkan_ok=True, task="translate") == "medium"
    assert not can_translate(catalog.models["large-v3-turbo-q8_0"])
    assert not can_translate(catalog.models["small.en"])
    assert can_translate(catalog.models["medium"])
    assert slow_warning(catalog.models["medium"], "cpu")
    assert slow_warning(catalog.models["large-v3-turbo-q8_0"], "cpu")
    assert slow_warning(catalog.models["medium"], "vulkan") is None
    assert slow_warning(catalog.models["small"], "cpu") is None


def test_registry_rejects_missing_and_corrupt_model(tmp_path: Path) -> None:
    registry = ModelRegistry(load_manifest(CATALOG), tmp_path)
    with pytest.raises(ModelMissing):
        registry.model_path("tiny")
    model_file = tmp_path / registry.manifest.models["tiny"].file_name
    model_file.write_bytes(b"bad")
    with pytest.raises(ModelCorrupt):
        registry.model_path("tiny")


def test_registry_verifies_small_local_fixture(tmp_path: Path) -> None:
    manifest_data = json.loads(CATALOG.read_text(encoding="utf-8"))
    content = b"known model bytes"
    item = next(entry for entry in manifest_data["models"] if entry["id"] == "tiny")
    item["size_bytes"] = len(content)
    item["sha256"] = hashlib.sha256(content).hexdigest()
    local_manifest = tmp_path / "manifest.json"
    local_manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    (tmp_path / item["file_name"]).write_bytes(content)
    registry = ModelRegistry(load_manifest(local_manifest), tmp_path)
    assert registry.model_path("tiny").read_bytes() == content
    (tmp_path / item["file_name"]).write_bytes(b"changed")
    with pytest.raises(ModelCorrupt):
        registry.model_path("tiny")
