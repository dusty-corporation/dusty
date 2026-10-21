# 0014 - PyInstaller bootloader license exception
- Status: Accepted by PM
- Date: 2026-10-21
## Context
The PyInstaller bootloader is GPL-2.0-or-later with the PyInstaller bootloader exception. Its special exception permits bundling the bootloader into programs under any license, despite the general GPL prohibition in SPEC §10.2.
## Decision
Allow only the `pyinstaller-bootloader` component when its license is recorded exactly as `GPL-2.0-or-later WITH PyInstaller-bootloader-exception`. Keep all other GPL components forbidden. The release inventory must identify the bootloader separately from other bundled components.
## Consequences
The license checker recognizes this exact component and expression. M5 must verify the packaged bootloader and include its notice and exception text.
## Alternatives considered
Forbid the bootloader and change packaging; unnecessary given the explicit exception.
