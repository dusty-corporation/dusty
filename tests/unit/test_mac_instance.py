"""Exercise local instance ownership and content-free activation on Mac."""

import os
import select
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAC_ONLY = pytest.mark.skipif(sys.platform != "darwin", reason="Darwin file-lock implementation")


def instance(root):
    from dusty.platform.single_instance import GuiInstance

    return GuiInstance(root)


def run_probe(source, *arguments):
    return subprocess.run(
        [sys.executable, "-c", source, *(str(value) for value in arguments)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=15,
    )


@MAC_ONLY
def test_module_import_is_native_lazy_and_dispatches_mac():
    result = run_probe("""
import sys
import dusty.platform.single_instance as boundary
assert 'dusty.platform.windows_instance' not in sys.modules
assert 'dusty.platform.mac_instance' not in sys.modules
from dusty.platform.single_instance import GuiInstance
assert GuiInstance.__module__ == 'dusty.platform.mac_instance'
assert 'dusty.platform.windows_instance' not in sys.modules
""")
    assert result.returncode == 0, result.stderr


@MAC_ONLY
def test_duplicate_signal_coalesces_and_owner_close_recovers(tmp_path):
    first = instance(tmp_path)
    try:
        assert first.owner
        assert not first.activation_requested()
        for _ in range(3):
            second = instance(tmp_path)
            assert not second.owner
            assert not second.activation_requested()
            second.close()
            second.close()
        assert first.activation_requested()
        assert not first.activation_requested()
    finally:
        first.close()
        first.close()
    assert not first.activation_requested()
    replacement = instance(tmp_path)
    try:
        assert replacement.owner and not replacement.activation_requested()
    finally:
        replacement.close()


@MAC_ONLY
def test_distinct_profiles_have_distinct_owners(tmp_path):
    first, second = instance(tmp_path / "first"), instance(tmp_path / "second")
    try:
        assert first.owner and second.owner
    finally:
        first.close()
        second.close()


@MAC_ONLY
def test_real_guard_duplicate_process_and_crash_recovery(tmp_path):
    first = instance(tmp_path)
    try:
        result = run_probe(
            """
from pathlib import Path
import sys
from dusty.privacy.network_guard import install_guard
install_guard()
from dusty.platform.single_instance import GuiInstance
value = GuiInstance(Path(sys.argv[1]))
assert not value.owner
value.close()
""",
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert first.activation_requested() and not first.activation_requested()
    finally:
        first.close()
    result = run_probe(
        """
import os, sys
from pathlib import Path
from dusty.privacy.network_guard import install_guard
install_guard()
from dusty.platform.single_instance import GuiInstance
value = GuiInstance(Path(sys.argv[1]))
assert value.owner
os._exit(0)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    replacement = instance(tmp_path)
    try:
        assert replacement.owner and not replacement.activation_requested()
    finally:
        replacement.close()


@pytest.mark.parametrize("target", ["profile", "directory", "owner", "activation"])
@MAC_ONLY
def test_symlink_control_paths_are_rejected_without_touching_target(tmp_path, target):
    profile = tmp_path / "profile"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"untouched")
    if target == "profile":
        profile.symlink_to(outside, target_is_directory=True)
    else:
        profile.mkdir(mode=0o700)
        control = profile / ".gui-instance"
        if target == "directory":
            control.symlink_to(outside, target_is_directory=True)
        else:
            control.mkdir(mode=0o700)
            (control / target).symlink_to(sentinel)
    with pytest.raises(OSError):
        instance(profile)
    assert sentinel.read_bytes() == b"untouched"
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel"]


@pytest.mark.parametrize("target", ["owner", "activation"])
@MAC_ONLY
def test_nonregular_control_files_are_rejected_without_blocking(tmp_path, target):
    control = tmp_path / ".gui-instance"
    control.mkdir(mode=0o700)
    os.mkfifo(control / target, mode=0o600)
    with pytest.raises(OSError):
        instance(tmp_path)
    assert (control / target).is_fifo()


@pytest.mark.parametrize("target", ["owner", "activation"])
@MAC_ONLY
def test_unknown_control_content_is_preserved(tmp_path, target):
    control = tmp_path / ".gui-instance"
    control.mkdir(mode=0o700)
    path = control / target
    path.write_bytes(b"unknown control data")
    path.chmod(0o600)
    with pytest.raises(OSError):
        instance(tmp_path)
    assert path.read_bytes() == b"unknown control data"


@MAC_ONLY
def test_untrusted_profile_permissions_are_rejected(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir(mode=0o755)
    with pytest.raises(OSError):
        instance(profile)
    assert not list(profile.iterdir())


@MAC_ONLY
def test_stale_activation_is_cleared_only_by_new_owner(tmp_path):
    first = instance(tmp_path)
    other = instance(tmp_path)
    other.close()
    first.close()
    replacement = instance(tmp_path)
    try:
        assert replacement.owner and not replacement.activation_requested()
    finally:
        replacement.close()


def test_window_activation_behavior_is_preserved():
    from dusty.platform.single_instance import activate_window

    calls = []

    class Window:
        def isMinimized(self):
            return True

        def showNormal(self):
            calls.append("normal")

        def show(self):
            calls.append("show")

        def raise_(self):
            calls.append("raise")

        def activateWindow(self):
            calls.append("activate")

    activate_window(Window())
    assert calls == ["normal", "show", "raise", "activate"]


def test_windows_dispatch_returns_selected_original_class_without_loading_mac():
    result = run_probe("""
import sys
from types import ModuleType
import dusty.platform.single_instance as boundary
assert 'dusty.platform.windows_instance' not in sys.modules
selected = ModuleType('dusty.platform.windows_instance')
class Original:
    pass
selected.GuiInstance = Original
sys.modules[selected.__name__] = selected
sys.platform = 'win32'
assert boundary.GuiInstance is Original
assert 'dusty.platform.mac_instance' not in sys.modules
""")
    assert result.returncode == 0, result.stderr


@MAC_ONLY
def test_parallel_guarded_startup_has_one_owner_and_sigkill_releases_it(tmp_path):
    source = """
import sys
from pathlib import Path
from dusty.privacy.network_guard import install_guard
install_guard()
from dusty.platform.single_instance import GuiInstance
print('waiting', flush=True)
sys.stdin.readline()
value = GuiInstance(Path(sys.argv[1]))
print('owner' if value.owner else 'duplicate', flush=True)
command = sys.stdin.readline().strip()
if command == 'poll':
    print(f'{value.activation_requested()} {value.activation_requested()}', flush=True)
    sys.stdin.readline()
value.close()
"""
    children = []

    def line(child):
        assert select.select([child.stdout], [], [], 5)[0], "Child response timed out"
        return child.stdout.readline().strip()

    try:
        for _ in range(8):
            children.append(
                subprocess.Popen(
                    [sys.executable, "-c", source, str(tmp_path)],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )
        assert [line(child) for child in children] == ["waiting"] * 8
        for child in children:
            child.stdin.write("start\n")
            child.stdin.flush()
        roles = [line(child) for child in children]
        errors = [
            child.stderr.read() for child, role in zip(children, roles, strict=True) if not role
        ]
        assert roles.count("owner") == 1 and roles.count("duplicate") == 7, errors
        owner = children[roles.index("owner")]
        owner.stdin.write("poll\n")
        owner.stdin.flush()
        assert line(owner) == "True False"
        owner.kill()  # SIGKILL prevents Python finally/close from running.
        owner.wait(timeout=5)
        replacement = instance(tmp_path)
        try:
            assert replacement.owner and not replacement.activation_requested()
        finally:
            replacement.close()
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)


@pytest.mark.parametrize("target", ["owner", "activation"])
@MAC_ONLY
def test_hardlinked_controls_are_rejected_and_preserved(tmp_path, target):
    control = tmp_path / ".gui-instance"
    control.mkdir(mode=0o700)
    original = tmp_path / "original"
    original.write_bytes(b"")
    original.chmod(0o600)
    os.link(original, control / target)
    with pytest.raises(OSError):
        instance(tmp_path)
    assert original.stat().st_nlink == 2
    assert original.read_bytes() == b""


@MAC_ONLY
def test_replaced_event_is_not_read_or_overwritten(tmp_path):
    first = instance(tmp_path)
    try:
        event = tmp_path / ".gui-instance/activation"
        event.rename(tmp_path / "old-event")
        event.write_bytes(b"1")
        event.chmod(0o600)
        with pytest.raises(OSError):
            first.activation_requested()
        assert event.read_bytes() == b"1"
    finally:
        first.close()


@MAC_ONLY
def test_event_write_failure_releases_transaction_and_redacts_error(tmp_path, monkeypatch):
    from dusty.platform import mac_instance

    first = instance(tmp_path)
    try:
        with monkeypatch.context() as patch:

            def failed_write(*args):
                raise OSError("/private/CANARY_PROFILE")

            patch.setattr(mac_instance.os, "pwrite", failed_write)
            with pytest.raises(OSError) as error:
                instance(tmp_path)
            assert "CANARY_PROFILE" not in str(error.value)
        second = instance(tmp_path)
        assert not second.owner
        second.close()
        assert first.activation_requested()
    finally:
        first.close()


@MAC_ONLY
def test_close_releases_owner_even_when_other_descriptor_was_closed(tmp_path):
    first = instance(tmp_path)
    os.close(first._event)
    first.close()
    first.close()
    replacement = instance(tmp_path)
    try:
        assert replacement.owner
    finally:
        replacement.close()


@pytest.mark.parametrize("target", ["directory", "owner", "activation"])
@MAC_ONLY
def test_nonprivate_control_permissions_are_preserved_and_rejected(tmp_path, target):
    first = instance(tmp_path)
    first.close()
    control = tmp_path / ".gui-instance"
    path = control if target == "directory" else control / target
    path.chmod(0o755 if target == "directory" else 0o644)
    with pytest.raises(OSError):
        instance(tmp_path)
    assert path.stat().st_mode & 0o077


@MAC_ONLY
def test_linked_ancestor_cannot_create_profile_outside_target(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        instance(link / "new/Dusty")
    assert not list(outside.iterdir())


@MAC_ONLY
def test_control_descriptors_are_not_inheritable(tmp_path):
    value = instance(tmp_path)
    try:
        assert all(
            not os.get_inheritable(fd)
            for fd in (value._root, value._directory, value._ownership, value._event)
        )
    finally:
        value.close()


@MAC_ONLY
def test_busy_activation_poll_is_nonblocking_and_startup_refuses_boundedly(tmp_path, monkeypatch):
    import fcntl

    from dusty.platform import mac_instance

    value = instance(tmp_path)
    transaction = os.open(tmp_path / ".gui-instance/activation", os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(transaction, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with monkeypatch.context() as patch:

            def unexpected_sleep(*args):
                raise AssertionError("Polling must never wait for another transaction")

            patch.setattr(mac_instance.time, "sleep", unexpected_sleep)
            assert not value.activation_requested()
            patch.setattr(mac_instance, "_CONTENTION_SECONDS", 0)
            with pytest.raises(OSError):
                instance(tmp_path)
        fcntl.flock(transaction, fcntl.LOCK_UN)
        duplicate = instance(tmp_path)
        assert not duplicate.owner
        duplicate.close()
        assert value.activation_requested()
    finally:
        os.close(transaction)
        value.close()


@MAC_ONLY
def test_control_directory_cannot_be_a_regular_file(tmp_path):
    control = tmp_path / ".gui-instance"
    control.write_bytes(b"unknown directory substitute")
    with pytest.raises(OSError):
        instance(tmp_path)
    assert control.read_bytes() == b"unknown directory substitute"


@MAC_ONLY
def test_transient_control_creation_absence_retries_and_still_has_single_owner(
    tmp_path, monkeypatch
):
    from dusty.platform import mac_instance

    original = mac_instance.os.open
    attempts = []

    def transient(name, flags, *args, **kwargs):
        if name == "owner":
            attempts.append(True)
            if len(attempts) == 1:
                raise FileNotFoundError("synthetic concurrent creation")
        return original(name, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(mac_instance.os, "open", transient)
        first = instance(tmp_path)
    try:
        assert first.owner and len(attempts) == 2
        second = instance(tmp_path)
        assert not second.owner
        second.close()
        assert first.activation_requested()
    finally:
        first.close()


@MAC_ONLY
def test_persistent_control_creation_absence_refuses_boundedly_and_closes(tmp_path, monkeypatch):
    from dusty.platform import mac_instance

    original = mac_instance.os.open

    def absent(name, flags, *args, **kwargs):
        if name == "owner":
            raise FileNotFoundError("synthetic persistent absence")
        return original(name, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(mac_instance.os, "open", absent)
        patch.setattr(mac_instance, "_CONTENTION_SECONDS", 0)
        with pytest.raises(OSError):
            instance(tmp_path)
    replacement = instance(tmp_path)
    try:
        assert replacement.owner
    finally:
        replacement.close()


@MAC_ONLY
def test_moved_profile_poll_refuses_without_recreating_any_path(tmp_path):
    profile = tmp_path / "CANARY_PROFILE"
    moved = tmp_path / "moved"
    value = instance(profile)
    profile.rename(moved)
    try:
        before = {path.name: path.read_bytes() for path in (moved / ".gui-instance").iterdir()}
        with pytest.raises(OSError) as error:
            value.activation_requested()
        assert "CANARY_PROFILE" not in str(error.value)
        assert not profile.exists()
        assert {
            path.name: path.read_bytes() for path in (moved / ".gui-instance").iterdir()
        } == before
    finally:
        value.close()
        value.close()


@MAC_ONLY
def test_replaced_profile_root_is_detected_without_mutating_old_or_new_state(tmp_path):
    profile = tmp_path / "profile"
    moved = tmp_path / "moved"
    old = instance(profile)
    profile.rename(moved)
    profile.mkdir(mode=0o700)
    replacement = instance(profile)
    try:
        assert replacement.owner  # A separate inode namespace, outside the atomic fault model.
        before = {
            path.relative_to(tmp_path): path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file()
        }
        with pytest.raises(OSError):
            old.activation_requested()
        old.close()
        old.close()
        assert not replacement.activation_requested()
        assert {
            path.relative_to(tmp_path): path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file()
        } == before
        duplicate = instance(profile)
        assert not duplicate.owner
        duplicate.close()
        assert replacement.activation_requested()
    finally:
        old.close()
        replacement.close()
