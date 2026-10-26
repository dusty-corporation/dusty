"""Compare pinned model URLs against the pinned upstream source tree."""

import ast
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

NAMES = ("tiny", "base", "small", "small.en", "medium", "large-v3-turbo", "large-v3")


def main() -> None:
    source = Path(sys.argv[1]) / "whisper" / "__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    maps = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_MODELS" for target in node.targets)
    ]
    if len(maps) != 1:
        raise ValueError("Expected exactly one upstream model URL map")
    actual = {}
    for name in NAMES:
        url = maps[0][name]
        parts = urlparse(url)
        sha = parts.path.split("/")[-2]
        if parts.scheme != "https" or parts.hostname != "openaipublic.azureedge.net":
            raise ValueError("Unexpected model source host")
        if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            raise ValueError("Upstream URL lacks embedded SHA-256")
        actual[name] = {"url": url, "sha256": sha}
    expected = json.loads(Path("modelpipeline/model_sources.json").read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("Pinned model source map differs from upstream")
    print("Pinned model source map verified")


if __name__ == "__main__":
    main()
