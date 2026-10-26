"""Smoke tests for the M0 application shell."""

import pytest

from dusty import __version__
from dusty.__main__ import create_window, main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"Dusty {__version__}"


def test_window_title(qtbot) -> None:
    window = create_window()
    qtbot.addWidget(window)
    window.show()
    assert window.windowTitle() == "Dusty"
