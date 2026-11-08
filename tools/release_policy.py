"""Validate release inputs without changing source files or publishing anything."""

import argparse
import json
from typing import Any

from tools.release_version import public_version, versions


def needs_receipts(tag: str) -> bool:
    versions(tag)
    return tag not in {"v0.5.0-m5.1", "v0.5.0-m5.2"}


def validate(tag: str, releases: list[dict[str, Any]]) -> tuple[str, str]:
    """The previous release is the newest published public release; versions only go up."""
    versions(tag)
    current = public_version(tag)
    if current is None:
        raise ValueError("Public release workflow accepts only v1.x.y")
    if tag == "v1.0.0":
        return "", ""
    published = [
        (version, str(r["tagName"]))
        for r in releases
        if r.get("isDraft") is False
        and r.get("isPrerelease") is False
        and (version := public_version(str(r.get("tagName", "")))) is not None
    ]
    if any(version >= current for version, _ in published):
        raise ValueError("A published public release already has this or a higher version")
    if not published:
        raise ValueError("Expected a previous public release, not a draft")
    return max(published)[1], ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("runs", help="JSON from public release list")
    args = parser.parse_args()
    prior, run = validate(args.tag, json.loads(args.runs))
    print(f"previous_tag={prior}\nprevious_run_id={run}")
