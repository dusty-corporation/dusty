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


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_disabled_controls_have_gray_borders_and_legible_text_in_render(qapp, qtbot, theme):
    from PySide6.QtGui import QStandardItem, QStandardItemModel
    from PySide6.QtWidgets import QLabel

    from dusty.app.theme import DISABLED_COLORS

    apply_theme(qapp, theme)
    colors = DISABLED_COLORS[theme]
    assert contrast_ratio(colors["ink"], colors["background"]) >= 4.5
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    controls = [
        QPushButton(text)
        for text in ("Start", "Download", "Delete", "Verify all", "Cancel download")
    ]
    controls[0].setObjectName("startButton")
    controls += [
        QToolButton(),
        QComboBox(),
        QSpinBox(),
        QPlainTextEdit(),
        QCheckBox("Skip long silences"),
        QRadioButton("Replace"),
        QTableView(),
        QScrollArea(),
    ]
    controls[5].setText("Options")
    controls[6].addItem("Small")
    controls[8].setPlainText("Vocabulary")
    model = QStandardItemModel(controls[11])
    model.appendRow(QStandardItem("Recording"))
    controls[11].setModel(model)
    controls[12].setWidget(QLabel("Options"))
    for control in controls:
        layout.addWidget(control)
        control.setEnabled(False)
    host.resize(500, 750)
    host.show()
    qtbot.wait(20)
    for control in controls:
        image = control.grab().toImage()
        pixels = {
            image.pixelColor(x, y).name()
            for x in range(image.width())
            for y in range(image.height())
        }
        assert colors["edge"] in pixels, type(control).__name__
        # Rasterizers blend thin glyphs differently. Require actual glyph pixels
        # close to the intended gray AND at least 4.5:1 rendered contrast.
        # Neither background nor border can satisfy this color-distance bound.
        ink = tuple(int(colors["ink"][i : i + 2], 16) for i in (1, 3, 5))
        glyphs = [
            pixel
            for pixel in pixels
            if max(
                abs(int(pixel[i : i + 2], 16) - channel)
                for i, channel in zip((1, 3, 5), ink, strict=True)
            )
            <= 12
        ]
        assert glyphs, type(control).__name__
        assert max(contrast_ratio(pixel, colors["background"]) for pixel in glyphs) >= 4.5
    apply_theme(qapp, "light")
