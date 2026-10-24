"""Check user-guide UI labels, approved wording and local documentation links."""

import re
from pathlib import Path

from dusty.app import messages as M

ROOT = Path(__file__).resolve().parents[1]


def normalized(text: str) -> str:
    return " ".join(text.split())


def strings(value: object):
    if isinstance(value, str):
        yield normalized(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, tuple | list):
        for item in value:
            yield from strings(item)


def check(root: Path = ROOT) -> list[str]:
    """This checks concrete contracts, not the factual meaning of all prose."""
    findings = []
    labels = set(strings(vars(M)))
    prefixes = {s.split("{", 1)[0].strip() for s in labels if "{" in s}
    user_files = sorted((root / "docs/user").glob("*.md"))
    for path in user_files:
        text = path.read_text(encoding="utf-8")
        for label in re.findall(r"\*\*([^*]+)\*\*", text):
            label = normalized(label)
            windows = path.name == "install.md" and label in {"More info", "Run anyway"}
            if label not in labels and label not in prefixes and not windows:
                findings.append(f"{path.name}: unknown UI label: {label}")
    spec = (root / "docs/pm/SPEC.md").read_text(encoding="utf-8")
    faq = normalized((root / "docs/user/faq.md").read_text(encoding="utf-8"))
    for name in ("Privacy", "Medical/accuracy disclaimer", r"HIPAA \(docs/FAQ only\)"):
        wording = re.search(r"- " + name + r': "([^\"]+)"', spec)
        if wording is None or normalized(wording[1]) not in faq:
            findings.append("faq.md: missing exact approved wording")
    models = (root / "docs/user/models.md").read_text(encoding="utf-8")
    if any(label not in models for label in M.MODEL_NAMES.values()):
        findings.append("models.md: catalog UI labels do not match")
    paths = user_files + [root / "README.md", root / "CONTRIBUTING.md", root / "docs/privacy.md"]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not (path.parent / target).exists():
                findings.append(f"{path.name}: missing local link: {target}")
    return findings


def main() -> int:
    findings = check()
    print("\n".join(findings) if findings else "Documentation consistency check passed")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
