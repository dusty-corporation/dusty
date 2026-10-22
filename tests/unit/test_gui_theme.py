"""Verify visible interactive boundaries and theme contrast, not just text colors."""

import pytest
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dusty.app.theme import CONTROL_COLORS, apply_theme, contrast_ratio


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_all_interactive_control_boundaries_have_three_to_one_contrast(qapp, qtbot, theme):
    apply_theme(qapp, theme)
    colors = CONTROL_COLORS[theme]
    for background in ("window", "base", "button"):
        assert contrast_ratio(colors["edge"], colors[background]) >= 3
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    controls = [
        QCheckBox(""),
        QRadioButton(""),
        QPushButton(""),
        QToolButton(),
        QComboBox(),
        QSpinBox(),
        QPlainTextEdit(),
        QTableView(),
        QScrollArea(),
    ]
    for control in controls:
        layout.addWidget(control)
    host.resize(500, 700)
    host.show()
    qtbot.wait(20)
    # Exercise the actual Qt stylesheet painter for every bordered control class.
    edge = colors["edge"].lower()
    for control in controls:
        image = control.grab().toImage()
        assert any(
            image.pixelColor(x, y).name().lower() == edge
            for y in range(image.height())
            for x in range(image.width())
        ), type(control).__name__
    for box in controls[:2]:
        assert not box.isChecked()
        box.click()
        assert box.isChecked()
    apply_theme(qapp, "light")
