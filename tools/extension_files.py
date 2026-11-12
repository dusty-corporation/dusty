"""Resource files of installed extensions, for the app builds (docs/dev/extensions.md)."""

from __future__ import annotations

import json
from pathlib import Path


def extension_catalogs() -> tuple[str, ...]:
    """Catalog file names of the extension models, in the resources folder."""
    from dusty import extensions

    return tuple(model.catalog for model in extensions.loaded().models)


def extension_model_files(resources: Path) -> set[str]:
    """Model file names the extension catalogs list; these must never be bundled."""
    names: set[str] = set()
    for catalog in extension_catalogs():
        data = json.loads((resources / catalog).read_text(encoding="utf-8"))
        names.update(item["file_name"] for item in data["models"])
    return names
