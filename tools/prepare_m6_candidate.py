"""Stage exact native candidates in a disposable M6 validation checkout only."""

import hashlib
import json
import os
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from tools.fetch_dev_binaries import extract_flat_zip

ROOT = Path(__file__).resolve().parents[1]


def prepare(source: Path, root: Path = ROOT) -> None:
    spec = json.loads((root / "native/m6-engine-candidate.json").read_text(encoding="utf-8"))
    manifest = root / "native/windows-utf8.manifest"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != spec["manifest_sha256"]:
        raise ValueError("Candidate manifest changed")
    archives = {}
    for backend in ("cpu", "vulkan"):
        expected = spec["backends"][backend]
        folder = source / backend
        names = set(expected["members"])
        allowed = names | {name + ".imports.txt" for name in names}
        if {p.name for p in folder.iterdir()} - allowed:
            raise ValueError("Unexpected candidate member")
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in sorted(names):
                if Path(name).name != name:
                    raise ValueError("Unsafe candidate member")
                path = folder / name
                if path.is_symlink() or path.is_junction():
                    raise ValueError("Linked candidate member")
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != expected["members"][name]:
                    raise ValueError("Candidate bytes changed")
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.external_attr = 0o600 << 16
                entry.create_system = 3
                archive.writestr(entry, data)
        data = buffer.getvalue()
        if (
            len(data) != expected["archive_bytes"]
            or hashlib.sha256(data).hexdigest() != expected["archive_sha256"]
        ):
            raise ValueError("Candidate archive changed")
        archives[backend] = data
    # Validate every input before changing any disposable-checkout input.
    pins_path = root / "native/versions.toml"
    pins = pins_path.read_text(encoding="utf-8")
    for backend, data in archives.items():
        target = root / "build/downloads" / f"whisper-{backend}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        extract_flat_zip(target, root / "build/bin" / backend)
        key = f"whisper_{backend}_zip_sha256"
        pins, count = re.subn(
            key + r' = "[0-9a-f]{64}"',
            f'{key} = "{spec["backends"][backend]["archive_sha256"]}"',
            pins,
        )
        if count != 1:
            raise ValueError("Candidate pin field missing")
    pins = pins.replace('tag = "engine-v2"', 'tag = "m6-validation-only"')
    pins = re.sub(r"native_run_id = \d+", f"native_run_id = {spec['run_id']}", pins)
    pins = re.sub(
        r'source_commit = "[0-9a-f]{40}"', f'source_commit = "{spec["source_commit"]}"', pins
    )
    pins_path.write_text(pins, encoding="utf-8", newline="\n")
    (root / "build/m6-candidate-validation.json").write_text(
        json.dumps(
            {
                "validation_only": True,
                "run_id": spec["run_id"],
                "source_commit": spec["source_commit"],
            }
        ),
        encoding="utf-8",
    )
    print("M6 validation-only candidate staged; committed production pins are not activated")


if __name__ == "__main__":
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REF_NAME") != "m6-hardening"
    ):
        raise SystemExit("Candidate staging is restricted to disposable M6 branch CI")
    prepare(Path(sys.argv[1]))
