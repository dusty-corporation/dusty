"""Scan captured pipeline output with the same literal model-host guard as CI."""

import sys
from pathlib import Path

from tools.check_no_huggingface import PATTERN


def main() -> None:
    for name in sys.argv[1:]:
        for number, line in enumerate(Path(name).read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                raise ValueError(f"Prohibited model-host reference in CI log at line {number}")
    print("Captured pipeline log scan passed")


if __name__ == "__main__":
    main()
