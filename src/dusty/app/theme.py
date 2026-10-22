"""Readable light/dark Qt palettes without an external styling dependency."""

import os
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication


def application_icon() -> QIcon:
    """Original waveform mark drawn with the already-used Qt GUI module."""
    icon = QIcon()
    for size in (16, 32, 64):
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#256847"))
        painter.drawRoundedRect(QRectF(0, 0, size, size), size / 4, size / 4)
        painter.setBrush(QColor("#eff5e7"))
        for x, height in ((0.24, 0.25), (0.41, 0.58), (0.58, 0.40), (0.75, 0.18)):
            painter.drawRoundedRect(
                QRectF(size * (x - 0.045), size * (1 - height) / 2, size * 0.09, size * height),
                size * 0.04,
                size * 0.04,
            )
        painter.end()
        icon.addPixmap(image)
    return icon


def apply_theme(app: QApplication, mode: str = "system") -> None:
    # The Windows offscreen plugin has no system font enumeration. Read the
    # installed Windows font for test/render parity; never bundle a font file.
    if app.platformName() == "offscreen" and not QFontDatabase.families():
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf"):
            if (fonts / name).is_file():
                QFontDatabase.addApplicationFont(str(fonts / name))
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    if mode == "system":
        mode = "dark" if app.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
    dark = mode == "dark"
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#19231f" if dark else "#f6f8f7",
        QPalette.ColorRole.WindowText: "#edf4ef" if dark else "#182c24",
        QPalette.ColorRole.Base: "#101a16" if dark else "#ffffff",
        QPalette.ColorRole.AlternateBase: "#23332b" if dark else "#edf3ef",
        QPalette.ColorRole.Text: "#edf4ef" if dark else "#182c24",
        QPalette.ColorRole.Button: "#2a3c32" if dark else "#edf3ef",
        QPalette.ColorRole.ButtonText: "#edf4ef" if dark else "#182c24",
        QPalette.ColorRole.Highlight: "#367c5d" if dark else "#256847",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#23332b" if dark else "#ffffff",
        QPalette.ColorRole.ToolTipText: "#edf4ef" if dark else "#182c24",
        QPalette.ColorRole.PlaceholderText: "#a6b9ad" if dark else "#63766a",
        QPalette.ColorRole.Link: "#8ed4b0" if dark else "#185d3b",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#87968d"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#87968d"))
    app.setPalette(palette)
    edge = "#486352" if dark else "#c7d8ce"
    app.setStyleSheet(f"""
        QMainWindow, QDialog {{ background: {colors[QPalette.ColorRole.Window]}; }}
        QPushButton {{ padding: 8px 14px; border: 1px solid {edge}; border-radius: 6px; }}
        QPushButton#startButton {{ background: #256847; color: white;
            font-weight: 600; padding: 12px 32px; }}
        QPushButton#startButton:disabled {{ background: {edge}; color: #edf3ef; }}
        QFrame#dropArea {{ border: 2px dashed {edge}; border-radius: 12px; }}
        QLabel#title {{ font-size: 24px; font-weight: 600; }}
        QLabel#dropTitle {{ font-size: 18px; font-weight: 600; }}
        QLabel#warning {{ color: {"#ffd794" if dark else "#805319"}; }}
        QComboBox, QSpinBox, QPlainTextEdit {{ padding: 5px; }}
        QTableView {{ border: 1px solid {edge}; border-radius: 6px; gridline-color: {edge}; }}
        QProgressBar {{ min-height: 12px; border: 1px solid {edge};
            border-radius: 4px; text-align: center; }}
        QProgressBar::chunk {{ background: #367c5d; }}
        QToolButton {{ padding: 6px; }}
    """)
