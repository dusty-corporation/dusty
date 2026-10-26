"""Collect network-guard coverage in its required isolated interpreter."""

import json
import sys
import trace
from pathlib import Path


def exercise() -> None:
    from dusty.privacy.network_guard import BLOCKED_EVENTS, NetworkBlockedError, install_guard

    install_guard()
    install_guard()
    events: list[tuple[str, tuple[object, ...]]] = [
        (event, ("redacted",)) for event in BLOCKED_EVENTS
    ]
    events += [
        ("ctypes.dlopen", ("WS2_32.dll",)),
        ("os.startfile", ("https://example.invalid",)),
        ("os.startfile", (None,)),
        ("webbrowser.open", ("redacted",)),
        ("subprocess.Popen", ("redacted",)),
        ("os.system", ("redacted",)),
    ]
    for event, arguments in events:
        try:
            sys.audit(event, *arguments)
        except NetworkBlockedError:
            pass
        else:
            raise AssertionError(event)
    sys.audit("os.startfile", str(Path(__file__).resolve().parent))
    sys.audit("ctypes.dlopen", None)


def main() -> None:
    tracer = trace.Trace(count=True, trace=False)
    tracer.runfunc(exercise)
    target = Path(__file__).resolve().parents[1] / "src/dusty/privacy/network_guard.py"
    hit = sorted(
        line
        for (filename, line), count in tracer.results().counts.items()
        if Path(filename).resolve() == target and count > 0
    )
    print(json.dumps(hit))


if __name__ == "__main__":
    main()
