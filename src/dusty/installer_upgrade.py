"""Remove only byte-identical, obsolete copies of Dusty's own license texts."""

import hashlib
import re
from pathlib import Path

from dusty.runtime_paths import RuntimePaths
from dusty.work_area import linked, protected_paths


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
        name: hashlib.sha256((current[0] / "licenses" / name).read_bytes()).digest()
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
            or {p.name for p in folder.iterdir()} != {"licenses"}
        ):
            return False
        texts = folder / "licenses"
        if linked(texts) or not texts.is_dir() or {p.name for p in texts.iterdir()} != set(names):
            return False
        for name in names:
            file = texts / name
            if (
                linked(file)
                or not file.is_file()
                or any(
                    file.resolve().is_relative_to(p) or p.is_relative_to(file.resolve())
                    for p in protected
                )
                or hashlib.sha256(file.read_bytes()).digest() != expected[name]
            ):
                return False
        obsolete.append(texts)
    for texts in obsolete:
        for name in names:
            file = texts / name
            # Recheck immediately before removal; never adopt a changed file.
            if linked(file) or hashlib.sha256(file.read_bytes()).digest() != expected[name]:
                return False
            file.unlink()
        texts.rmdir()
        texts.parent.rmdir()
    return True
