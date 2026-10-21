"""Run pinned converters twice and emit one model manifest fragment."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

LIMIT = 2 * 1024**3


def digest(path: Path) -> str:
    hash_value = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8 * 1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def one_conversion(whisper_cpp: Path, openai: Path, work: Path, vad: bool) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    if vad:
        run(
            sys.executable,
            str(whisper_cpp / "models/convert-silero-vad-to-ggml.py"),
            "--output",
            str(work / "ggml-silero.bin"),
        )
        results = list(work.glob("ggml-silero-*.bin"))
        if len(results) != 1:
            raise ValueError("Silero converter did not produce one model")
        return results[0]
    run(
        sys.executable,
        str(whisper_cpp / "models/convert-pt-to-ggml.py"),
        str(work.parent / "model.pt"),
        str(openai),
        str(work),
    )
    result = work / "ggml-model.bin"
    if not result.is_file():
        raise ValueError("Whisper converter output missing")
    return result


def main() -> None:
    model = sys.argv[1]
    quant = sys.argv[2]
    whisper_cpp = Path("build/upstream-whisper").resolve()
    openai = Path("build/upstream-openai").resolve()
    work = Path("build/model-work").resolve()
    package = Path("build/model-package").resolve()
    package.mkdir(parents=True, exist_ok=True)
    vad = model == "silero-vad"
    os.environ["PYTHONPATH"] = str(Path("modelpipeline/offline_site").resolve())
    first = one_conversion(whisper_cpp, openai, work / "first", vad)
    first_hash = digest(first)
    shutil.rmtree(first.parent)
    second = one_conversion(whisper_cpp, openai, work / "second", vad)
    if digest(second) != first_hash:
        raise ValueError("Converter output is not reproducible")
    if not vad:
        (work / "model.pt").unlink()

    if quant == "f16" or vad:
        final = package / ("ggml-silero-vad.bin" if vad else f"ggml-{model}.bin")
        shutil.move(second, final)
    else:
        quantizer = whisper_cpp / "build/bin/whisper-quantize"
        if not quantizer.is_file():
            raise ValueError("Quantizer binary missing")
        first_quant = work / "first-quant.bin"
        run(str(quantizer), str(second), str(first_quant), quant)
        quant_hash = digest(first_quant)
        first_quant.unlink()
        final = package / f"ggml-{model}-{quant}.bin"
        run(str(quantizer), str(second), str(final), quant)
        if digest(final) != quant_hash:
            raise ValueError("Quantizer output is not reproducible")
    if final.stat().st_size >= LIMIT:
        raise ValueError("Model asset is 2 GiB or larger")
    if vad:
        entry = {
            "id": "silero-vad",
            "file_name": final.name,
            "size_bytes": final.stat().st_size,
            "sha256": digest(final),
            "url": f"https://github.com/dusty-corporation/dusty/releases/download/models-v1/{final.name}",
            "source": {
                "silero_vad_version": "6.2.3",
                "whisper_cpp_commit": "d1be6fde11ac6e0407606b4e42fe72d34add8037",
            },
        }
    else:
        source = json.loads(Path("modelpipeline/model_sources.json").read_text(encoding="utf-8"))[
            model
        ]
        entry = {
            "id": f"{model}-{quant}",
            "display_name": model.replace("-", " ").title(),
            "description": "M1 benchmark candidate",
            "file_name": final.name,
            "size_bytes": final.stat().st_size,
            "sha256": digest(final),
            "url": f"https://github.com/dusty-corporation/dusty/releases/download/models-v1/{final.name}",
            "multilingual": not model.endswith(".en"),
            "supports_translate": model != "large-v3-turbo" and not model.endswith(".en"),
            "english_only": model.endswith(".en"),
            "quantization": quant,
            "source": {
                "openai_pt_url": source["url"],
                "openai_pt_sha256": source["sha256"],
                "whisper_cpp_commit": "d1be6fde11ac6e0407606b4e42fe72d34add8037",
                "converter": "models/convert-pt-to-ggml.py",
            },
            "recommended_min_ram_gb": 8,
        }
    Path("fragment.json").write_text(
        json.dumps({"vad" if vad else "model": entry}) + "\n", encoding="utf-8"
    )
    print(f"Converted {model} {quant}: {final.stat().st_size} bytes, SHA-256 {digest(final)}")


if __name__ == "__main__":
    main()
