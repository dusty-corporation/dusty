"""Validate release inputs without changing source files or publishing anything."""

import argparse
import json
from typing import Any

from tools.release_version import versions


def needs_receipts(tag: str) -> bool:
    versions(tag)
    return tag not in {"v0.5.0-m5.1", "v0.5.0-m5.2"}


def validate(tag: str, releases: list[dict[str, Any]]) -> tuple[str, str]:
    versions(tag)
    if not tag.startswith("v1.0."):
        raise ValueError("Public release workflow accepts only v1.0.x")
    if tag == "v1.0.0":
        return "", ""
    previous = f"v1.0.{int(tag.rsplit('.', 1)[1]) - 1}"
    eligible = [
        r
        for r in releases
        if r.get("tagName") == previous
        and r.get("isDraft") is False
        and r.get("isPrerelease") is False
    ]
    if len(eligible) != 1:
        raise ValueError("Expected the immediately previous public release, not a draft")
    return previous, ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("runs", help="JSON from public release list")
    args = parser.parse_args()
    prior, run = validate(args.tag, json.loads(args.runs))
    print(f"previous_tag={prior}\nprevious_run_id={run}")
