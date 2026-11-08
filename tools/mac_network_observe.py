"""Observe attempted network operations by Dusty processing on macOS (P31).

    PYTHONPATH=src python tools/mac_network_observe.py --out build/netobs/run-1 \
        --bin-dir build/bin --models-dir build/models-dev --app build/mac-app/Dusty.app

Development and acceptance tool only. It needs no sudo and changes no system
setting. Nothing here reaches beyond the loopback interface: the positive
controls connect to 127.0.0.1 port 9 (nothing listens, so the kernel refuses)
and resolve "localhost".

Three independent layers, because each one sees attempts the others miss:

1. Kernel layer. Every scenario runs under sandbox-exec with a profile that
   allows everything except network operations, and a denied network operation
   sends SIGKILL to the process that tried it. The sandbox is inherited by
   every descendant (lifeline, ffmpeg, ffprobe, whisper-cli). It acts on the
   system call, so it also sees code that bypasses libc. A run that completes
   with valid outputs therefore proves that no process in the tree made a
   sandbox-visible network attempt (connect, bind, sendto, name resolution
   through mDNSResponder, local socket connects) and that processing needs no
   network. The unified log is not used as a detector: on this macOS version
   sandbox violations of ad hoc signed programs are not reported there (the
   calibration step records this).
2. libc layer. A DYLD_INSERT_LIBRARIES interposer records socket, connect,
   connectx, bind, listen, sendto, sendmsg, getaddrinfo, getnameinfo,
   gethostbyname, gethostbyname2, gethostbyaddr, DNSServiceGetAddrInfo and
   DNSServiceQueryRecord with the process ID and program name, before calling
   the real function. It also writes one "load" record per process, so a
   process without a load record counts as not observed, never as clean.
   Dusty gives native children a minimal environment, so for observation only
   this harness wraps dusty.platform.mac_process.child_environment in its own
   process to add the two interposer variables. Program, arguments, lifeline,
   posix_spawn and everything else are the product code paths, unchanged.
   Hardened runtime programs ignore DYLD variables, so the signed Dusty.app is
   observed by layers 1 and 3 only; its natives are the same bytes as the
   staged dev copies apart from the signature (check_macos_bundle verifies that).
3. Crash report layer. A process the sandbox kills usually gets a crash report
   in ~/Library/Logs/DiagnosticReports whose termination namespace is SANDBOX,
   naming the process, also for the hardened app and its children. Every such
   report written during a scenario (the calibration control excepted) counts
   as an attempt by the named process. ReportCrash throttles repeated reports
   for one program, so a missing report proves nothing; the primary signal is
   that a killed process fails the run. Auto runs must also show that the GPU
   probe passed and Metal transcribed, because a killed probe would otherwise
   fall back to the CPU and still finish.
4. Python layer. A recording audit hook, added before Dusty's own guard,
   writes the names of socket, urllib, http.client and webbrowser audit events
   in the app process. Dusty's guard log line (network_blocked) is collected
   from the isolated data folder for the packaged app as well.

Calibration (positive and negative controls) runs first and the run fails if
any control does not behave as expected. Results go to <out>/results.json and
<out>/summary.md.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

try:
    from tools.mac_privacy_canary import GUI_DRIVER
except ImportError:  # run as a script: tools/ itself is on sys.path
    from mac_privacy_canary import GUI_DRIVER  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)  # the venv interpreter, so PySide6 is importable
TOOL_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
# Every network operation is denied. IP traffic (any address, loopback included),
# IP bind and accept, and name resolution through mDNSResponder also send SIGKILL
# to the process that tried, so a run cannot silently continue past an attempt.
# A bare "(deny network* (with send-signal SIGKILL))" is not usable: on macOS
# 26.2 it also kills on link(2) of a regular file (Dusty publishes outputs and
# state with hard links) although the link itself is allowed; calibration keeps
# a hard link control to prove this profile does not.
KILL_PROFILE = (
    "(version 1)\n"
    "(allow default)\n"
    "(deny network*)\n"
    "(deny network-outbound (remote ip) (with send-signal SIGKILL))\n"
    '(deny network-outbound (remote unix-socket (path-literal "/private/var/run/mDNSResponder"))'
    " (with send-signal SIGKILL))\n"
    "(deny network-bind (local ip) (with send-signal SIGKILL))\n"
    "(deny network-inbound (local ip) (with send-signal SIGKILL))\n"
)
OBSERVE_ENV = ("DUSTY_NETOBS_LOG",)
FIXTURE = ROOT / "tests/fixtures/audio/formats/jfk.m4a"
FORMATS = ("txt", "srt", "vtt", "json", "docx")
NETWORK_FAMILIES = {2: "AF_INET", 30: "AF_INET6"}
RESOLVER_CALLS = frozenset(
    {
        "getaddrinfo",
        "getnameinfo",
        "gethostbyname",
        "gethostbyname2",
        "gethostbyaddr",
        "DNSServiceGetAddrInfo",
        "DNSServiceQueryRecord",
    }
)
SOCKET_CALLS = frozenset({"socket", "connect", "connectx", "bind", "listen", "sendto", "sendmsg"})
PYTHON_NETWORK_PREFIXES: tuple[str, ...] = (
    "socket.",
    "urllib.",
    "http.client.",
    "webbrowser.",
    "ftplib.",
    "smtplib.",
    "imaplib.",
    "poplib.",
    "nntplib.",
    "telnetlib.",
)

INTERPOSER_C = r"""
#include <arpa/inet.h>
#include <dns_sd.h>
#include <errno.h>
#include <fcntl.h>
#include <mach-o/dyld.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define INTERPOSE(replacement, original) \
    __attribute__((used)) static struct { const void *r; const void *o; } \
    interpose_##original __attribute__((section("__DATA,__interpose"))) = \
    {(const void *)(unsigned long)&replacement, (const void *)(unsigned long)&original};

static void clean(const char *in, char *out, size_t size) {
    size_t i = 0;
    for (; in && in[i] && i + 1 < size; i++) {
        char c = in[i];
        int ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                 || c == '.' || c == ':' || c == '-' || c == '_' || c == '/' || c == '%';
        out[i] = ok ? c : '?';
    }
    out[i] = 0;
}

static void folder_and_name(char *out, size_t size) {
    char path[1024];
    uint32_t length = sizeof path;
    out[0] = 0;
    if (_NSGetExecutablePath(path, &length) != 0) return;
    char *name = strrchr(path, '/');
    if (!name) { clean(path, out, size); return; }
    *name = 0;
    char *folder = strrchr(path, '/');
    char joined[512];
    snprintf(joined, sizeof joined, "%s/%s", folder ? folder + 1 : path, name + 1);
    clean(joined, out, size);
}

static void record(const char *call, int family, const char *detail) {
    int saved = errno;
    const char *log = getenv("DUSTY_NETOBS_LOG");
    if (log && *log) {
        char program[300], safe[300], line[1024];
        folder_and_name(program, sizeof program);
        clean(detail, safe, sizeof safe);
        int n = snprintf(line, sizeof line,
            "{\"pid\":%d,\"ppid\":%d,\"program\":\"%s\",\"call\":\"%s\","
            "\"family\":%d,\"detail\":\"%s\"}\n",
            (int)getpid(), (int)getppid(), program, call, family, safe);
        int fd = open(log, O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0600);
        if (fd >= 0) {
            size_t size = n < (int)sizeof line ? (size_t)n : sizeof line - 1;
            if (n > 0) (void)write(fd, line, size);
            close(fd);
        }
    }
    errno = saved;
}

static void describe(const struct sockaddr *address, char *out, size_t size, int *family) {
    out[0] = 0;
    *family = -1;
    if (!address) return;
    *family = address->sa_family;
    if (address->sa_family == AF_INET) {
        const struct sockaddr_in *in4 = (const struct sockaddr_in *)address;
        char text[INET_ADDRSTRLEN] = "";
        inet_ntop(AF_INET, &in4->sin_addr, text, sizeof text);
        snprintf(out, size, "%s:%d", text, ntohs(in4->sin_port));
    } else if (address->sa_family == AF_INET6) {
        const struct sockaddr_in6 *in6 = (const struct sockaddr_in6 *)address;
        char text[INET6_ADDRSTRLEN] = "";
        inet_ntop(AF_INET6, &in6->sin6_addr, text, sizeof text);
        snprintf(out, size, "%s:%d", text, ntohs(in6->sin6_port));
    } else if (address->sa_family == AF_UNIX) {
        snprintf(out, size, "unix:%s", ((const struct sockaddr_un *)address)->sun_path);
    }
}

__attribute__((constructor)) static void loaded(void) { record("load", 0, ""); }

static int my_socket(int domain, int type, int protocol) {
    record("socket", domain, "");
    return socket(domain, type, protocol);
}
static int my_connect(int fd, const struct sockaddr *address, socklen_t length) {
    char text[256]; int family;
    describe(address, text, sizeof text, &family);
    record("connect", family, text);
    return connect(fd, address, length);
}
static int my_connectx(int fd, const sa_endpoints_t *endpoints, sae_associd_t associd,
                       unsigned int flags, const struct iovec *iov, unsigned int iovcnt,
                       size_t *len, sae_connid_t *connid) {
    char text[256] = ""; int family = -1;
    if (endpoints) describe(endpoints->sae_dstaddr, text, sizeof text, &family);
    record("connectx", family, text);
    return connectx(fd, endpoints, associd, flags, iov, iovcnt, len, connid);
}
static int my_bind(int fd, const struct sockaddr *address, socklen_t length) {
    char text[256]; int family;
    describe(address, text, sizeof text, &family);
    record("bind", family, text);
    return bind(fd, address, length);
}
static int my_listen(int fd, int backlog) {
    struct sockaddr_storage local; socklen_t length = sizeof local;
    char text[256] = ""; int family = -1;
    if (getsockname(fd, (struct sockaddr *)&local, &length) == 0)
        describe((struct sockaddr *)&local, text, sizeof text, &family);
    record("listen", family, text);
    return listen(fd, backlog);
}
static ssize_t my_sendto(int fd, const void *buffer, size_t size, int flags,
                         const struct sockaddr *address, socklen_t length) {
    char text[256]; int family;
    describe(address, text, sizeof text, &family);
    if (address) record("sendto", family, text);
    return sendto(fd, buffer, size, flags, address, length);
}
static ssize_t my_sendmsg(int fd, const struct msghdr *message, int flags) {
    char text[256] = ""; int family = -1;
    if (message && message->msg_name) {
        describe((const struct sockaddr *)message->msg_name, text, sizeof text, &family);
        record("sendmsg", family, text);
    }
    return sendmsg(fd, message, flags);
}
static int my_getaddrinfo(const char *node, const char *service,
                          const struct addrinfo *hints, struct addrinfo **result) {
    record("getaddrinfo", -1, node ? node : "");
    return getaddrinfo(node, service, hints, result);
}
static int my_getnameinfo(const struct sockaddr *address, socklen_t length, char *host,
                          socklen_t hostlen, char *serv, socklen_t servlen, int flags) {
    char text[256]; int family;
    describe(address, text, sizeof text, &family);
    record("getnameinfo", family, text);
    return getnameinfo(address, length, host, hostlen, serv, servlen, flags);
}
static struct hostent *my_gethostbyname(const char *name) {
    record("gethostbyname", -1, name ? name : "");
    return gethostbyname(name);
}
static struct hostent *my_gethostbyname2(const char *name, int family) {
    record("gethostbyname2", family, name ? name : "");
    return gethostbyname2(name, family);
}
static struct hostent *my_gethostbyaddr(const void *address, socklen_t length, int type) {
    record("gethostbyaddr", type, "");
    return gethostbyaddr(address, length, type);
}
static DNSServiceErrorType my_DNSServiceGetAddrInfo(
    DNSServiceRef *ref, DNSServiceFlags flags, uint32_t index, DNSServiceProtocol protocol,
    const char *host, DNSServiceGetAddrInfoReply callback, void *context) {
    record("DNSServiceGetAddrInfo", -1, host ? host : "");
    return DNSServiceGetAddrInfo(ref, flags, index, protocol, host, callback, context);
}
static DNSServiceErrorType my_DNSServiceQueryRecord(
    DNSServiceRef *ref, DNSServiceFlags flags, uint32_t index, const char *name,
    uint16_t rrtype, uint16_t rrclass, DNSServiceQueryRecordReply callback, void *context) {
    record("DNSServiceQueryRecord", -1, name ? name : "");
    return DNSServiceQueryRecord(ref, flags, index, name, rrtype, rrclass, callback, context);
}

INTERPOSE(my_socket, socket)
INTERPOSE(my_connect, connect)
INTERPOSE(my_connectx, connectx)
INTERPOSE(my_bind, bind)
INTERPOSE(my_listen, listen)
INTERPOSE(my_sendto, sendto)
INTERPOSE(my_sendmsg, sendmsg)
INTERPOSE(my_getaddrinfo, getaddrinfo)
INTERPOSE(my_getnameinfo, getnameinfo)
INTERPOSE(my_gethostbyname, gethostbyname)
INTERPOSE(my_gethostbyname2, gethostbyname2)
INTERPOSE(my_gethostbyaddr, gethostbyaddr)
INTERPOSE(my_DNSServiceGetAddrInfo, DNSServiceGetAddrInfo)
INTERPOSE(my_DNSServiceQueryRecord, DNSServiceQueryRecord)
"""

CONTROL_C = r"""
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

/* Loopback only: TCP connect to 127.0.0.1:9, UDP send to it, resolve localhost. */
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "quiet";
    if (!strcmp(mode, "quiet")) { puts("quiet"); return 0; }
    if (!strcmp(mode, "link")) {  /* a hard link, as Dusty uses to publish files */
        FILE *f = fopen("netobs-link-source", "w");
        if (!f) return 3;
        fputs("x", f); fclose(f);
        int r = link("netobs-link-source", "netobs-link-target");
        printf("link=%d\n", r); unlink("netobs-link-source"); unlink("netobs-link-target");
        return r == 0 ? 0 : 4;
    }
    if (!strcmp(mode, "unix")) {  /* a local socket that is not name resolution */
        int fd = socket(AF_UNIX, SOCK_STREAM, 0);
        struct sockaddr_un a; memset(&a, 0, sizeof a);
        a.sun_family = AF_UNIX; strcpy(a.sun_path, "/private/var/run/syslog");
        printf("unix=%d\n", connect(fd, (struct sockaddr *)&a, sizeof a)); close(fd);
        return 0;
    }
    if (!strcmp(mode, "connect") || !strcmp(mode, "all")) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        struct sockaddr_in a; memset(&a, 0, sizeof a);
        a.sin_family = AF_INET; a.sin_port = htons(9); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        int r = connect(fd, (struct sockaddr *)&a, sizeof a);
        printf("connect=%d\n", r); close(fd);
    }
    if (!strcmp(mode, "udp") || !strcmp(mode, "all")) {
        int fd = socket(AF_INET, SOCK_DGRAM, 0);
        struct sockaddr_in a; memset(&a, 0, sizeof a);
        a.sin_family = AF_INET; a.sin_port = htons(9); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        printf("sendto=%zd\n", sendto(fd, "x", 1, 0, (struct sockaddr *)&a, sizeof a)); close(fd);
    }
    if (!strcmp(mode, "resolve") || !strcmp(mode, "all")) {
        struct addrinfo *res = NULL;
        int r = getaddrinfo("localhost", "9", NULL, &res);
        printf("getaddrinfo=%d\n", r); if (res) freeaddrinfo(res);
    }
    return 0;
}
"""

# sandbox-exec is a SIP-protected platform binary, so dyld removes DYLD_* variables
# before it runs and they never reach the sandboxed program. This launcher runs
# inside the sandbox and restores the interposer from NETOBS_INSERT before exec.
LAUNCHER_C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc, char **argv) {
    const char *insert = getenv("NETOBS_INSERT");
    if (argc < 2) return 126;
    if (insert && *insert) setenv("DYLD_INSERT_LIBRARIES", insert, 1);
    execv(argv[1], argv + 1);
    perror("netobs-launch");
    return 127;
}
"""

# Runs inside the observed Python process (venv interpreter, PYTHONPATH=src).
CHILD_PRELUDE = r"""
import json, os, sys
_LOG = os.environ.get("DUSTY_NETOBS_PYLOG", "")
_PREFIXES = %(prefixes)r
def _record(event, args):
    if _LOG and event.startswith(_PREFIXES):
        with open(_LOG, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "event": event}) + "\n")
sys.addaudithook(_record)
from dusty.privacy.network_guard import install_guard
install_guard()
if os.environ.get("DUSTY_NETOBS_CHILDREN") == "1":
    from dusty.platform import mac_process
    _original = mac_process.child_environment
    def _observed(executable):
        environment = dict(_original(executable))
        for name in %(observe)r:
            environment[name] = os.environ[name]
        environment["DYLD_INSERT_LIBRARIES"] = os.environ["NETOBS_INSERT"]
        return environment
    mac_process.child_environment = _observed
"""

CHILD_BODIES = {
    "batch": r"""
from dusty.devcli import main
sys.exit(main(sys.argv[1:]))
""",
    "python-control": r"""
from dusty.privacy.logging import configure_logger
from dusty.privacy.network_guard import NetworkBlockedError
from pathlib import Path
configure_logger(Path(os.environ["LOCALAPPDATA"]) / "Dusty")
import socket
results = {}
for name, attempt in (
    ("getaddrinfo", lambda: socket.getaddrinfo("localhost", 9)),
    ("socket_connect", lambda: socket.socket().connect(("127.0.0.1", 9))),
):
    try:
        attempt()
        results[name] = "not blocked"
    except NetworkBlockedError:
        results[name] = "blocked"
    except OSError as error:
        results[name] = "os error " + type(error).__name__
print(json.dumps(results))
""",
    "runner-control": r"""
from pathlib import Path
from dusty.platform.mac_process import run_job_process
lines = []
result = run_job_process([sys.argv[1], sys.argv[2]], on_stdout=lines.append, timeout_sec=30)
print(json.dumps({"exit_code": result.exit_code, "stdout": lines}))
""",
    "gui-batch": GUI_DRIVER,
    "gui": r"""
import threading, signal
seconds = float(sys.argv[1])
timer = threading.Timer(seconds, lambda: os.kill(os.getpid(), signal.SIGTERM))
timer.daemon = True  # a GUI that fails to start must end on its own, not pass
timer.start()
from dusty.__main__ import main
sys.exit(main([]))
""",
}


DIAGNOSTIC_REPORTS = Path.home() / "Library/Logs/DiagnosticReports"
CONTROL_NAME = "netobs-control"


def sandbox_reports(since: float, folder: Path = DIAGNOSTIC_REPORTS) -> list[dict]:
    """Crash reports written since a time for processes the sandbox killed."""
    found = []
    for path in sorted(folder.glob("*.ips")) if folder.is_dir() else []:
        try:
            if path.stat().st_mtime < since:
                continue
            _, body = path.read_text(encoding="utf-8", errors="replace").split("\n", 1)
            report = json.loads(body)
        except (OSError, ValueError):
            continue
        termination = report.get("termination") or {}
        if termination.get("namespace") == "SANDBOX":
            found.append({"process": report.get("procName", "?"), "file": path.name})
    return found


class ObserveError(RuntimeError):
    """The harness itself could not run; this is not an observation result."""


def compile_tools(work: Path) -> tuple[Path, Path, Path]:
    """Build the interposer, the loopback control and the launcher with Apple clang."""
    work.mkdir(parents=True, exist_ok=True)
    sources = {
        "netobs_interpose.c": INTERPOSER_C,
        "netobs_control.c": CONTROL_C,
        "netobs_launch.c": LAUNCHER_C,
    }
    for name, text in sources.items():
        (work / name).write_text(text, encoding="utf-8")
    dylib, control = work / "libnetobs.dylib", work / "netobs-control"
    launcher = work / "netobs-launch"
    # The interposer is also built as arm64e: dyld may load it into Apple's own
    # arm64e programs such as /usr/bin/sandbox-exec, and macOS 15 refuses a plain
    # arm64 library there. Dusty's own programs load the arm64 slice.
    for args in (
        [
            "-arch",
            "arm64e",
            "-dynamiclib",
            "-O2",
            "-Wall",
            "-o",
            str(dylib),
            str(work / "netobs_interpose.c"),
        ],
        ["-O2", "-Wall", "-o", str(control), str(work / "netobs_control.c")],
        ["-O2", "-Wall", "-o", str(launcher), str(work / "netobs_launch.c")],
    ):
        result = subprocess.run(
            ["/usr/bin/clang", "-arch", "arm64", *args],
            env=TOOL_ENV,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise ObserveError("clang failed: " + result.stderr.strip()[-400:])
    return dylib, control, launcher


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"unparsed": line[:200]})
    return rows


def classify(rows: list[dict]) -> dict:
    """Split interposer records into loads, network attempts and local IPC."""
    loads: Counter[str] = Counter()
    network, local = [], []
    for row in rows:
        call, family = row.get("call", ""), row.get("family", -1)
        if call == "load":
            loads[row.get("program", "?")] += 1
        elif call in RESOLVER_CALLS or (call in SOCKET_CALLS and family in NETWORK_FAMILIES):
            network.append(row)
        else:
            local.append(row)
    return {"loaded": dict(sorted(loads.items())), "network": network, "local_ipc": local}


def python_events(path: Path) -> list[str]:
    return sorted({row.get("event", "?") for row in read_jsonl(path)})


def guard_lines(user_dir: Path, needle: str = "network_blocked") -> list[str]:
    lines = []
    for log in sorted((user_dir / "logs").glob("dusty.log*")):
        lines += [
            line.split(" ", 2)[-1]
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
            if needle in line
        ]
    return lines


def run(argv: list[str], env: dict[str, str], *, cwd: Path, timeout: float = 900) -> dict:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv, env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        code = None
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
        stderr = "timeout"
    if sys.platform == "win32":
        raise NotImplementedError("macOS only")
    return {
        "exit_code": code,
        "killed_by_sigkill": code == -signal.SIGKILL,
        "seconds": round(time.monotonic() - started, 1),
        "stdout_tail": (stdout or "").strip().splitlines()[-8:],
        "stderr_tail": (stderr or "").strip().splitlines()[-3:],
    }


def child_exit(outcome: dict) -> int | None:
    """The control's exit code as the Dusty runner reported it, if printed."""
    for line in reversed(outcome["stdout_tail"]):
        try:
            return json.loads(line)["exit_code"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return None


class Harness:
    def __init__(
        self,
        out: Path,
        bin_dir: Path,
        models_dir: Path,
        app: Path | None,
        qt_platform: str = "cocoa",
    ):
        self.out, self.bin_dir, self.models_dir, self.app = out, bin_dir, models_dir, app
        self.qt_platform = qt_platform
        self.dylib, self.control, self.launcher = compile_tools(out / "tools")
        self.results: dict = {"calibration": [], "scenarios": []}

    def sandboxed(self, argv: list[str], use_sandbox: bool) -> list[str]:
        if not use_sandbox:
            return argv
        return [SANDBOX_EXEC, "-p", KILL_PROFILE, str(self.launcher), *argv]

    def scenario_dir(self, name: str) -> Path:
        self.mark = time.time() - 1  # crash report times have one second resolution
        folder = self.out / name
        folder.mkdir(parents=True)
        (folder / "appdata").mkdir()
        return folder

    def base_env(self, folder: Path, *, interpose: bool) -> dict[str, str]:
        env = dict(TOOL_ENV)
        env["HOME"] = os.environ.get("HOME", str(Path.home()))
        env["LOCALAPPDATA"] = str(folder / "appdata")
        env["DUSTY_NETOBS_LOG"] = str(folder / "native.jsonl")
        env["DUSTY_NETOBS_PYLOG"] = str(folder / "python.jsonl")
        if interpose:
            env["DYLD_INSERT_LIBRARIES"] = str(self.dylib)
            env["NETOBS_INSERT"] = str(self.dylib)
        return env

    def python_child(
        self,
        body: str,
        args: list[str],
        folder: Path,
        *,
        sandbox: bool,
        children: bool,
        extra: dict[str, str] | None = None,
        timeout: float = 900,
    ) -> dict:
        script = folder / f"child_{body}.py"
        script.write_text(
            CHILD_PRELUDE % {"prefixes": PYTHON_NETWORK_PREFIXES, "observe": OBSERVE_ENV}
            + CHILD_BODIES[body],
            encoding="utf-8",
        )
        env = self.base_env(folder, interpose=True)
        env["PYTHONPATH"] = str(ROOT / "src")
        env["DUSTY_BIN_DIR"] = str(self.bin_dir)
        env["DUSTY_MODELS_DIR"] = str(self.models_dir)
        if children:
            env["DUSTY_NETOBS_CHILDREN"] = "1"
        env.update(extra or {})
        argv = self.sandboxed([str(PYTHON), str(script), *args], sandbox)
        return run(argv, env, cwd=folder, timeout=timeout)

    def record(self, kind: str, entry: dict) -> dict:
        self.results[kind].append(entry)
        status = entry.get("status") or ("pass" if entry.get("passed") else "FAIL")
        print(f"[{status}] {kind}: {entry['name']}")
        return entry

    # Calibration -----------------------------------------------------------

    def calibrate(self) -> bool:
        checks: list[tuple[str, Callable[[], dict]]] = [
            ("control-quiet-interposer", lambda: self.control_direct("quiet", False)),
            ("control-all-interposer", lambda: self.control_direct("all", False)),
            ("control-quiet-sandbox", lambda: self.control_direct("quiet", True)),
            ("control-hard-link-sandbox", lambda: self.control_direct("link", True)),
            ("control-local-socket-sandbox", lambda: self.control_direct("unix", True)),
            ("control-connect-sandbox", lambda: self.control_direct("connect", True)),
            ("control-udp-sandbox", lambda: self.control_direct("udp", True)),
            ("control-resolve-sandbox", lambda: self.control_direct("resolve", True)),
            ("control-through-lifeline", lambda: self.control_runner("all", False)),
            ("control-through-lifeline-sandbox", lambda: self.control_runner("connect", True)),
            ("control-quiet-through-lifeline-sandbox", lambda: self.control_runner("quiet", True)),
            ("python-guard-control", self.python_control),
        ]
        ok = True
        for name, check in checks:
            entry = check()
            entry["name"] = name
            ok &= self.record("calibration", entry)["passed"]
        self.results["unified_log_note"] = self.unified_log_probe()
        return ok

    def control_direct(self, mode: str, sandbox: bool) -> dict:
        folder = self.scenario_dir(f"cal-direct-{mode}-{'sandbox' if sandbox else 'plain'}")
        env = self.base_env(folder, interpose=True)
        outcome = run(
            self.sandboxed([str(self.control), mode], sandbox), env, cwd=folder, timeout=60
        )
        seen = classify(read_jsonl(folder / "native.jsonl"))
        loaded = "tools/netobs-control" in seen["loaded"]
        reports = self.wait_reports(outcome)
        if mode in ("quiet", "link"):
            passed = outcome["exit_code"] == 0 and loaded and not seen["network"]
            expected = "exit 0, load record, no network records"
            if mode == "link":
                expected = "hard link succeeds and is not killed (no false positive)"
        elif mode == "unix":
            unix = [row for row in seen["local_ipc"] if row["call"] == "connect"]
            passed = (
                outcome["exit_code"] == 0 and bool(unix) and "unix=-1" in outcome["stdout_tail"]
            )
            expected = "local socket connect denied (not killed) and recorded as local IPC"
        elif sandbox:
            passed = outcome["killed_by_sigkill"] and loaded and bool(seen["network"])
            expected = "killed by SIGKILL, attempt recorded before the kill"
            # The crash report channel is recorded, not required: ReportCrash may be
            # throttled, and the kill itself already proves detection.
            outcome["sandbox_crash_report"] = any(row["process"] == CONTROL_NAME for row in reports)
        else:
            calls = {row["call"] for row in seen["network"]}
            passed = outcome["exit_code"] == 0 and {"connect", "sendto", "getaddrinfo"} <= calls
            expected = "exit 0, connect, sendto and getaddrinfo recorded"
        return {"expected": expected, "run": outcome, "interposer": seen, "passed": passed}

    def control_bin(self) -> Path:
        folder = self.out / "control-bin"
        if not folder.exists():
            (folder / "lifeline").mkdir(parents=True)
            (folder / "control").mkdir()
            shutil.copy2(self.bin_dir / "lifeline/dusty-lifeline", folder / "lifeline")
            shutil.copy2(self.control, folder / "control/netobs-control")
        return folder

    def control_runner(self, mode: str, sandbox: bool) -> dict:
        folder = self.scenario_dir(f"cal-lifeline-{mode}-{'sandbox' if sandbox else 'plain'}")
        bin_dir = self.control_bin()
        outcome = self.python_child(
            "runner-control",
            [str(bin_dir / "control/netobs-control"), mode],
            folder,
            sandbox=sandbox,
            children=True,
            extra={"DUSTY_BIN_DIR": str(bin_dir)},
            timeout=120,
        )
        seen = classify(read_jsonl(folder / "native.jsonl"))
        chain = {"lifeline/dusty-lifeline", "control/netobs-control"} <= set(seen["loaded"])
        attributed = {row["program"] for row in seen["network"]}
        if mode == "quiet":
            passed = outcome["exit_code"] == 0 and chain and not seen["network"]
            expected = "Dusty runner starts the control under the lifeline; no network records"
        elif sandbox:
            # The kernel kills the control; the Dusty runner reports its failure.
            passed = (
                outcome["exit_code"] == 0
                and chain
                and attributed == {"control/netobs-control"}
                and child_exit(outcome) not in (0, None)
            )
            expected = "control killed inside the Dusty process tree; attempt attributed to it"
        else:
            passed = (
                outcome["exit_code"] == 0 and chain and attributed == {"control/netobs-control"}
            )
            expected = "attempts recorded and attributed to the control, not the lifeline"
        return {"expected": expected, "run": outcome, "interposer": seen, "passed": passed}

    def python_control(self) -> dict:
        folder = self.scenario_dir("cal-python-guard")
        outcome = self.python_child("python-control", [], folder, sandbox=False, children=False)
        events = python_events(folder / "python.jsonl")
        guard = guard_lines(folder / "appdata/Dusty")
        printed = outcome["stdout_tail"][-1] if outcome["stdout_tail"] else "{}"
        try:
            verdicts = json.loads(printed)
        except json.JSONDecodeError:
            verdicts = {}
        passed = (
            verdicts == {"getaddrinfo": "blocked", "socket_connect": "blocked"}
            and "socket.getaddrinfo" in events
            and "socket.__new__" in events
            and any("socket.getaddrinfo" in line for line in guard)
        )
        return {
            "expected": "guard blocks both, recording hook and dusty.log see the events",
            "run": outcome,
            "python_events": events,
            "guard_log": guard,
            "verdicts": verdicts,
            "passed": passed,
        }

    def unified_log_probe(self) -> str:
        """Record whether sandbox denials of an ad hoc program reach the unified log."""
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        profile = "(version 1)(allow default)(deny network*)"
        subprocess.run(
            [SANDBOX_EXEC, "-p", profile, str(self.control), "connect"],
            env=TOOL_ENV,
            capture_output=True,
            check=False,
        )
        time.sleep(2)
        shown = subprocess.run(
            [
                "/usr/bin/log",
                "show",
                "--start",
                started,
                "--style",
                "compact",
                "--predicate",
                'subsystem == "com.apple.sandbox.reporting"',
            ],
            env=TOOL_ENV,
            capture_output=True,
            text=True,
            check=False,
        )
        hit = "netobs-control" in shown.stdout
        return (
            "unified log reported the ad hoc control's denial"
            if hit
            else "unified log did not report the ad hoc control's denial; not used as a detector"
        )

    # Scenarios -------------------------------------------------------------

    def wait_reports(self, outcome: dict) -> list[dict]:
        """SANDBOX crash reports since this scenario started, after ReportCrash runs."""
        deadline = time.monotonic() + (8 if outcome.get("killed_by_sigkill") else 2)
        while True:
            found = sandbox_reports(self.mark)
            if found or time.monotonic() >= deadline:
                return found
            time.sleep(0.5)

    def judge(
        self, folder: Path, outcome: dict, required: set[str], *, python: bool = False
    ) -> dict:
        reports = [row for row in self.wait_reports(outcome) if row["process"] != CONTROL_NAME]
        seen = classify(read_jsonl(folder / "native.jsonl"))
        events = python_events(folder / "python.jsonl")
        guard = guard_lines(folder / "appdata/Dusty")
        loaded = set(seen["loaded"])
        missing = sorted(required - loaded)
        # A GPU probe killed by the sandbox would make auto silently fall back to
        # the CPU and still finish, so auto runs must show that Metal really ran.
        settings = folder / "appdata/Dusty/settings.json"
        try:
            probe = json.loads(settings.read_text(encoding="utf-8")).get("backend_probe", {})
        except (OSError, ValueError, AttributeError):
            probe = {}
        backends = sorted(
            {
                part.removeprefix("backend=")
                for line in guard_lines(folder / "appdata/Dusty", "backend=")
                for part in line.split()
                if part.startswith("backend=")
            }
        )
        if python and not any("python" in name for name in loaded):
            missing.append("python interpreter")
        return {
            "run": outcome,
            "interposer": seen,
            "python_events": events,
            "guard_log": guard,
            "sandbox_reports": reports,
            "not_observed": missing,
            "gpu_probe_ok": probe.get("ok") if isinstance(probe, dict) else None,
            "backends_logged": backends,
        }

    def finish(self, entry: dict, name: str, layers: list[str], completed: bool) -> dict:
        """clean, network attempt, did not complete, or incomplete observation."""
        attempt = (
            entry["run"].get("killed_by_sigkill")
            or entry["interposer"]["network"]
            or entry["python_events"]
            or entry["guard_log"]
            or entry.get("sandbox_reports")
        )
        if attempt:
            status = "network attempt"
        elif not completed:
            status = "did not complete"
        elif entry["not_observed"]:
            status = "incomplete observation"
        else:
            status = "clean"
        entry.update(name=name, layers=layers, status=status, passed=status == "clean")
        return self.record("scenarios", entry)

    def batch(self, backend: str, *, children: bool) -> dict:
        label = f"devcli-{backend}" + ("" if children else "-product-env")
        folder = self.scenario_dir(label)
        source = folder / "input/jfk.m4a"
        source.parent.mkdir()
        shutil.copyfile(FIXTURE, source)
        args = ["transcribe", str(source), "--out", str(folder / "output"), "--model", "tiny"]
        args += ["--backend", backend]
        for value in FORMATS:
            args += ["--format", value]
        outcome = self.python_child("batch", args, folder, sandbox=True, children=children)
        outputs = sorted(path.name for path in (folder / "output").glob("*"))
        required: set[str] = set()
        if children:
            required |= {"lifeline/dusty-lifeline", "ffmpeg/ffprobe", "ffmpeg/ffmpeg"}
            required |= {"cpu/whisper-cli"} if backend == "cpu" else {"metal/whisper-cli"}
        entry = self.judge(folder, outcome, required, python=True)
        entry["outputs"] = outputs
        completed = outcome["exit_code"] == 0 and len(outputs) == len(FORMATS)
        if backend == "auto":
            completed &= entry["gpu_probe_ok"] is True and entry["backends_logged"] == ["metal"]
        return self.finish(entry, label, ["sandbox kill", "interposer", "python audit"], completed)

    def gui_env(self) -> dict[str, str]:
        """Real Cocoa (a window appears briefly) or Qt's offscreen platform."""
        env = {"LANG": "en_US.UTF-8"}
        if self.qt_platform == "offscreen":
            env["QT_QPA_PLATFORM"] = "offscreen"
        return env

    def returning_user(self, folder: Path) -> Path:
        """Private profile with a saved output folder, so no welcome dialog waits."""
        profile = folder / "appdata/Dusty"
        profile.mkdir(mode=0o700, exist_ok=True)
        output = folder / "output"
        (profile / "settings.json").write_text(
            json.dumps({"schema_version": 1, "welcome_seen": True, "output_dir": str(output)}),
            encoding="utf-8",
        )
        return output

    def source_gui_batch(self) -> dict:
        folder = self.scenario_dir("source-gui-batch")
        output = self.returning_user(folder)
        source = folder / "input/jfk.m4a"
        source.parent.mkdir()
        shutil.copyfile(FIXTURE, source)
        outcome = self.python_child(
            "gui-batch",
            ["batch", str(source), str(output), "netobs hint"],
            folder,
            sandbox=True,
            children=True,
            extra=self.gui_env(),
            timeout=300,
        )
        outputs = sorted(path.name for path in output.glob("*"))
        required = {"lifeline/dusty-lifeline", "ffmpeg/ffprobe", "ffmpeg/ffmpeg"}
        required |= {"metal/whisper-cli"}
        entry = self.judge(folder, outcome, required, python=True)
        entry["outputs"] = outputs
        entry["qt_platform"] = self.qt_platform
        summary = any('"jobs": ["done"]' in line for line in outcome["stdout_tail"])
        completed = (
            outcome["exit_code"] == 0
            and summary
            and len(outputs) == len(FORMATS)
            and entry["gpu_probe_ok"] is True
            and entry["backends_logged"] == ["metal"]
        )
        layers = ["sandbox kill", "interposer", "python audit"]
        return self.finish(entry, "source-gui-batch", layers, completed)

    def source_gui(self, seconds: float) -> dict:
        folder = self.scenario_dir("source-gui-idle")
        self.returning_user(folder)
        outcome = self.python_child(
            "gui",
            [str(seconds)],
            folder,
            sandbox=True,
            children=True,
            extra=self.gui_env(),
            timeout=seconds + 60,
        )
        entry = self.judge(folder, outcome, set(), python=True)
        entry["qt_platform"] = self.qt_platform
        completed = outcome["exit_code"] == -signal.SIGTERM  # still running when stopped
        layers = ["sandbox kill", "interposer", "python audit"]
        return self.finish(entry, "source-gui-idle", layers, completed)

    def app_env(self, folder: Path) -> dict[str, str]:
        env = self.base_env(folder, interpose=False)
        # Private folders, as Dusty creates them; the GUI refuses a group-readable profile.
        models = folder / "appdata/Dusty/models"
        models.parent.mkdir(mode=0o700)
        models.mkdir(mode=0o700)
        for name in ("ggml-tiny.bin", "ggml-silero-vad.bin"):
            if (self.models_dir / name).is_file():
                os.link(self.models_dir / name, models / name)
        return env

    def app_selftest(self, backend: str) -> dict:
        assert self.app is not None
        folder = self.scenario_dir(f"app-selftest-{backend}")
        env = self.app_env(folder)
        argv = [str(self.app / "Contents/MacOS/Dusty"), "--self-test", "--backend", backend]
        outcome = run(self.sandboxed(argv, True), env, cwd=folder, timeout=900)
        entry = self.judge(folder, outcome, set())
        completed = outcome["exit_code"] == 0 and any(
            line.startswith("OK") for line in outcome["stdout_tail"]
        )
        if backend == "auto":
            completed &= entry["gpu_probe_ok"] is True
        return self.finish(
            entry, f"app-selftest-{backend}", ["sandbox kill", "dusty guard log"], completed
        )

    def app_headless(self) -> dict:
        assert self.app is not None
        folder = self.scenario_dir("app-headless-batch")
        env = self.app_env(folder)
        source = folder / "input/jfk.m4a"
        source.parent.mkdir()
        shutil.copyfile(FIXTURE, source)
        argv = [str(self.app / "Contents/MacOS/Dusty"), "--headless-batch", str(source)]
        argv += ["--out", str(folder / "output")]
        outcome = run(self.sandboxed(argv, True), env, cwd=folder, timeout=900)
        entry = self.judge(folder, outcome, set())
        outputs = sorted(path.name for path in (folder / "output").glob("*"))
        entry["outputs"] = outputs
        completed = outcome["exit_code"] == 0 and outputs == ["jfk.txt"]
        completed &= entry["gpu_probe_ok"] is True and entry["backends_logged"] == ["metal"]
        return self.finish(
            entry, "app-headless-batch", ["sandbox kill", "dusty guard log"], completed
        )

    def app_gui(self, seconds: float) -> dict:
        assert self.app is not None
        folder = self.scenario_dir("app-gui-idle")
        env = self.app_env(folder)
        env.update(self.gui_env())
        self.returning_user(folder)
        argv = self.sandboxed([str(self.app / "Contents/MacOS/Dusty")], True)
        started = time.monotonic()
        process = subprocess.Popen(
            argv, env=env, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            code = process.wait(timeout=seconds)
            ended_early = True
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGTERM)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
            ended_early = False
        if sys.platform == "win32":
            raise NotImplementedError("macOS only")
        outcome: dict[str, object] = {
            "exit_code": code,
            "killed_by_sigkill": code == -signal.SIGKILL,
            "ended_before_terminate": ended_early,
            "seconds": round(time.monotonic() - started, 1),
        }
        entry = self.judge(folder, outcome, set())
        entry["qt_platform"] = self.qt_platform
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        outcome["stderr_tail"] = stderr.strip().splitlines()[-3:]
        return self.finish(
            entry, "app-gui-idle", ["sandbox kill", "dusty guard log"], not ended_early
        )


def summary_markdown(results: dict) -> str:
    lines = ["# Network attempt observation", "", f"Overall: {results['verdict']}", ""]
    lines += ["## Calibration", "", "| Control | Expected | Result |", "|---|---|---|"]
    for row in results["calibration"]:
        lines.append(
            f"| {row['name']} | {row['expected']} | {'pass' if row['passed'] else 'FAIL'} |"
        )
    lines += ["", results.get("unified_log_note", ""), "", "## Scenarios", ""]
    lines += [
        "| Scenario | Exit | Processes observed | Network | Python | Guard | Sandbox kills "
        "| Result |"
    ]
    lines += ["|---|---|---|---|---|---|---|---|"]
    for row in results["scenarios"]:
        loaded = ", ".join(f"{k} x{v}" for k, v in row["interposer"]["loaded"].items()) or "n/a"
        lines.append(
            f"| {row['name']} | {row['run']['exit_code']} | {loaded} | "
            f"{len(row['interposer']['network'])} | {len(row['python_events'])} | "
            f"{len(row['guard_log'])} | {len(row.get('sandbox_reports', []))} | "
            f"{row['status']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="New folder for this run")
    parser.add_argument("--bin-dir", type=Path, default=ROOT / "build/bin")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "build/models-dev")
    parser.add_argument("--app", type=Path, help="Built Dusty.app to observe as well")
    parser.add_argument("--gui-seconds", type=float, default=20.0)
    parser.add_argument("--skip-gui", action="store_true")
    parser.add_argument(
        "--qt-platform",
        choices=("cocoa", "offscreen"),
        default="cocoa",
        help="cocoa shows real windows briefly (works unattended); offscreen draws nothing",
    )
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("This harness needs macOS", file=sys.stderr)
        return 2
    if args.out.exists():
        print(f"Refusing existing output folder: {args.out}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True)
    harness = Harness(
        args.out.resolve(),
        args.bin_dir.resolve(),
        args.models_dir.resolve(),
        args.app.resolve() if args.app else None,
        args.qt_platform,
    )
    results_platform = args.qt_platform
    started = time.time() - 1
    calibrated = harness.calibrate()
    if calibrated:
        harness.batch("cpu", children=True)
        harness.batch("auto", children=True)
        harness.batch("auto", children=False)
        if not args.skip_gui:
            harness.source_gui(args.gui_seconds)
            harness.source_gui_batch()
        if harness.app:
            harness.app_selftest("cpu")
            harness.app_selftest("auto")
            harness.app_headless()
            if not args.skip_gui:
                harness.app_gui(args.gui_seconds)
    results = harness.results
    statuses = Counter(row["status"] for row in results["scenarios"])
    late = [row for row in sandbox_reports(started) if row["process"] != CONTROL_NAME]
    results["sandbox_reports_during_run"] = late
    if not calibrated:
        verdict = "calibration failed; scenario results are not trustworthy"
    elif late and not statuses["network attempt"]:
        verdict = "NETWORK ATTEMPT: sandbox crash reports for " + ", ".join(
            sorted({row["process"] for row in late})
        )
    elif statuses["network attempt"]:
        verdict = f"NETWORK ATTEMPT observed in {statuses['network attempt']} scenario(s)"
    elif set(statuses) == {"clean"}:
        verdict = "no network attempts observed"
    else:
        verdict = "no network attempts observed; some scenarios did not complete: " + ", ".join(
            f"{count} {status}" for status, count in sorted(statuses.items()) if status != "clean"
        )
    results["verdict"] = verdict
    results["profile"] = KILL_PROFILE
    results["qt_platform"] = results_platform
    results["python"] = str(PYTHON)
    (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (args.out / "summary.md").write_text(summary_markdown(results), encoding="utf-8")
    print(results["verdict"])
    return 0 if verdict == "no network attempts observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
