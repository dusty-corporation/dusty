"""CI-only shortcut audit using Unicode IShellLinkW, never link resolution."""

import argparse
import ctypes as C
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path


class Guid(C.Structure):
    _fields_ = [("data", C.c_ubyte * 16)]

    def __init__(self, value):
        super().__init__((C.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le))


def method(pointer, index, *types):
    table = C.cast(pointer, C.POINTER(C.POINTER(C.c_void_p))).contents
    return C.WINFUNCTYPE(C.c_int32, C.c_void_p, *types)(table[index])


def checked(result):
    if result < 0:
        raise OSError("Windows Unicode shortcut API failed")


@contextmanager
def shell_link():
    ole = C.WinDLL("ole32")
    ole.CoInitializeEx.argtypes = [C.c_void_p, C.c_ulong]
    ole.CoInitializeEx.restype = C.c_int32
    # RPC_E_CHANGED_MODE means the caller already owns another COM apartment.
    initialized = ole.CoInitializeEx(None, 2)
    if initialized not in (0, 1, -2147417850):
        checked(initialized)
    link, persist = C.c_void_p(), C.c_void_p()
    try:
        ole.CoCreateInstance.argtypes = [
            C.POINTER(Guid),
            C.c_void_p,
            C.c_ulong,
            C.POINTER(Guid),
            C.POINTER(C.c_void_p),
        ]
        checked(
            ole.CoCreateInstance(
                C.byref(Guid("00021401-0000-0000-c000-000000000046")),
                None,
                1,
                C.byref(Guid("000214f9-0000-0000-c000-000000000046")),
                C.byref(link),
            )
        )
        checked(
            method(link, 0, C.POINTER(Guid), C.POINTER(C.c_void_p))(
                link, C.byref(Guid("0000010b-0000-0000-c000-000000000046")), C.byref(persist)
            )
        )
        yield link, persist
    finally:
        for pointer in (persist, link):
            if pointer:
                method(pointer, 2)(pointer)
        if initialized in (0, 1):
            ole.CoUninitialize()


def read_shortcut(file: Path) -> tuple[str, str]:
    """GetPath(SLGP_RAWPATH) does not Resolve, repair, launch or save the link."""
    with shell_link() as (link, persist):
        checked(method(persist, 5, C.c_wchar_p, C.c_ulong)(persist, str(file), 0))
        target, arguments = C.create_unicode_buffer(32768), C.create_unicode_buffer(32768)
        checked(
            method(link, 3, C.c_wchar_p, C.c_int, C.c_void_p, C.c_ulong)(
                link, target, len(target), None, 4
            )
        )
        checked(method(link, 10, C.c_wchar_p, C.c_int)(link, arguments, len(arguments)))
        if len(target.value) == len(target) - 1 or len(arguments.value) == len(arguments) - 1:
            raise ValueError("Shortcut audit refuses potentially truncated fields")
        return target.value, arguments.value


def audit(install: Path, roots: list[Path]) -> list[dict[str, str]]:
    checked_links = []
    install = Path(os.path.abspath(install))
    for root in roots:
        for file in root.rglob("*.lnk"):
            target, arguments = read_shortcut(file)
            if not target:
                if file.name.casefold() == "dusty.lnk":
                    raise ValueError("Dusty shortcut has no readable filesystem target")
                continue
            # No Resolve call or access to remote/unknown link targets.
            target_path = Path(os.path.abspath(target))
            if not target_path.is_relative_to(install):
                continue
            if (
                target_path.name.lower().startswith("unins")
                and target_path.suffix.lower() == ".exe"
            ):
                if arguments != "/SILENT /DUSTYCONFIRM=yes":
                    raise ValueError("Shortcut launches a bare uninstaller")
            checked_links.append(
                {"target": str(target_path.relative_to(install)), "arguments": arguments}
            )
    if sum(link["target"] == str(Path("dusty/dusty.exe")) for link in checked_links) != 2:
        raise ValueError("Expected Start Menu and default Desktop app shortcuts")
    return checked_links


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Installed shortcut audit is disposable CI only")
    parser = argparse.ArgumentParser()
    parser.add_argument("install", type=Path)
    parser.add_argument("roots", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(audit(args.install, args.roots)))


if __name__ == "__main__":
    main()
