"""Assemble a development bin_dir and models_dir for the macOS pipeline.

This is a development tool, not packaging. It copies already built local
artifacts, verifies their hashes against committed or recorded trust anchors,
and lays them out the way dusty.engine.binaries expects:

    <out>/ffmpeg/ffmpeg, <out>/ffmpeg/ffprobe
    <out>/cpu/whisper-cli plus the dylibs it loads
    <out>/metal/whisper-cli plus the dylibs it loads
    <out>/lifeline/dusty-lifeline (built by native/macos/build_lifeline.sh)
    <models>/ggml-tiny.bin, <models>/ggml-silero-vad.bin

Each program comes from the newest local build that has it: native-v3 packages
(built by native/macos/build_whisper.sh and build_ffmpeg.sh, verified against
their SHA256SUMS.txt) first. Otherwise ffmpeg and ffprobe come from runtime-v1
(verified against native-runtime-v1.json) and whisper-cli from the native-v2
packages, then the mac0-native build tree.
Dylibs are stored as real files under the exact install names the binaries
load. A build-tree binary with an absolute LC_RPATH gets @loader_path instead
(as native/macos/build_whisper.sh does) and is signed ad hoc again; relocatable
packages are copied unchanged. Nothing is downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "build"
_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}
_RPATH_DEP = re.compile(r"^\s+@rpath/([A-Za-z0-9_.+-]+\.dylib) \(")
_RPATH_CMD = re.compile(r"^\s+path (.+) \(offset \d+\)$")
_SYSTEM_PREFIXES = ("/usr/lib/", "/System/Library/")


class StageError(RuntimeError):
    """The development layout could not be assembled safely."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(args: list[str]) -> str:
    result = subprocess.run(args, env=_ENV, capture_output=True, text=True, check=False)
    if result.returncode:
        raise StageError(f"{Path(args[0]).name} failed with exit code {result.returncode}")
    return result.stdout


def rpath_dependencies(binary: Path) -> list[str]:
    """Install names loaded through @rpath, excluding the dylib's own id."""
    lines = _run(["/usr/bin/otool", "-L", str(binary)]).splitlines()[1:]
    names = [match.group(1) for line in lines if (match := _RPATH_DEP.match(line))]
    own_id = _run(["/usr/bin/otool", "-D", str(binary)]).splitlines()[1:]
    own = {line.strip().removeprefix("@rpath/") for line in own_id}
    return [name for name in names if name not in own]


def absolute_dependencies(binary: Path) -> list[str]:
    lines = _run(["/usr/bin/otool", "-L", str(binary)]).splitlines()[1:]
    return [line.strip().split(" (")[0] for line in lines if line.strip().startswith("/")]


def rpaths(binary: Path) -> list[str]:
    lines = _run(["/usr/bin/otool", "-l", str(binary)]).splitlines()
    found = []
    for index, line in enumerate(lines):
        if line.strip() == "cmd LC_RPATH":
            for candidate in lines[index + 1 : index + 4]:
                match = _RPATH_CMD.match(candidate)
                if match:
                    found.append(match.group(1))
                    break
    return found


def _copy_real(source: Path, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source.resolve(strict=True), target)
    os.chmod(target, mode)


def _make_self_contained(binary: Path) -> None:
    """Point @rpath at the binary's own folder and re-sign ad hoc."""
    current = rpaths(binary)
    if current == ["@loader_path"] or (not current and not rpath_dependencies(binary)):
        return
    args = ["/usr/bin/install_name_tool"]
    for entry in current:
        args += ["-delete_rpath", entry]
    args += ["-add_rpath", "@loader_path", str(binary)]
    _run(args)
    _run(["/usr/bin/codesign", "--force", "--sign", "-", str(binary)])


def stage_ffmpeg(source_build: Path, out: Path) -> list[dict[str, Any]]:
    package = source_build / "macos-arm64/native-v3/ffmpeg/package"
    if (package / "ffmpeg").is_file():
        return stage_ffmpeg_package(package, out)
    runtime = source_build / "macos-arm64/runtime-v1/Contents"
    manifest = json.loads((runtime / "Resources/native-runtime-v1.json").read_text("utf-8"))
    expected = {item["role"]: item for item in manifest["artifacts"]}
    entries = []
    for role in ("ffmpeg", "ffprobe"):
        item = expected.get(role)
        if item is None:
            raise StageError(f"{role} is not listed in native-runtime-v1.json")
        source = runtime / item["path"]
        if source.is_symlink() or not source.is_file():
            raise StageError(f"{role} source is missing or linked")
        if source.stat().st_size != item["size_bytes"] or sha256(source) != item["sha256"]:
            raise StageError(f"{role} does not match native-runtime-v1.json")
        target = out / "ffmpeg" / role
        _copy_real(source, target, 0o755)
        if sha256(target) != item["sha256"]:
            raise StageError(f"{role} copy does not match its source")
        entries.append(
            {"path": f"ffmpeg/{role}", "sha256": item["sha256"], "trust": "native-runtime-v1.json"}
        )
    return entries


def stage_ffmpeg_package(package: Path, out: Path) -> list[dict[str, Any]]:
    """Copy ffmpeg and ffprobe from a build_ffmpeg.sh package, verified by SHA256SUMS.txt."""
    sums_path = package.parent / "SHA256SUMS.txt"
    if not sums_path.is_file():
        raise StageError(f"{sums_path} is missing")
    sums = read_sums(sums_path)
    entries = []
    for role in ("ffmpeg", "ffprobe"):
        source = package / role
        if source.is_symlink() or not source.is_file():
            raise StageError(f"{role} source is missing or linked")
        if sums.get(role) is None or sha256(source) != sums[role]:
            raise StageError(f"{role} does not match SHA256SUMS.txt")
        target = out / "ffmpeg" / role
        _copy_real(source, target, 0o755)
        if sha256(target) != sums[role]:
            raise StageError(f"{role} copy does not match its source")
        entries.append(
            {"path": f"ffmpeg/{role}", "sha256": sums[role], "trust": "native-v3 SHA256SUMS.txt"}
        )
    return entries


def read_sums(path: Path) -> dict[str, str]:
    """Parse a shasum-style SHA256SUMS file into {file name: hash}."""
    sums = {}
    for line in path.read_text("utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise StageError(f"Invalid hash line in {path.name}")
            sums[name.strip().lstrip("*")] = digest
    return sums


def whisper_sources(source_build: Path, backend: str) -> tuple[Path, dict[str, str] | None, str]:
    """Prefer the native-v3 package, then native-v2, then the mac0 build tree."""
    for generation in ("native-v3", "native-v2"):
        package = source_build / f"macos-arm64/{generation}/whisper-{backend}/package"
        if (package / "whisper-cli").is_file():
            sums = package.parent / "SHA256SUMS.txt"
            if generation == "native-v3" and not sums.is_file():
                raise StageError(f"{sums} is missing")
            return package, read_sums(sums) if sums.is_file() else None, generation
    return source_build / f"mac0-native/{backend}/bin", None, "mac0-native"


def stage_whisper(
    source_bin: Path, out: Path, backend: str, sums: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Copy whisper-cli and the closure of @rpath dylibs it loads, as real files.

    When ``sums`` is given, every copied file must match its recorded hash.
    """
    executable = source_bin / "whisper-cli"
    if executable.is_symlink() or not executable.is_file():
        raise StageError(f"{backend} whisper-cli is missing or linked")
    target_dir = out / backend
    pending = ["whisper-cli"]
    seen: set[str] = set()
    sources: dict[str, Path] = {}
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        source = source_bin / name
        if not source.exists():
            raise StageError(f"{backend} dependency {name} is missing")
        sources[name] = source
        pending.extend(rpath_dependencies(source))
    entries = []
    for name in sorted(sources):
        source, target = sources[name], target_dir / name
        _copy_real(source, target, 0o755)
        source_hash = sha256(source.resolve(strict=True))
        if sums is not None and sums.get(name) != source_hash:
            raise StageError(f"{backend}/{name} does not match SHA256SUMS.txt")
        _make_self_contained(target)
        leaks = [
            dep for dep in absolute_dependencies(target) if not dep.startswith(_SYSTEM_PREFIXES)
        ]
        if leaks or any(entry != "@loader_path" for entry in rpaths(target)):
            raise StageError(f"{backend}/{name} still loads code from outside bin_dir")
        missing = [dep for dep in rpath_dependencies(target) if not (target_dir / dep).is_file()]
        if missing:
            raise StageError(f"{backend}/{name} needs unstaged dylibs")
        entries.append(
            {
                "path": f"{backend}/{name}",
                "sha256": sha256(target),
                "source_name": source.resolve(strict=True).name,
                "source_sha256": source_hash,
            }
        )
    used = {path.resolve() for path in sources.values()}
    unused = sorted(
        path.name
        for path in source_bin.iterdir()
        if path.suffix == ".dylib" and not path.is_symlink() and path.resolve() not in used
    )
    if unused:
        print(f"note: {backend} dylibs not loaded by whisper-cli were not staged: {unused}")
    return entries


def stage_lifeline(source_dir: Path, prebuilt: Path | None, out: Path) -> list[dict[str, Any]]:
    target = out / "lifeline/dusty-lifeline"
    if prebuilt is not None:
        if prebuilt.is_symlink() or not prebuilt.is_file():
            raise StageError("Prebuilt lifeline is missing or linked")
        _copy_real(prebuilt, target, 0o755)
        return [{"path": "lifeline/dusty-lifeline", "sha256": sha256(target), "built": False}]
    script = source_dir.parent / "build_lifeline.sh"
    if script.is_file() and (source_dir / "lifeline.c").is_file():
        # The launcher's own build script is the reference recipe; it needs a new folder.
        scratch = out / ".lifeline-build"
        _run(["/bin/bash", str(script), str(scratch)])
        built = scratch / "lifeline/dusty-lifeline"
        if built.is_symlink() or not built.is_file():
            raise StageError("build_lifeline.sh produced no lifeline/dusty-lifeline")
        _copy_real(built, target, 0o755)
        shutil.rmtree(scratch)
        return [{"path": "lifeline/dusty-lifeline", "sha256": sha256(target), "built": True}]
    sources = sorted(source_dir.glob("*.c")) if source_dir.is_dir() else []
    if not sources:
        print(f"note: no lifeline C sources in {source_dir}; lifeline/ was not staged")
        return []
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "/usr/bin/clang",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(target),
            *map(str, sources),
        ]
    )
    os.chmod(target, 0o755)
    return [{"path": "lifeline/dusty-lifeline", "sha256": sha256(target), "built": True}]


def stage_models(source_dir: Path, models_out: Path, catalog: Path) -> list[dict[str, Any]]:
    data = json.loads(catalog.read_text("utf-8"))
    tiny = next(item for item in data["models"] if item["id"] == "tiny")
    vad = data["vad"][0]
    entries = []
    for item in (tiny, vad):
        source = source_dir / item["file_name"]
        if source.is_symlink() or not source.is_file():
            raise StageError(f"{item['file_name']} is missing or linked")
        if source.stat().st_size != item["size_bytes"] or sha256(source) != item["sha256"]:
            raise StageError(f"{item['file_name']} does not match resources/models.json")
        target = models_out / item["file_name"]
        _copy_real(source, target, 0o644)
        if sha256(target) != item["sha256"]:
            raise StageError(f"{item['file_name']} copy does not match its source")
        entries.append(
            {"path": item["file_name"], "sha256": item["sha256"], "trust": "resources/models.json"}
        )
    return entries


def _check_target(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise StageError(f"Refusing to use {path}: not a plain directory")
    if path.is_dir() and any(path.iterdir()):
        raise StageError(f"Refusing to overwrite non-empty {path}")


def _publish(partial: Path, final: Path) -> None:
    if final.is_dir():
        final.rmdir()  # Checked empty before staging began.
    partial.rename(final)


def stage(
    out: Path,
    models_out: Path,
    *,
    source_build: Path = DEFAULT_SOURCE,
    lifeline_source: Path = ROOT / "native/macos/lifeline",
    lifeline_prebuilt: Path | None = None,
    catalog: Path = ROOT / "resources/models.json",
    stage_model_files: bool = True,
) -> dict[str, Any]:
    if sys.platform != "darwin":
        raise StageError("This tool stages macOS binaries and runs only on macOS")
    out, models_out = out.absolute(), models_out.absolute()
    _check_target(out)
    if stage_model_files:
        _check_target(models_out)
    bin_partial = out.with_name(out.name + f".partial-{os.getpid()}")
    models_partial = models_out.with_name(models_out.name + f".partial-{os.getpid()}")
    for partial in (bin_partial, models_partial):
        if partial.exists():
            raise StageError(f"Refusing to reuse leftover {partial}")
    try:
        files = stage_ffmpeg(source_build, bin_partial)
        ffmpeg_origin = "native-v3" if files[0]["trust"].startswith("native-v3") else "runtime-v1"
        native = source_build / "mac0-native"
        whisper_origin = {}
        for backend in ("cpu", "metal"):
            source_bin, sums, origin = whisper_sources(source_build, backend)
            files += stage_whisper(source_bin, bin_partial, backend, sums)
            whisper_origin[backend] = origin + (" (SHA256SUMS verified)" if sums else "")
        files += stage_lifeline(lifeline_source, lifeline_prebuilt, bin_partial)
        models = stage_models(native, models_partial, catalog) if stage_model_files else []
        manifest = {
            "schema": "dusty.dev.mac-stage",
            "version": 1,
            "bin_files": files,
            "model_files": models,
            "whisper_source": whisper_origin,
            "ffmpeg_source": ffmpeg_origin,
            "lifeline_staged": any(entry["path"].startswith("lifeline/") for entry in files),
        }
        (bin_partial / "dev-stage-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        _publish(bin_partial, out)
        if stage_model_files:
            _publish(models_partial, models_out)
    except BaseException:
        for partial in (bin_partial, models_partial):
            if partial.is_dir() and not partial.is_symlink():
                shutil.rmtree(partial)
        raise
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "build/bin")
    parser.add_argument("--models-out", type=Path, default=ROOT / "build/models")
    parser.add_argument("--source-build", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--lifeline-source", type=Path, default=ROOT / "native/macos/lifeline")
    parser.add_argument("--lifeline", type=Path, help="Copy this prebuilt dusty-lifeline instead")
    parser.add_argument(
        "--no-models",
        action="store_true",
        help="Stage bin_dir only, for models already fetched and verified elsewhere",
    )
    args = parser.parse_args(argv)
    try:
        manifest = stage(
            args.out,
            args.models_out,
            source_build=args.source_build,
            lifeline_source=args.lifeline_source,
            lifeline_prebuilt=args.lifeline,
            stage_model_files=not args.no_models,
        )
    except (StageError, OSError, KeyError, ValueError, StopIteration) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for entry in manifest["bin_files"]:
        print(f"bin    {entry['sha256']}  {entry['path']}")
    for entry in manifest["model_files"]:
        print(f"models {entry['sha256']}  {entry['path']}")
    print(
        f"staged bin_dir={args.out}" + ("" if args.no_models else f" models_dir={args.models_out}")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
