"""Remove only byte-identical, obsolete copies of Dusty's own license texts."""

import hashlib
import json
import re
from pathlib import Path

from dusty.runtime_paths import RuntimePaths
from dusty.work_area import linked, protected_paths

RECEIPT = ".dusty-license-cleanup.json"


def tidy_license_copies(paths: RuntimePaths, install: Path) -> bool:
    """Preflight all old version folders; unknown/changed/linked content blocks cleanup."""
    root = install / "licenses/dusty"
    if not root.exists():
        return True
    protected = protected_paths(paths.user_dir)
    if linked(root) or protected is None:
        return False
    source = paths.resources_dir.parent / "licenses/dusty"
    current = list(source.glob("dusty-*.dist-info"))
    if len(current) != 1 or linked(current[0]):
        return False
    names = ("LICENSE", "NOTICE")
    expected = {
        name: hashlib.sha256((current[0] / "licenses" / name).read_bytes()).hexdigest()
        for name in names
    }
    obsolete = []
    for folder in root.iterdir():
        if folder.name == current[0].name:
            continue
        if (
            not re.fullmatch(r"dusty-\d+\.\d+\.\d+(?:\.dev\d+)?\.dist-info", folder.name)
            or linked(folder)
            or not folder.is_dir()
            or any(
                folder.resolve().is_relative_to(p) or p.is_relative_to(folder.resolve())
                for p in protected
            )
        ):
            return False
        children = {p.name for p in folder.iterdir()}
        if not children:
            continue  # Preserve an empty unmarked folder; never guess its ownership.
        marker = folder / RECEIPT
        payload = json.dumps(
            {
                "schema": 1,
                "purpose": "obsolete-dusty-license",
                "directory": folder.name,
                "files": expected,
            }
        ).encode("ascii")
        resumed = RECEIPT in children
        if resumed:
            if linked(marker) or marker.read_bytes() != payload:
                return False
            if children - {"licenses", RECEIPT}:
                return False
        elif children != {"licenses"}:
            return False
        texts = folder / "licenses"
        if linked(texts):
            return False
        if not texts.exists() and resumed:
            present = set()
        elif not texts.is_dir():
            return False
        else:
            present = {p.name for p in texts.iterdir()}
        if present - set(names) or (not resumed and present != set(names)):
            return False
        for name in present:
            file = texts / name
            if (
                linked(file)
                or not file.is_file()
                or any(
                    file.resolve().is_relative_to(p) or p.is_relative_to(file.resolve())
                    for p in protected
                )
                or hashlib.sha256(file.read_bytes()).hexdigest() != expected[name]
            ):
                return False
        obsolete.append((texts, present, marker, payload, resumed))
    for texts, present, marker, payload, resumed in obsolete:
        if not resumed:
            with marker.open("xb") as stream:
                stream.write(payload)
        for name in sorted(present):
            file = texts / name
            # Recheck immediately before removal; never adopt a changed file.
            if (
                linked(file)
                or marker.read_bytes() != payload
                or hashlib.sha256(file.read_bytes()).hexdigest() != expected[name]
            ):
                return False
            file.unlink()
        if texts.exists():
            texts.rmdir()
        if (
            linked(marker)
            or marker.read_bytes() != payload
            or {p.name for p in texts.parent.iterdir()} != {RECEIPT}
        ):
            return False
        marker.unlink()
        texts.parent.rmdir()
    return True
