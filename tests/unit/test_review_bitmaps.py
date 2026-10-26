"""Review image conversion must preserve native pixels and dimensions."""

from PySide6.QtGui import QColor, QImage

from tools.review_bitmaps import convert


def test_native_review_png_conversion_is_lossless(tmp_path):
    image = QImage(48, 32, QImage.Format.Format_RGB32)
    image.fill(QColor("#18342a"))
    image.setPixelColor(3, 7, QColor("#ffb000"))
    assert image.save(str(tmp_path / "models.bmp"))
    convert(tmp_path)
    actual = QImage(str(tmp_path / "models.png"))
    assert actual.size() == image.size()
    assert actual == image
