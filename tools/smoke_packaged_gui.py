"""Create and close the packaged Qt window, with an isolated repo-local profile."""

import argparse
import ctypes
import json
import os
import subprocess
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    profile = root / "build/packaged-gui/user"
    (profile / "Dusty").mkdir(parents=True, exist_ok=True)
    (profile / "Dusty/settings.json").write_text(
        json.dumps({"schema_version": 1, "welcome_seen": True}), encoding="utf-8"
    )
    environment = {**os.environ, "LOCALAPPDATA": str(profile), "QT_QPA_PLATFORM": "windows"}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(
        [str(args.bundle.resolve() / "dusty/dusty.exe")], env=environment, startupinfo=startup
    )
    api = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    api.EnumWindows.argtypes = [callback_type, ctypes.c_void_p]
    api.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    api.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    api.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    windows = []

    @callback_type
    def inspect_window(handle, _):
        pid = ctypes.c_ulong()
        api.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(256)
        api.GetWindowTextW(handle, title, len(title))
        if pid.value == process.pid and title.value == "Dusty":
            windows.append(handle)
        return True

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and process.poll() is None:
            api.EnumWindows(inspect_window, None)
            if windows:
                api.PostMessageW(windows[0], 0x0010, 0, 0)  # WM_CLOSE
                if process.wait(timeout=30) != 0:
                    raise RuntimeError("Packaged GUI failed while closing")
                print("Packaged Qt window created and closed successfully")
                return
            time.sleep(0.1)
        raise RuntimeError("Packaged Qt window was not created")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
