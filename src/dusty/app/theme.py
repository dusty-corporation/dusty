"""Readable light/dark Qt palettes without an external styling dependency."""

import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle

CONTROL_COLORS = {
    "light": {"edge": "#68796f", "window": "#f6f8f7", "base": "#ffffff", "button": "#edf3ef"},
    "dark": {"edge": "#9eafa5", "window": "#19231f", "base": "#101a16", "button": "#2a3c32"},
}


def contrast_ratio(first: str, second: str) -> float:
    """WCAG sRGB relative luminance ratio for control-boundary verification."""

    def luminance(value: str) -> float:
        color = QColor(value)
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    a, b = sorted((luminance(first), luminance(second)))
    return (b + 0.05) / (a + 0.05)


class ControlStyle(QProxyStyle):
    """Keep check marks and arrows visible while drawing high-contrast boundaries."""

    def drawPrimitive(self, element, option, painter, widget=None):
        checks = (
            QStyle.PrimitiveElement.PE_IndicatorCheckBox,
            QStyle.PrimitiveElement.PE_IndicatorRadioButton,
        )
        if element in checks:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(option.rect).adjusted(1, 1, -1, -1)
            checked = bool(option.state & QStyle.StateFlag.State_On)
            dark = option.palette.window().color().lightness() < 128
            edge = QColor(CONTROL_COLORS["dark" if dark else "light"]["edge"])
            accent = QColor("#8ed4b0" if dark else "#185d3b")
            painter.setPen(QPen(edge, 2))
            painter.setBrush(option.palette.base())
            if element == QStyle.PrimitiveElement.PE_IndicatorRadioButton:
                painter.drawEllipse(rect)
                if checked:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(accent)
                    painter.drawEllipse(rect.adjusted(3, 3, -3, -3))
            else:
                painter.drawRoundedRect(rect, 2, 2)
                if checked:
                    painter.setPen(QPen(accent, 2))
                    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
                    painter.drawPolyline(
                        QPolygonF(
                            [
                                QPointF(x + w * 0.18, y + h * 0.5),
                                QPointF(x + w * 0.42, y + h * 0.75),
                                QPointF(x + w * 0.85, y + h * 0.2),
                            ]
                        )
                    )
            painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)


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
    app.setStyle(ControlStyle("Fusion"))
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
    edge = CONTROL_COLORS["dark" if dark else "light"]["edge"]
    disabled_start_ink = "#23372c" if dark else "#edf3ef"
    base = colors[QPalette.ColorRole.Base]
    button = colors[QPalette.ColorRole.Button]
    ink = colors[QPalette.ColorRole.Text]
    accent = "#8ed4b0" if dark else "#185d3b"
    app.setStyleSheet(f"""
        QMainWindow, QDialog {{ background: {colors[QPalette.ColorRole.Window]}; }}
        QPushButton {{ background: {button}; color: {ink}; padding: 8px 14px;
            border: 1px solid {edge}; border-radius: 6px; }}
        QPushButton#startButton, QPushButton#primaryButton {{ background: #256847; color: white;
            font-weight: 600; padding: 12px 32px; }}
        QPushButton#startButton:disabled {{ background: {edge}; color: {disabled_start_ink}; }}
        QFrame#dropArea {{ border: 2px dashed {edge}; border-radius: 12px; }}
        QLabel#title {{ font-size: 24px; font-weight: 600; }}
        QLabel#dropTitle {{ font-size: 18px; font-weight: 600; }}
        QLabel#warning {{ color: {"#ffd794" if dark else "#805319"}; }}
        QComboBox, QSpinBox, QPlainTextEdit {{ padding: 5px; background: {base};
            color: {ink}; border: 1px solid {edge}; border-radius: 4px; }}
        QComboBox QAbstractItemView, QMenu {{ background: {base}; color: {ink};
            border: 1px solid {edge}; }}
        QComboBox QAbstractItemView::item:disabled {{ color: #87968d; background: {base}; }}
        QCheckBox, QRadioButton {{ spacing: 8px; }}
        QPushButton:focus, QToolButton:focus, QComboBox:focus, QSpinBox:focus,
        QPlainTextEdit:focus, QTableView:focus {{ border: 2px solid {accent}; }}
        QCheckBox:focus, QRadioButton:focus {{ outline: 2px solid {accent}; }}
        QScrollArea {{ border: 1px solid {edge}; }}
        QScrollBar {{ background: {base}; }}
        QScrollBar::handle {{ background: {edge}; min-width: 20px; min-height: 20px; }}
        QTableView {{ border: 1px solid {edge}; border-radius: 6px; gridline-color: {edge}; }}
        QProgressBar {{ min-height: 12px; border: 1px solid {edge};
            border-radius: 4px; text-align: center; }}
        QProgressBar::chunk {{ background: #367c5d; }}
        QToolButton {{ padding: 6px; background: {button}; color: {ink};
            border: 1px solid {edge}; border-radius: 4px; }}
    """)
