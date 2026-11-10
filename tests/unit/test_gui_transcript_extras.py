"""The Options row for time markers and words that may be wrong, on both platforms."""

from pathlib import Path

import pytest
from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QValidator

from dusty.app import messages as M
from dusty.app.window import MainWindow, MinutesBox
from dusty.app.workers import Prepared
from dusty.core import BatchOptions, Job
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def window(qtbot, tmp_path: Path):
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    view = MainWindow(paths, interactive=False)
    qtbot.addWidget(view)
    view.apply_prepared(
        Prepared(
            tuple(view.registry.manifest.models),
            False,
            {"schema_version": 1, "welcome_seen": True},
            vad_installed=True,
        )
    )
    view.output_dir = tmp_path / "out"
    view.show()
    view._refresh()
    return view


def test_extras_are_off_by_default_and_their_details_wait(window) -> None:
    assert not window.time_markers.isChecked() and not window.mark_unsure.isChecked()
    assert window.time_markers.isEnabled() and window.mark_unsure.isEnabled()
    assert not window.marker_minutes.isEnabled()
    assert window.marker_minutes.value() == 5.0
    assert window.unsure_buttons["very"].isChecked()
    assert not any(button.isEnabled() for button in window.unsure_buttons.values())
    assert "00:05:00, 00:10:00" in window.markers_help.text()
    summary = window.choices_summary.text()
    assert "time markers" not in summary and M.UNSURE_ON not in summary
    options = window.batch_options()
    assert not options.time_markers and not options.mark_unsure


def test_choices_reach_the_batch_and_the_summary(window) -> None:
    window.time_markers.setChecked(True)
    assert window.marker_minutes.isEnabled()
    window.marker_minutes.setValue(5.4)
    assert "00:05:24, 00:10:48" in window.markers_help.text()
    window.mark_unsure.setChecked(True)
    assert all(button.isEnabled() for button in window.unsure_buttons.values())
    window.unsure_buttons["somewhat"].setChecked(True)
    options = window.batch_options()
    assert options.time_markers and options.marker_minutes == 5.4
    assert options.mark_unsure and options.unsure_level == "somewhat"
    summary = window.choices_summary.text()
    expected = M.MARKERS_ON.format(minutes=window.marker_minutes.text())
    assert expected in summary and M.UNSURE_ON in summary


def test_extras_wait_for_text_or_word_output(window) -> None:
    window.time_markers.setChecked(True)
    window.mark_unsure.setChecked(True)
    window.formats["json"].setChecked(True)
    window.formats["txt"].setChecked(False)
    window.formats["docx"].setChecked(False)
    assert not window.time_markers.isEnabled() and not window.mark_unsure.isEnabled()
    assert not window.marker_minutes.isEnabled()
    assert window.extras_unavailable.isVisibleTo(window.options_dialog)
    assert "time markers" not in window.choices_summary.text()
    window.formats["docx"].setChecked(True)
    assert window.marker_minutes.isEnabled()
    assert not window.extras_unavailable.isVisibleTo(window.options_dialog)


def test_extras_are_remembered(window, qtbot, tmp_path) -> None:
    window.time_markers.setChecked(True)
    window.marker_minutes.setValue(12.5)
    window.mark_unsure.setChecked(True)
    window.unsure_buttons["somewhat"].setChecked(True)
    assert window._save_settings()
    saved = dict(window.settings)
    assert saved["time_markers"] is True and saved["marker_minutes"] == 12.5
    assert saved["mark_unsure"] is True and saved["unsure_level"] == "somewhat"
    fresh = MainWindow(window.paths, interactive=False)
    qtbot.addWidget(fresh)
    fresh.apply_prepared(
        Prepared(tuple(fresh.registry.manifest.models), False, saved, vad_installed=True)
    )
    assert fresh.time_markers.isChecked() and fresh.marker_minutes.value() == 12.5
    assert fresh.mark_unsure.isChecked() and fresh.unsure_buttons["somewhat"].isChecked()


def test_settings_from_1_1_3_leave_extras_off(window, qtbot) -> None:
    fresh = MainWindow(window.paths, interactive=False)
    qtbot.addWidget(fresh)
    old = {"schema_version": 1, "welcome_seen": True, "vad": False, "formats": ["txt"]}
    fresh.apply_prepared(
        Prepared(tuple(fresh.registry.manifest.models), False, old, vad_installed=True)
    )
    assert not fresh.time_markers.isChecked() and not fresh.mark_unsure.isChecked()
    assert fresh.marker_minutes.value() == 5.0 and fresh.unsure_buttons["very"].isChecked()


def test_resumed_batch_restores_its_extras(window, tmp_path) -> None:
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        time_markers=True,
        marker_minutes=0.5,
        mark_unsure=True,
        unsure_level="somewhat",
    )
    window.restore_batch(options, [Job(tmp_path / "a.wav")])
    assert window.batch_options() == options


def test_extras_controls_have_names_for_assistive_technology(window) -> None:
    for widget in (
        window.time_markers,
        window.marker_minutes,
        window.mark_unsure,
        *window.unsure_buttons.values(),
    ):
        assert widget.accessibleName()


def type_text(widget, text: str) -> None:
    """Type each character as a key press, as a keyboard or input method does.

    qtbot.keyClicks aborts on characters outside Latin-1, such as Persian digits.
    """
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    for char in text:
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            event = QKeyEvent(kind, Qt.Key.Key_unknown, Qt.KeyboardModifier.NoModifier, char)
            QApplication.sendEvent(widget, event)


@pytest.fixture
def minutes(qtbot):
    def make(language: QLocale.Language | str) -> MinutesBox:
        box = MinutesBox()
        box.setLocale(QLocale(language))
        box.setValue(5)
        qtbot.addWidget(box)
        box.show()
        return box

    return make


@pytest.mark.parametrize(
    ("text", "state"),
    [
        ("5", QValidator.State.Acceptable),
        ("5.4", QValidator.State.Acceptable),
        ("5,4", QValidator.State.Acceptable),
        ("0.5", QValidator.State.Acceptable),
        ("120", QValidator.State.Acceptable),
        ("5.25", QValidator.State.Acceptable),
        ("", QValidator.State.Intermediate),
        ("5.", QValidator.State.Intermediate),
        ("0.2", QValidator.State.Intermediate),
        ("200", QValidator.State.Intermediate),
        ("5.255", QValidator.State.Invalid),
        ("abc", QValidator.State.Invalid),
        ("-5", QValidator.State.Invalid),
        ("5.4.1", QValidator.State.Invalid),
        ("1e2", QValidator.State.Invalid),
    ],
)
def test_minutes_accept_either_decimal_separator(minutes, text, state) -> None:
    box = minutes(QLocale.Language.English)
    assert box.validate(text, len(text))[0] == state


@pytest.mark.parametrize("typed", ["5,4", "5.4"])
def test_minutes_typed_in_french_show_a_comma(minutes, qtbot, typed) -> None:
    box = minutes(QLocale.Language.French)
    box.lineEdit().selectAll()
    qtbot.keyClicks(box.lineEdit(), typed)
    qtbot.keyClick(box.lineEdit(), Qt.Key.Key_Return)
    assert box.value() == pytest.approx(5.4)
    assert box.text() == "5,4"


def test_minutes_never_keep_an_empty_or_out_of_range_value(minutes, qtbot) -> None:
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtWidgets import QApplication

    box = minutes(QLocale.Language.English)
    box.setValue(7.5)
    for typed in ("", "300", "0.1", "1."):
        box.lineEdit().selectAll()
        box.lineEdit().del_()
        qtbot.keyClicks(box.lineEdit(), typed)
        qtbot.keyClick(box.lineEdit(), Qt.Key.Key_Return)
        QApplication.sendEvent(box, QFocusEvent(QEvent.Type.FocusOut))
        assert box.value() == 7.5
        assert box.text() == "7.5"


@pytest.mark.parametrize(
    ("name", "shown"), [("fa_IR", "۵٫۴"), ("ar_EG", "٥٫٤"), ("de_DE", "5,4"), ("en_US", "5.4")]
)
def test_minutes_accept_their_own_text_in_every_language(minutes, qtbot, name, shown) -> None:
    box = minutes(name)
    box.setValue(5.4)
    assert box.text() == shown
    assert box.validate(shown, len(shown))[0] == QValidator.State.Acceptable
    unfinished = shown[:-1]
    assert box.validate(unfinished, len(unfinished))[0] == QValidator.State.Intermediate
    box.setValue(7)
    box.lineEdit().selectAll()
    type_text(box.lineEdit(), shown)
    qtbot.keyClick(box.lineEdit(), Qt.Key.Key_Return)
    assert box.value() == pytest.approx(5.4)
    assert box.text() == shown


@pytest.mark.parametrize("typed", ["5.4", "5,4", "۵٫۴", "۵.۴", "٥٫٤"])
def test_minutes_on_a_persian_computer_take_any_usual_separator(minutes, qtbot, typed) -> None:
    box = minutes("fa_IR")
    box.lineEdit().selectAll()
    type_text(box.lineEdit(), typed)
    qtbot.keyClick(box.lineEdit(), Qt.Key.Key_Return)
    assert box.value() == pytest.approx(5.4)
    assert box.text() == "۵٫۴"


def test_minutes_range_help_uses_the_computers_digits(window) -> None:
    from PySide6.QtCore import QLocale as Locale

    window.marker_minutes.setLocale(Locale("fa_IR"))
    window.marker_minutes.setValue(6)
    assert "۰٫۵" in window.markers_help.text() and "۱۲۰" in window.markers_help.text()
