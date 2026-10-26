"""Catch literal prohibited model-host references in build and runtime inputs.

This guards against accidental dependencies; it does not detect obfuscated references.
"""

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    "|".join((r"(?<!no_)hugging" + "face", "hf" + "_hub", "hf" + r"\.co", "HF" + "_TOKEN")),
    re.I,
)
ROOT_FILES = ("pyproject.toml", "uv.lock")
SOURCE_DIRS = (
    "src",
    "tools",
    "tests",
    ".github",
    "native",
    "modelpipeline",
    "installer",
    "packaging",
)
SCANNED_EXTENSIONS = {".py", ".toml", ".yml", ".yaml", ".json", ".ps1", ".sh", ".iss", ".spec"}


def check(root: Path) -> list[str]:
    paths = [root / name for name in ROOT_FILES]
    for name in SOURCE_DIRS:
        directory = root / name
        if directory.is_dir():
            paths.extend(path for path in directory.rglob("*") if path.suffix in SCANNED_EXTENSIONS)
    findings: list[str] = []
    for path in sorted(paths):
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                findings.append(
                    f"{path.relative_to(root).as_posix()}:{number}: prohibited model-host reference"
                )
    return findings


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    findings = check(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Model-host exclusion check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
