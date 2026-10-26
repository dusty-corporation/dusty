# Dependency pins and shipped scope

Python is restricted to 3.12 by `.python-version` and `pyproject.toml`; `uv sync --python 3.12` selected CPython 3.12.11 in this environment. `uv.lock` pins transitive packages and artifact hashes.

| Role | Package | Pinned version |
|------|---------|----------------|
| Runtime GUI | PySide6 | 6.9.2 |
| Test-only DOCX openability | python-docx | 1.2.0 |
| Tests | pytest | 8.4.2 |
| Qt tests | pytest-qt | 4.5.0 |
| Lint and format | ruff | 0.13.1 |
| Types | mypy | 1.18.2 |
| Packaging | PyInstaller | 6.16.0 |
| SBOM | cyclonedx-bom | 7.1.0 |
| License inventory | pip-licenses | 5.0.0 |
| Build backend | hatchling | 1.27.0 |

PySide6 offers LGPL-3.0 as a license alternative and is intended for dynamic linking in the later `--onedir` package. Development tools are not shipped as runtime libraries. M0's license check audits the locked runtime dependency graph; release packaging must additionally audit every bundled binary and resource.

ADR 0019 replaced runtime python-docx/lxml with the standard-library DOCX writer.
Neither package is shipped. The actual bundle inventory, not this summary, drives
notices, SBOM and the license gate. ADRs 0014 and 0020 to 0023 cover the narrow
bootloader, Microsoft runtime, platform-import and installer-only exceptions.
