"""Merge small model fragments into the M1 release manifest."""

import json
from pathlib import Path


def main() -> None:
    models = []
    vad = []
    for path in sorted(Path("build/fragments").rglob("fragment.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "model" in data:
            models.append(data["model"])
        if "vad" in data:
            vad.append(data["vad"])
    if len(models) != 10 or len(vad) != 1:
        raise ValueError("Incomplete model manifest fragments")
    manifest = {"schema_version": 1, "release_tag": "models-v1", "models": models, "vad": vad}
    Path("models.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
