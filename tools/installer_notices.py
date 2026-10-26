"""Retain notices and unmodified MPL source for the approved setup runtime."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / "packaging/licenses/inno"


def runtime_notices(bundle: Path) -> str:
    rows = json.loads((LICENSES / "components.json").read_text(encoding="utf-8"))
    text = (bundle / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    text += (
        "\n\n# Installer runtime only (ADR 0023)\n\n"
        "These components are used only in the unmodified upstream Inno runtime, "
        "not in Dusty's processing app or downloader.\n\n"
        "Made using RemObjects Pascal Script: https://www.remobjects.com/ps.aspx\n\n"
        "JEDI source under MPL-1.1 is in installer-jedi-source.zip beside these "
        "notices, with its original notices and full license. No Dusty modifications.\n\n"
        + (LICENSES / "license.txt").read_text(encoding="utf-8")
    )
    for row in rows:
        text += f"\n\n## {row['name']} {row['version']}\n\n{row['source']}\n"
        for link in row.get("source_links", []):
            text += f"\n{link}\n"
        text += "\n" + (LICENSES / row["notice"]).read_text(encoding="utf-8")
    return text + "\n\n" + (LICENSES / "lzma-public-domain.txt").read_text(encoding="utf-8")


def source_archive(sources: Path) -> bytes:
    """Verify reviewed source bytes, then archive exact JEDI units deterministically."""
    import io

    proof = json.loads((LICENSES / "runtime-source.json").read_text(encoding="utf-8"))
    for row in proof["reviewed_files"] + proof["jedi_sources"]:
        if hashlib.sha256((sources / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Pinned Inno source differs from reviewed bytes")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in proof["jedi_sources"]:
            info = zipfile.ZipInfo(Path(row["path"]).name, date_time=(2026, 5, 26, 0, 0, 0))
            archive.writestr(info, (sources / row["path"]).read_bytes())
        archive.writestr(
            zipfile.ZipInfo("LICENSE-and-notices.txt", date_time=(2026, 5, 26, 0, 0, 0)),
            (LICENSES / "jedi-uxtheme.txt").read_bytes(),
        )
    return stream.getvalue()
