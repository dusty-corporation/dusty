"""Documentation contracts must fail when labels, approved claims or links drift."""

import shutil

import pytest

from tools.check_docs import ROOT, check


def test_user_documentation_matches_current_ui_and_approved_wording():
    assert check() == []


@pytest.mark.parametrize("damage", ["label", "wording", "link", "catalog"])
def test_docs_checker_rejects_drift(tmp_path, damage):
    shutil.copytree(ROOT / "docs", tmp_path / "docs")
    for name in ("README.md", "CONTRIBUTING.md", "LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / name, tmp_path / name)
    file = tmp_path / "docs/user/faq.md"
    text = file.read_text(encoding="utf-8")
    if damage == "label":
        text += "\nPress **Imaginary app control**.\n"
    elif damage == "wording":
        text = text.replace("It is not certified as HIPAA-compliant", "Invented compliance claim")
    elif damage == "link":
        text += "\n[Missing guide](missing-guide.md)\n"
    else:
        file = tmp_path / "docs/user/models.md"
        text = file.read_text(encoding="utf-8").replace("Tiny: Fastest", "Tiny: changed")
    file.write_text(text, encoding="utf-8")
    assert check(tmp_path)
