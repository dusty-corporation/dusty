"""Offline model catalog, selection rules, and local integrity checks."""

from .catalog import (
    Model,
    ModelManifest,
    can_translate,
    load_manifest,
    recommend_model,
    slow_warning,
)
from .partials import cleanup_stale_partials
from .registry import ModelCorrupt, ModelMissing, ModelRegistry

__all__ = [
    "Model",
    "ModelCorrupt",
    "ModelManifest",
    "ModelMissing",
    "ModelRegistry",
    "can_translate",
    "cleanup_stale_partials",
    "load_manifest",
    "recommend_model",
    "slow_warning",
]
