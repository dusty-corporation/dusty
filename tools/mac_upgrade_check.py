"""Run the Mac first run, upgrade, removal and relocation scenarios headless (P24, P25).

    python -m tools.mac_upgrade_check --new build/mac-app-B/Dusty.app \\
        [--old build/mac-app-A/Dusty.app] --models <verified models folder> \\
        --out build/upgrade-run

--old is the version installed first and --new the version that replaces it; without
--old the new build is used for both. Every scenario gets its own new HOME and
TMPDIR under --out and LOCALAPPDATA is removed from the app environment, so the
data folder is the Mac default, <HOME>/Library/Application Support/Dusty, while
the real one is never touched. The app runs only headless: --version,
--self-test, --installer-test, --installer-status, --installer-pass and
--headless-batch. Nothing is downloaded: verified Tiny and Voice detection models
are copied into the data folder's models folder, where finished downloads go, and
Dusty checks size and SHA-256 before use. Settings the window would save (output
folder, formats, language) are written with the same shared settings code.

Results go to <out>/results.json with paths shown relative to --out, and a table
is printed. Rows marked "info" record behavior without a pass or fail (the old
build's probe cache and a quarantined copy). Exit 1 when any checked row fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/audio/formats/jfk.wav"
DATA = Path("Library/Application Support/Dusty")
MODELS = ("ggml-tiny.bin", "ggml-silero-vad.bin")
CATALOG = ("large-v3-turbo-q8_0", "small", "medium", "small.en", "tiny")
PREFERENCES = {"welcome_seen": True, "formats": ["txt", "srt"], "language": "en"}
QUARANTINE = "0081;{:x};Safari;"


@dataclass
class Row:
    scenario: str
    step: str
    expected: str
    observed: str
    result: str  # pass, fail or info


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(root: Path, *, skip: tuple[str, ...] = ()) -> dict[str, tuple]:
    """Every entry under root: files by content, size, inode and modification time."""
    entries: dict[str, tuple] = {}
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if any(relative == name or relative.startswith(name + "/") for name in skip):
            continue
        info = path.lstat()
        if path.is_symlink():
            entries[relative] = ("link", os.readlink(path))
        elif path.is_dir():
            entries[relative] = ("dir",)
        else:
            entries[relative] = ("file", sha256(path), info.st_size, info.st_ino, info.st_mtime_ns)
    return entries


def bundle_listing(app: Path) -> dict[str, tuple]:
    """A bundle by content: what a replaced copy must match exactly."""
    return {
        name: entry[:2] if entry[0] == "file" else entry for name, entry in snapshot(app).items()
    }


def differences(before: dict, after: dict) -> list[str]:
    names = sorted(set(before) | set(after))
    return [name for name in names if before.get(name) != after.get(name)]


def leftovers(home: Path) -> list[str]:
    """Everything left in a home folder outside its Trash, as relative names."""
    return [
        path.relative_to(home).as_posix()
        for path in sorted(home.rglob("*"))
        if path.relative_to(home).parts[0] != ".Trash"
    ]


def redact(text: str, out: Path) -> str:
    text = text.replace(str(out), "<out>")
    return text.replace(str(Path.home()), "<home>")


class Harness:
    def __init__(self, out: Path, models: Path, old: Path, new: Path):
        self.out, self.models, self.old, self.new = out, models, old, new
        self.rows: list[Row] = []

    def record(self, scenario: str, step: str, expected: str, observed: str, ok: bool | None):
        result = "info" if ok is None else ("pass" if ok else "fail")
        self.rows.append(Row(scenario, step, expected, redact(observed, self.out), result))

    def home(self, name: str) -> Path:
        home = self.out / name / "home"
        home.mkdir(parents=True)
        (self.out / name / "tmp").mkdir()
        return home

    def app(self, bundle: Path, home: Path, *args: str, timeout: int = 600) -> tuple[int, str]:
        environment = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "LC_ALL": "C",
            "HOME": str(home),
            "TMPDIR": str(home.parent / "tmp") + "/",
        }
        try:
            run = subprocess.run(
                [str(bundle / "Contents/MacOS/Dusty"), *args],
                capture_output=True,
                text=True,
                env=environment,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return -1, "timeout"
        lines = [line for line in run.stdout.splitlines() if line.strip()]
        return run.returncode, lines[-1] if lines else "(no output)"

    def expect(self, scenario, step, bundle, home, args, code, last):
        exit_code, line = self.app(bundle, home, *args)
        self.record(
            scenario,
            step,
            f"exit {code}, {last}",
            f"exit {exit_code}, {line}",
            exit_code == code and line == last,
        )

    def status(self, bundle: Path, home: Path) -> dict[str, str]:
        out = home.parent / "status.json"
        out.unlink(missing_ok=True)
        self.app(bundle, home, "--installer-status", "--out", str(out))
        return json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}

    def add_models(self, home: Path, names: tuple[str, ...]) -> None:
        folder = home / DATA / "models"
        folder.mkdir(exist_ok=True)
        for name in names:
            shutil.copy2(self.models / name, folder / name)

    def settings(self, home: Path) -> dict:
        file = home / DATA / "settings.json"
        return json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}

    def no_running_copy(self, folder: Path) -> bool:
        listing = subprocess.run(
            ["/bin/ps", "-axww", "-o", "command="], capture_output=True, text=True, check=False
        ).stdout
        return str(folder) not in listing

    # P24

    def first_run(self) -> None:
        scenario = "1 first run"
        home = self.home("p24")
        apps = self.out / "p24/Apps with spaces é 日本"
        apps.mkdir()
        app = apps / "Dusty.app"
        ditto(self.new, app)
        data = home / DATA
        status = self.status(app, home)
        self.record(
            scenario,
            "--installer-status, no models",
            "every catalog model and Voice detection missing",
            json.dumps(status, sort_keys=True),
            bool(status) and set(status.values()) == {"missing"},
        )
        self.expect(
            scenario, "--self-test, no model", app, home, ["--self-test"], 1, "SELFTEST_FAILED"
        )
        self.expect(
            scenario,
            "--installer-test --model tiny, no model",
            app,
            home,
            ["--installer-test", "--model", "tiny"],
            1,
            "SELFTEST_FAILED_CPU",
        )
        inputs = self.out / "p24/Recordings"
        inputs.mkdir()
        shutil.copy2(FIXTURE, inputs / FIXTURE.name)
        outputs = self.out / "p24/Transcripts"
        self.expect(
            scenario,
            "--headless-batch, no model",
            app,
            home,
            ["--headless-batch", str(inputs / FIXTURE.name), "--out", str(outputs)],
            1,
            "failed MODEL_MISSING",
        )
        written = sorted(p.name for p in outputs.rglob("*")) if outputs.exists() else []
        self.record(scenario, "outputs after the refused batch", "none", str(written), not written)
        probe = self.settings(home).get("backend_probe")
        self.record(
            scenario,
            "probe cache after runs without a model",
            "nothing cached (D1)",
            json.dumps(probe),
            probe is None,
        )
        mode = oct(data.stat().st_mode & 0o777)
        self.record(scenario, "data folder created private", "0o700", mode, mode == "0o700")
        self.add_models(home, MODELS[:1])
        status = self.status(app, home)
        self.record(
            scenario,
            "--installer-status, Tiny copied",
            "tiny installed",
            status.get("tiny", "?"),
            status.get("tiny") == "installed",
        )
        self.expect(
            scenario,
            "--self-test --backend cpu",
            app,
            home,
            ["--self-test", "--backend", "cpu"],
            0,
            "OK",
        )
        self.expect(scenario, "--self-test (Auto)", app, home, ["--self-test"], 0, "OK")
        probe = self.settings(home).get("backend_probe") or {}
        virtual = virtual_mac(probe)
        self.record(
            scenario,
            "GPU path this run verifies",
            "Metal, or the CPU inside a virtual Mac",
            "CPU, Dusty does not use the GPU inside a virtual Mac" if virtual else "Metal",
            None,
        )
        self.record(
            scenario,
            "probe cached in settings.json backend_probe",
            "ok false, unsupported and virtual Mac, engine and driver signatures"
            if virtual
            else "ok true, engine and driver signatures, device named",
            f"ok {probe.get('ok')}, device {probe.get('device_name')}, keys {sorted(probe)}",
            probe.get("ok") is (not virtual) and {"engine", "driver"} <= set(probe),
        )
        before = sha256(data / "settings.json")
        self.expect(scenario, "--self-test (Auto) again", app, home, ["--self-test"], 0, "OK")
        self.record(
            scenario,
            "second Auto run reuses the cache",
            "settings.json unchanged",
            "unchanged" if sha256(data / "settings.json") == before else "changed",
            sha256(data / "settings.json") == before,
        )
        self.expect(
            scenario,
            "--self-test --backend metal",
            app,
            home,
            ["--self-test", "--backend", "metal"],
            *((1, "GPU_ERROR") if virtual else (0, "OK")),
        )
        self.expect(
            scenario,
            "--installer-test --model tiny (Auto, once)",
            app,
            home,
            ["--installer-test", "--model", "tiny"],
            0,
            "OK_CPU" if virtual else "OK_METAL",
        )
        work = sorted(p.name for p in (data / "work").iterdir())
        self.record(scenario, "work folder after the runs", "empty", str(work), not work)
        log = (data / "logs/dusty.log").read_text(encoding="utf-8")
        clean = str(self.out) not in log and "/Users/" not in log
        self.record(scenario, "log has no paths", "no path", "no path" if clean else "path", clean)

    def old_probe_defect(self) -> None:
        """The old build's probe cache after a batch with no model (defect D1 before the fix)."""
        if self.old == self.new:
            return
        scenario = "1 first run"
        home = self.home("p24-old")
        app = self.out / "p24-old/Applications/Dusty.app"
        app.parent.mkdir()
        ditto(self.old, app)
        inputs = self.out / "p24-old/Recordings"
        inputs.mkdir()
        shutil.copy2(FIXTURE, inputs / FIXTURE.name)
        self.app(
            app,
            home,
            "--headless-batch",
            str(inputs / FIXTURE.name),
            "--out",
            str(self.out / "p24-old/Transcripts"),
        )
        self.add_models(home, MODELS[:1])
        code, line = self.app(app, home, "--self-test")
        probe = self.settings(home).get("backend_probe") or {}
        self.record(
            scenario,
            "old build: batch with no model, add Tiny, --self-test (Auto)",
            "records what the old build caches",
            f"exit {code}, {line}, cached ok {probe.get('ok')}",
            None,
        )

    # P25

    def upgrade(self) -> None:
        scenario = "2 upgrade"
        home = self.home("p25")
        data = home / DATA
        apps = self.out / "p25/Applications"
        apps.mkdir()
        app = apps / "Dusty.app"
        ditto(self.old, app)
        old_version = version(self.old)
        self.expect(
            scenario, "old app --version", app, home, ["--version"], 0, f"Dusty {old_version}"
        )
        self.app(app, home, "--self-test", "--backend", "cpu")  # First start makes the folder.
        self.add_models(home, MODELS)
        self.expect(
            scenario,
            "old app --installer-pass --model tiny",
            app,
            home,
            ["--installer-pass", "--model", "tiny"],
            0,
            "(no output)",
        )
        self.expect(scenario, "old app --self-test (Auto)", app, home, ["--self-test"], 0, "OK")
        outputs = self.out / "p25/Transcripts é"
        from dusty.queue.storage import load_settings, save_settings

        settings = load_settings(data / "settings.json")
        settings.update(PREFERENCES, output_dir=str(outputs))
        save_settings(data / "settings.json", settings)
        inputs = self.out / "p25/Recordings"
        inputs.mkdir()
        shutil.copy2(FIXTURE, inputs / FIXTURE.name)
        self.expect(
            scenario,
            "old app --headless-batch to a separate output folder",
            app,
            home,
            ["--headless-batch", str(inputs / FIXTURE.name), "--out", str(outputs)],
            0,
            "done OK",
        )
        saved = self.settings(home)
        self.record(
            scenario,
            "settings before the upgrade",
            "model tiny, preferences, output folder, probe ok",
            f"model {saved.get('model_id')}, probe ok "
            f"{(saved.get('backend_probe') or {}).get('ok')}, keys {sorted(saved)}",
            saved.get("model_id") == "tiny"
            and all(saved.get(k) == v for k, v in PREFERENCES.items()),
        )
        self.data_before = snapshot(data, skip=("logs",))
        self.log_before = (data / "logs/dusty.log").read_bytes()
        self.outputs_before = snapshot(outputs)
        self.inputs_before = snapshot(inputs)
        self.record(
            scenario,
            "outputs written",
            "jfk.txt",
            str(sorted(self.outputs_before)),
            sorted(self.outputs_before) == ["jfk.txt"],
        )
        self.record(
            scenario,
            "old app has quit",
            "no process from the copy",
            str(self.no_running_copy(apps)),
            self.no_running_copy(apps),
        )
        trash(app, home)
        ditto(self.new, app)
        self.record(
            scenario,
            "replace like Finder (old to Trash, new copied)",
            "installed copy equals the new build file by file",
            f"{len(differences(bundle_listing(self.new), bundle_listing(app)))} differences",
            not differences(bundle_listing(self.new), bundle_listing(app)),
        )
        changed = differences(bundle_listing(self.old), bundle_listing(app))
        self.record(
            scenario,
            "no old files left in the bundle",
            "every file that differed between builds now has the new content",
            f"{len(changed)} files differ from the old build",
            None,
        )
        verify = codesign_verify(app)
        self.record(
            scenario,
            "codesign --verify --deep --strict on the replaced copy",
            "valid",
            verify,
            verify == "valid",
        )
        self.expect(
            scenario, "new app --version", app, home, ["--version"], 0, f"Dusty {version(self.new)}"
        )
        status = self.status(app, home)
        self.record(
            scenario,
            "new app --installer-status",
            "tiny and silero-vad installed (hash verified), others missing",
            json.dumps(status, sort_keys=True),
            status.get("tiny") == "installed"
            and status.get("silero-vad") == "installed"
            and all(status.get(name) == "missing" for name in CATALOG if name != "tiny"),
        )
        self.expect(scenario, "new app --self-test (Auto)", app, home, ["--self-test"], 0, "OK")
        self.compare(scenario, home, outputs, inputs)

    def compare(self, scenario: str, home: Path, outputs: Path, inputs: Path) -> None:
        data = home / DATA
        changed = differences(self.data_before, snapshot(data, skip=("logs",)))
        self.record(
            scenario,
            "data folder except logs",
            "identical: settings, queue, models (content, inode, time)",
            f"{len(changed)} changed {changed}",
            not changed,
        )
        parts = sorted(p.name for p in (data / "models").glob("*.part"))
        self.record(
            scenario,
            "no new download",
            "no .part file, model inode and time kept",
            str(parts),
            not parts and not changed,
        )
        log = (data / "logs/dusty.log").read_bytes()
        self.record(
            scenario,
            "log kept",
            "earlier lines kept, new lines appended",
            "kept" if log.startswith(self.log_before) else "rewritten",
            log.startswith(self.log_before),
        )
        changed = differences(self.outputs_before, snapshot(outputs))
        self.record(
            scenario,
            "outputs untouched",
            "same content, inode and time",
            f"{len(changed)} changed",
            not changed,
        )
        changed = differences(self.inputs_before, snapshot(inputs))
        self.record(
            scenario,
            "recordings untouched",
            "same content, inode and time",
            f"{len(changed)} changed",
            not changed,
        )

    def remove_reinstall(self) -> None:
        scenario = "3 remove and reinstall"
        home = self.out / "p25/home"
        data = home / DATA
        apps = self.out / "p25/Applications"
        app = apps / "Dusty.app"
        outputs = self.out / "p25/Transcripts é"
        inputs = self.out / "p25/Recordings"
        trash(app, home)
        self.record(
            scenario,
            "drag Dusty.app to the Trash",
            "app gone from Applications",
            str(sorted(p.name for p in apps.iterdir())),
            not app.exists(),
        )
        self.compare(scenario, home, outputs, inputs)
        ditto(self.new, app)
        status = self.status(app, home)
        self.record(
            scenario,
            "reinstalled app --installer-status",
            "tiny and silero-vad installed",
            f"tiny {status.get('tiny')}, silero-vad {status.get('silero-vad')}",
            status.get("tiny") == "installed" and status.get("silero-vad") == "installed",
        )
        before = self.settings(home)
        self.expect(
            scenario, "reinstalled app --self-test (Auto)", app, home, ["--self-test"], 0, "OK"
        )
        self.record(
            scenario,
            "settings found again",
            "same settings, probe cache reused",
            "same" if self.settings(home) == before else "changed",
            self.settings(home) == before
            and all(before.get(k) == v for k, v in PREFERENCES.items()),
        )
        # docs/user/mac.md, Remove Dusty, applied to this isolated home only.
        self.record(
            scenario,
            "removal step 1: Dusty has quit",
            "no process from the copy",
            str(self.no_running_copy(apps)),
            self.no_running_copy(apps),
        )
        trash(app, home)
        trash(data, home)
        left = leftovers(home)
        self.record(
            scenario,
            "removal step 2: data folder to the Trash",
            "only the empty Library/Application Support folders remain",
            str(left),
            left == ["Library", "Library/Application Support"],
        )
        temporary = sorted(p.name for p in (home.parent / "tmp").iterdir())
        self.record(
            scenario, "temporary folder", "nothing from Dusty", str(temporary), not temporary
        )
        changed = differences(self.outputs_before, snapshot(outputs))
        self.record(
            scenario, "outputs after removal", "untouched", f"{len(changed)} changed", not changed
        )
        changed = differences(self.inputs_before, snapshot(inputs))
        self.record(
            scenario,
            "recordings after removal",
            "untouched",
            f"{len(changed)} changed",
            not changed,
        )

    # P33 relocation and quarantine

    def moved(self) -> Path:
        scenario = "4 moved app"
        home = self.home("p33")
        first = self.out / "p33/First folder/Dusty.app"
        first.parent.mkdir()
        ditto(self.new, first)
        self.expect(
            scenario,
            "--self-test --backend cpu before the move",
            first,
            home,
            ["--self-test", "--backend", "cpu"],
            1,
            "SELFTEST_FAILED",
        )
        self.add_models(home, MODELS[:1])
        moved = self.out / "p33/Moved here ü/Dusty.app"
        moved.parent.mkdir()
        first.rename(moved)
        self.expect(
            scenario,
            "moved app --self-test --backend cpu",
            moved,
            home,
            ["--self-test", "--backend", "cpu"],
            0,
            "OK",
        )
        self.expect(scenario, "moved app --self-test (Auto)", moved, home, ["--self-test"], 0, "OK")
        verify = codesign_verify(moved)
        self.record(scenario, "codesign verify after the move", "valid", verify, verify == "valid")
        return home

    def quarantined(self, home: Path) -> None:
        """Ad hoc signed copies with a quarantine attribute, launched as from Terminal.

        One copy has the attribute on the bundle folder only, another on every file
        (as Archive Utility leaves an extracted download). Each is launched once,
        before any other launch, because Gatekeeper may show a dialog and protect
        the bundle from later changes.
        """
        scenario = "4 moved app"
        value = QUARANTINE.format(int(time.time()))
        for name, recursive in (("Quarantined bundle", False), ("Quarantined files", True)):
            copy = self.out / "p33" / name / "Dusty.app"
            copy.parent.mkdir()
            ditto(self.new, copy)
            flags = ["-r", "-w"] if recursive else ["-w"]
            written = xattr([*flags, "com.apple.quarantine", value, str(copy)])
            label = "every file" if recursive else "bundle folder only"
            self.record(
                scenario,
                f"quarantine attribute, {label}",
                "written",
                written,
                None,
            )
            self.record(
                scenario, f"spctl --assess, {label}", "Gatekeeper verdict", spctl(copy), None
            )
            code, line = self.app(copy, home, "--version", timeout=90)
            self.record(
                scenario,
                f"Terminal launch --version, {label}",
                "recorded, no expectation",
                f"exit {code}, {line}",
                None,
            )


def ditto(source: Path, destination: Path) -> None:
    subprocess.run(["/usr/bin/ditto", str(source), str(destination)], check=True)


def trash(path: Path, home: Path) -> None:
    """Move to <home>/.Trash under a free name, as Finder does."""
    bin_dir = home / ".Trash"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target, number = bin_dir / path.name, 2
    while target.exists():
        target = bin_dir / f"{path.stem} {number}{path.suffix}"
        number += 1
    path.rename(target)


def version(app: Path) -> str:
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    return str(info["CFBundleShortVersionString"])


def virtual_mac(probe: dict) -> bool:
    """Whether the app's GPU check found a virtual Mac, where it never starts the Metal engine.

    GitHub's Mac runners are virtual Macs. Only there, as recorded by the app
    itself, are the truthful CPU results expected; any real Mac must pass as Metal.
    """
    return probe.get("unsupported") is True and probe.get("virtual_mac") is True


def codesign_verify(app: Path) -> str:
    run = subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)],
        capture_output=True,
        text=True,
        check=False,
    )
    return "valid" if run.returncode == 0 else run.stderr.strip().splitlines()[-1]


def spctl(app: Path) -> str:
    run = subprocess.run(
        ["/usr/sbin/spctl", "--assess", "--type", "execute", "-vv", str(app)],
        capture_output=True,
        text=True,
        check=False,
    )
    text = " ".join((run.stdout + run.stderr).split())
    return f"exit {run.returncode}: {text}"


def xattr(args: list[str]) -> str:
    run = subprocess.run(["/usr/bin/xattr", *args], capture_output=True, text=True, check=False)
    refused = run.stderr.count("Operation not permitted")
    return "written" if run.returncode == 0 else f"exit {run.returncode}, {refused} refused"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--new", type=Path, required=True, help="Dusty.app installed last")
    parser.add_argument("--old", type=Path, help="Dusty.app installed first (default: --new)")
    parser.add_argument("--models", type=Path, required=True, help="Verified models folder")
    parser.add_argument("--out", type=Path, required=True, help="New folder for this run")
    parser.add_argument(
        "--no-quarantine",
        action="store_true",
        help="Skip the quarantined launches (Gatekeeper may show a dialog for them)",
    )
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("This check needs macOS", file=sys.stderr)
        return 2
    for name in MODELS:
        if not (args.models / name).is_file():
            print(f"Missing {name} in the models folder", file=sys.stderr)
            return 2
    out = args.out.resolve()
    out.mkdir(parents=True)
    new = args.new.resolve()
    harness = Harness(out, args.models.resolve(), (args.old or args.new).resolve(), new)
    harness.first_run()
    harness.old_probe_defect()
    harness.upgrade()
    harness.remove_reinstall()
    home = harness.moved()
    if not args.no_quarantine:
        harness.quarantined(home)
    rows = [asdict(row) for row in harness.rows]
    (out / "results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    for row in harness.rows:
        print(f"[{row.result}] {row.scenario} | {row.step} | {row.observed}")
    failed = [row for row in harness.rows if row.result == "fail"]
    print(f"{len(harness.rows)} rows, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
