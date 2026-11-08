"""Mac start refusals: an unsafe data folder or lease gives a plain message, not a traceback."""

import os
import stat
import sys
from pathlib import Path

import pytest

from dusty.app import messages as M

mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="macOS data folder rules")
pytestmark = mac_only


def _data_folder() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Dusty"


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.fixture
def linked_data_folder(tmp_path) -> Path:
    """The data folder is a symbolic link to a folder that already belongs to us."""
    target = tmp_path / "elsewhere"
    target.mkdir(mode=0o700)
    folder = _data_folder()
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.symlink_to(target, target_is_directory=True)
    return target


@pytest.fixture
def entry_calls(monkeypatch):
    """Record whether real work would have started; nothing native runs here."""
    import dusty.devcli
    import dusty.selftest

    calls: list[str] = []
    monkeypatch.setattr(
        dusty.selftest, "run_selftest", lambda *a, **k: calls.append("self-test") or "OK"
    )
    monkeypatch.setattr(dusty.devcli, "transcribe", lambda *a, **k: calls.append("batch") or 0)
    return calls


@pytest.fixture
def gui_errors(monkeypatch, qapp):
    """Capture the start refusal dialog instead of waiting for a click."""
    from dusty.app.dialogs import ErrorDialog

    shown: list[tuple[str, list[str]]] = []

    def exec_(dialog):
        from PySide6.QtWidgets import QLabel

        shown.append((dialog.windowTitle(), [w.text() for w in dialog.findChildren(QLabel)]))
        return 0

    monkeypatch.setattr(ErrorDialog, "exec", exec_)
    original = (qapp.applicationName(), qapp.organizationName(), qapp.applicationDisplayName())
    yield shown
    qapp.setApplicationName(original[0])
    qapp.setOrganizationName(original[1])
    qapp.setApplicationDisplayName(original[2])


def test_private_user_dir_reports_links_files_and_other_owners(tmp_path, monkeypatch):
    from dusty.__main__ import _private_user_dir

    fresh = tmp_path / "fresh/Dusty"
    assert _private_user_dir(fresh) is True
    assert _mode(fresh) == 0o700
    open_folder = tmp_path / "open/Dusty"
    open_folder.mkdir(parents=True)
    os.chmod(open_folder, 0o755)
    assert _private_user_dir(open_folder) is True
    assert _mode(open_folder) == 0o700
    target = tmp_path / "target"
    target.mkdir()
    os.chmod(target, 0o755)
    link = tmp_path / "link/Dusty"
    link.parent.mkdir()
    link.symlink_to(target, target_is_directory=True)
    assert _private_user_dir(link) is False
    assert _mode(target) == 0o755  # A link is never followed or changed.
    plain = tmp_path / "file/Dusty"
    plain.parent.mkdir()
    plain.write_text("public", encoding="utf-8")
    assert _private_user_dir(plain) is False
    assert plain.read_text(encoding="utf-8") == "public"
    foreign = tmp_path / "foreign/Dusty"
    foreign.mkdir(parents=True)
    os.chmod(foreign, 0o755)
    real_uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real_uid + 1)  # Owned by another user.
    assert _private_user_dir(foreign) is False
    monkeypatch.undo()
    assert _mode(foreign) == 0o755  # Another owner's folder is left alone.


@pytest.mark.parametrize(
    "argv",
    [["--self-test"], ["--headless-batch", "lecture.wav", "--out", "out"]],
    ids=["self-test", "headless-batch"],
)
def test_command_line_entry_refuses_linked_data_folder(
    argv, linked_data_folder, entry_calls, capsys
):
    from dusty.__main__ import main

    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == M.DATA_FOLDER_UNSAFE
    assert "Traceback" not in captured.err and str(linked_data_folder) not in captured.err
    assert entry_calls == []
    assert _mode(linked_data_folder) == 0o700 and not list(linked_data_folder.iterdir())


@pytest.mark.parametrize(
    ("argv", "work"),
    [
        (["--self-test"], "self-test"),
        (["--headless-batch", "lecture.wav", "--out", "out"], "batch"),
    ],
    ids=["self-test", "headless-batch"],
)
def test_command_line_entry_creates_private_data_folder(argv, work, entry_calls, tmp_path):
    from dusty.__main__ import main

    folder = _data_folder()
    assert not folder.exists()
    assert main(argv) == 0
    assert entry_calls == [work]
    assert stat.S_ISDIR(os.lstat(folder).st_mode) and _mode(folder) == 0o700


def test_headless_batch_without_output_stops_before_creating_data_folder(entry_calls):
    from dusty.__main__ import main

    with pytest.raises(SystemExit) as stopped:
        main(["--headless-batch", "lecture.wav"])
    assert stopped.value.code == 2
    assert not _data_folder().exists() and entry_calls == []


def test_gui_refuses_linked_data_folder_with_a_dialog(
    linked_data_folder, gui_errors, monkeypatch, capsys
):
    from dusty.__main__ import main
    from dusty.platform import mac_instance

    def no_lease(*args, **kwargs):
        raise AssertionError("The lease must not be opened through a link")

    monkeypatch.setattr(mac_instance, "GuiInstance", no_lease)
    assert main([]) == 1
    assert gui_errors == [(M.ERROR_TITLE, [M.DATA_FOLDER_UNSAFE])]
    assert "Traceback" not in capsys.readouterr().err


def test_gui_reports_a_lease_error_instead_of_a_traceback(gui_errors, monkeypatch, capsys):
    from dusty.__main__ import main
    from dusty.platform import mac_instance

    seen = []

    def broken(user_dir):
        seen.append(_mode(user_dir))
        raise OSError("GUI instance control state is unavailable or unsafe")

    monkeypatch.setattr(mac_instance, "GuiInstance", broken)
    assert main([]) == 1
    assert seen == [0o700]  # The folder was made private before the lease.
    assert gui_errors == [(M.ERROR_TITLE, [M.INSTANCE_UNAVAILABLE])]
    error = capsys.readouterr().err
    assert error.strip() == M.INSTANCE_UNAVAILABLE and "Traceback" not in error


def test_gui_refuses_data_folder_owned_by_another_user(gui_errors, monkeypatch):
    from dusty.__main__ import main
    from dusty.platform import mac_instance

    folder = _data_folder()
    folder.mkdir(parents=True, mode=0o700)
    real_uid = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real_uid + 1)
    monkeypatch.setattr(mac_instance, "GuiInstance", lambda *a: pytest.fail("lease opened"))
    assert main([]) == 1
    assert gui_errors == [(M.ERROR_TITLE, [M.DATA_FOLDER_UNSAFE])]


def test_real_lease_refusal_through_main_is_reported(gui_errors, monkeypatch):
    """A real unsafe lease state (a world-readable control folder) gives the message."""
    from dusty.__main__ import main

    folder = _data_folder()
    folder.mkdir(parents=True, mode=0o700)
    control = folder / ".gui-instance"
    control.mkdir(mode=0o755)
    os.chmod(control, 0o755)
    assert main([]) == 1
    assert gui_errors == [(M.ERROR_TITLE, [M.INSTANCE_UNAVAILABLE])]
    assert _mode(control) == 0o755  # Nothing is repaired or removed behind the user.


def test_gui_second_launch_still_exits_zero_through_the_private_folder(monkeypatch):
    from dusty.__main__ import main
    from dusty.platform.mac_instance import GuiInstance

    owner = GuiInstance(_private_folder())
    try:
        assert owner.owner
        assert main([]) == 0  # A second launch asks the owner to activate, then exits.
        assert owner.activation_requested()
    finally:
        owner.close()


def _private_folder() -> Path:
    from dusty.__main__ import _private_user_dir

    folder = _data_folder()
    assert _private_user_dir(folder)
    return folder


class _Lease:
    def __init__(self, result):
        self.result = result

    def activation_requested(self) -> bool:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class _Timer:
    active = True

    def stop(self) -> None:
        self.active = False


@pytest.mark.parametrize("requested", [True, False])
def test_activation_poll_raises_the_window_only_when_asked(requested):
    from dusty.__main__ import _poll_activation

    raised, timer = [], _Timer()
    _poll_activation(_Lease(requested), "window", timer, raised.append, mac=True)
    assert raised == (["window"] if requested else []) and timer.active


def test_activation_poll_stops_quietly_when_the_mac_lease_breaks():
    from dusty.__main__ import _poll_activation

    raised, timer = [], _Timer()
    lease = _Lease(OSError("GUI instance control state is unavailable or unsafe"))
    _poll_activation(lease, "window", timer, raised.append, mac=True)
    assert raised == [] and not timer.active
    with pytest.raises(OSError):  # Other platforms keep their earlier behavior.
        _poll_activation(lease, "window", _Timer(), raised.append, mac=False)
