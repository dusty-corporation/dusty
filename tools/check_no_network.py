"""Reject networking imports from the offline Dusty application package."""

import ast
import sys
from pathlib import Path

FORBIDDEN = (
    "socket",
    "ssl",
    "http",
    "urllib",
    "ftplib",
    "smtplib",
    "requests",
    "httpx",
    "aiohttp",
    "websocket",
    "dusty_fetch",
    "PySide6.QtNetwork",
    "PySide6.QtWebEngine",
)
FORBIDDEN_QT = ("QtNetwork", "QtWebEngine")


def is_forbidden(name: str) -> bool:
    return any(
        name == item or name.startswith(item + ".") for item in FORBIDDEN
    ) or name.startswith("websocket")


def scan_source(source: str, label: str) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(source, filename=label)
    except SyntaxError as exc:
        return [f"{label}:{exc.lineno}: invalid Python syntax"]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_node: ast.Import | ast.ImportFrom = node
            if isinstance(import_node, ast.Import):
                names = [alias.name for alias in import_node.names]
            else:
                module = import_node.module or ""
                names = [module] + [f"{module}.{alias.name}" for alias in import_node.names]
                if module == "PySide6":
                    names += [
                        alias.name for alias in import_node.names if alias.name in FORBIDDEN_QT
                    ]
            for name in names:
                if is_forbidden(name) or name in FORBIDDEN_QT:
                    findings.append(
                        f"{label}:{import_node.lineno}: forbidden networking import: {name}"
                    )
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            dynamic_import = (
                isinstance(func, ast.Name)
                and func.id == "__import__"
                or isinstance(func, ast.Attribute)
                and func.attr == "import_module"
                and isinstance(func.value, ast.Name)
                and func.value.id == "importlib"
            )
            if dynamic_import and isinstance(node.args[0], ast.Constant):
                import_name = node.args[0].value
                if isinstance(import_name, str) and is_forbidden(import_name):
                    findings.append(
                        f"{label}:{node.lineno}: forbidden networking import: {import_name}"
                    )
    return findings


def check(root: Path) -> list[str]:
    app = root / "src" / "dusty"
    if not app.is_dir():
        return ["src/dusty is missing"]
    findings: list[str] = []
    for path in sorted(app.rglob("*.py")):
        findings += scan_source(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix())
    return findings


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    findings = check(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Network import check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
