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
    "webbrowser",
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
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update({a.asname or a.name: a.name for a in node.names})
        elif isinstance(node, ast.ImportFrom):
            aliases.update({a.asname or a.name: f"{node.module}.{a.name}" for a in node.names})

    def qualified(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

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
        elif isinstance(node, ast.Call):
            name = qualified(node.func)
            forbidden_call = (
                (name.startswith("subprocess.") and name != "subprocess.list2cmdline")
                or name in {"os.system", "os.startfile", "os.popen", "importlib.import_module"}
                or name.startswith(("os.spawn", "os.exec"))
                or name.endswith((".ShellExecuteW", ".ShellExecuteA"))
            )
            if (
                name.endswith(
                    (
                        ".WinDLL",
                        ".CDLL",
                        ".LoadLibrary",
                        ".LoadLibraryW",
                        ".LoadLibraryExW",
                        ".GetModuleHandleW",
                        ".LoadLibraryA",
                        ".LoadLibraryExA",
                        ".GetModuleHandleA",
                    )
                )
                and node.args
            ):
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    library = (
                        argument.value.replace("\\", "/").rsplit("/", 1)[-1].rstrip(" .").lower()
                    )
                    forbidden_call |= library.removesuffix(".dll") in {
                        "ws2_32",
                        "wsock32",
                        "winhttp",
                        "wininet",
                        "urlmon",
                        "dnsapi",
                        "mswsock",
                        "iphlpapi",
                    }
            if forbidden_call:
                findings.append(f"{label}:{node.lineno}: forbidden network/launch bypass: {name}")
            if not node.args:
                continue
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
