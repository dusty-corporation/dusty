"""Launch Dusty's offline app and development entry points."""


def create_window():
    """Create the desktop window; native preparation starts after it is shown."""
    from dusty.app.window import MainWindow

    return MainWindow()


def _prepare_mac_application(app) -> None:
    """Mac application identity and Dock icon; Qt 6 handles Retina scaling itself."""
    from dusty.app import messages as M
    from dusty.app.theme import application_icon

    app.setApplicationName(M.APP_NAME)
    app.setApplicationDisplayName(M.APP_NAME)
    app.setOrganizationName(M.APP_NAME)
    app.setWindowIcon(application_icon())


def _private_user_dir(user_dir) -> bool:
    """Mac: create the data folder private (0700), or make an existing one private.

    The Mac single-instance lease refuses a data folder that others can read. A
    folder made earlier by a self-test or batch run with the default umask would
    otherwise stop the window from opening. Links and other owners are left alone
    and reported as unusable: False means the folder is a link, not a folder,
    belongs to another user, or could not be made private.
    """
    import os
    import stat
    import sys

    if sys.platform != "darwin":
        return True
    try:
        user_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.mkdir(user_dir, 0o700)
        except FileExistsError:
            pass
        info = os.lstat(user_dir)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            return False
        if stat.S_IMODE(info.st_mode) & 0o077:
            os.chmod(user_dir, 0o700, follow_symlinks=False)
        info = os.lstat(user_dir)
        return stat.S_ISDIR(info.st_mode) and not stat.S_IMODE(info.st_mode) & 0o077
    except OSError:
        return False


def _mac_startup_refused(text: str, *, gui: bool) -> int:
    """Explain a refused Mac start in plain words, never with a traceback or a path."""
    import sys

    print(text, file=sys.stderr)
    if gui:
        from PySide6.QtWidgets import QApplication

        from dusty.app.dialogs import ErrorDialog
        from dusty.app.theme import apply_theme

        app = QApplication.instance()
        if not isinstance(app, QApplication):
            app = QApplication(sys.argv[:1])
        _prepare_mac_application(app)
        apply_theme(app)
        ErrorDialog(text=text).exec()
    return 1


def _finish_mac_removal(*, remove_models: bool) -> bool:
    """Mac Remove Dusty data, after the window closed; tell the person the outcome."""
    from dusty.app import messages as M
    from dusty.app.dialogs import TextDialog
    from dusty.mac_removal import remove_data
    from dusty.runtime_paths import resolve_paths

    removed = remove_data(resolve_paths(), remove_models=remove_models)
    if removed:
        texts = (M.REMOVE_DATA_DONE,) + (() if remove_models else (M.REMOVE_DATA_MODELS_KEPT,))
        dialog = TextDialog(M.REMOVE_DATA_DONE_TITLE, texts)
    else:
        dialog = TextDialog(M.REMOVE_DATA_KEPT_TITLE, (M.REMOVE_DATA_KEPT, M.REMOVE_DATA_DONE))
    dialog.button(M.OK, dialog.accept, default=True)
    dialog.exec()
    return removed


def _poll_activation(instance, window, timer, activate, *, mac: bool) -> None:
    """Raise the window when a second launch asked for it.

    Mac: if the lease state becomes unusable while the window is open, keep the
    window working and stop polling instead of raising from a timer slot.
    """
    try:
        requested = instance.activation_requested()
    except OSError:
        if not mac:
            raise
        timer.stop()
        return
    if requested:
        activate(window)


def _probe_platform_gpu(paths, output, model_id: str, report_exit: bool) -> int:
    """Mac GPU probe through the shared engine probe (Metal); Windows uses Vulkan."""
    import json

    from dusty.engine.backend import probe_gpu
    from dusty.models import ModelRegistry, load_manifest

    try:
        registry = ModelRegistry(
            load_manifest(paths.resources_dir / "models.json"), paths.models_dir
        )
        # The probe keeps its result and scratch files in the data folder.
        ok = _private_user_dir(paths.user_dir) and probe_gpu(paths, registry, model_id=model_id)
    except Exception:
        ok = False
    output.write_text(json.dumps({"real_gpu_found": ok}), encoding="utf-8")
    return (0 if ok else 1) if report_exit else 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from dusty import __version__
    from dusty.engine.binaries import gpu_backend

    windows = sys.platform == "win32"
    parser = argparse.ArgumentParser(prog="dusty")
    parser.add_argument("--version", action="version", version=f"Dusty {__version__}")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--model", default="tiny")
    # The GPU choice is the platform backend: "vulkan" on Windows, "metal" on Mac.
    parser.add_argument("--backend", choices=("auto", "cpu", gpu_backend()), default="auto")
    parser.add_argument("--headless-batch", nargs="+", metavar="FILE")
    parser.add_argument("--out")
    parser.add_argument("--installer-upgrade-root", help=argparse.SUPPRESS)
    parser.add_argument("--check-model-download", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--check-hardening", action="store_true", help=argparse.SUPPRESS)
    for flag in (
        "probe-vulkan",
        "probe-vulkan-child",
        "installer-test",
        "installer-clear",
        "installer-pass",
        "installer-prepare",
        "model-size",
        "installer-status",
        "installer-cancel-part",
        "installer-can-uninstall",
    ):
        parser.add_argument("--" + flag, action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--uninstall-data", choices=("keep-models", "remove-models"), help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)

    if args.installer_can_uninstall:
        from dusty.installer_cleanup import uninstall_allowed
        from dusty.runtime_paths import resolve_paths

        return 0 if uninstall_allowed(resolve_paths()) else 1

    if args.installer_upgrade_root:
        from pathlib import Path

        from dusty.installer_upgrade import tidy_license_copies
        from dusty.runtime_paths import resolve_paths

        try:
            return (
                0 if tidy_license_copies(resolve_paths(), Path(args.installer_upgrade_root)) else 1
            )
        except (OSError, ValueError):
            return 1

    if args.probe_vulkan_child or args.probe_vulkan:
        from pathlib import Path

        from dusty.runtime_paths import resolve_paths

        if not args.out:
            return 2
        paths = resolve_paths()
        if not windows:
            return _probe_platform_gpu(paths, Path(args.out), args.model, args.probe_vulkan)
        if args.probe_vulkan:
            from dusty.installer_support import probe

            return 0 if probe(paths, Path(args.out)) else 1
        import json

        from dusty.platform.vulkan_probe import probe_device

        try:
            ok = probe_device(paths.bin_dir / "vulkan")
        except Exception:
            ok = False
        Path(args.out).write_text(json.dumps({"real_gpu_found": ok}), encoding="utf-8")
        return 0

    if (
        args.installer_clear
        or args.installer_pass
        or args.installer_prepare
        or args.model_size
        or args.installer_status
        or args.installer_cancel_part
    ):
        from pathlib import Path

        from dusty.installer_support import accept_tests, clear_failed_selection, model_size
        from dusty.runtime_paths import resolve_paths

        if args.installer_clear:
            clear_failed_selection(resolve_paths())
        elif args.installer_pass:
            accept_tests(resolve_paths(), args.model)
        elif args.installer_prepare:
            from dusty.models import cleanup_stale_partials
            from dusty.work_area import sanitize_output

            paths = resolve_paths()
            sanitize_output(paths)
            cleanup_stale_partials(paths.models_dir)
        elif args.installer_status and args.out:
            import json

            from dusty.installer_support import model_status

            Path(args.out).write_text(
                json.dumps(model_status(resolve_paths()), separators=(",", ":")), encoding="utf-8"
            )
        elif args.installer_cancel_part:
            from dusty.installer_support import cancel_partial

            return 0 if cancel_partial(resolve_paths(), args.model) else 1
        elif args.out:
            Path(args.out).write_text(model_size(resolve_paths()), encoding="utf-8")
        return 0

    if args.uninstall_data:
        from dusty.installer_cleanup import cleanup
        from dusty.runtime_paths import resolve_paths

        return (
            0
            if cleanup(resolve_paths(), remove_models=args.uninstall_data == "remove-models")
            else 1
        )

    # Cleanup/probe helpers return above: they must not create or hold a new
    # log during removal. Processing/GUI paths capture before any Qt imports.
    import os

    from dusty.privacy.native_diagnostics import install_capture, set_context
    from dusty.runtime_paths import resolve_paths

    # Native crash diagnostics observe a Windows-only exception; never on Mac.
    if windows and os.environ.get("DUSTY_NATIVE_DIAGNOSTICS") == "1":
        install_capture(resolve_paths().user_dir)

    if args.check_hardening:
        from pathlib import Path

        from dusty.app.hardening_check import run

        return run(Path(args.out)) if args.out else 2

    if args.check_model_download:
        from pathlib import Path

        from dusty.app.model_download_check import run_download_check

        if not args.out:
            return 2
        return run_download_check(args.model, Path(args.out))

    from dusty.app import messages as M

    mac = sys.platform == "darwin"
    if args.self_test or args.installer_test:
        set_context("self-test")
        if mac and not _private_user_dir(resolve_paths().user_dir):
            return _mac_startup_refused(M.DATA_FOLDER_UNSAFE, gui=False)
        from dusty.privacy.logging import configure_logger
        from dusty.runtime_paths import resolve_paths
        from dusty.selftest import run_selftest

        paths = resolve_paths()
        configure_logger(paths.user_dir)
        code = run_selftest(paths, args.model, backend=args.backend, once=args.installer_test)
        if args.installer_test and args.out:
            from pathlib import Path

            Path(args.out).write_text(code, encoding="utf-8")
        print(code)
        return 0 if code.startswith("OK") else 1

    if args.headless_batch:
        set_context("batch")
        if not args.out:
            parser.error("--out is required with --headless-batch")
        if mac and not _private_user_dir(resolve_paths().user_dir):
            return _mac_startup_refused(M.DATA_FOLDER_UNSAFE, gui=False)
        from pathlib import Path

        from dusty.devcli import transcribe

        return transcribe(
            [Path(value) for value in args.headless_batch],
            Path(args.out),
            model=args.model,
            backend=args.backend,
            formats=("txt",),
        )

    set_context("qt-startup")
    user_dir = resolve_paths().user_dir
    if mac and not _private_user_dir(user_dir):
        return _mac_startup_refused(M.DATA_FOLDER_UNSAFE, gui=True)
    from dusty.platform.single_instance import GuiInstance, activate_window

    try:
        instance = GuiInstance(user_dir)
    except OSError:
        if not mac:
            raise
        return _mac_startup_refused(M.INSTANCE_UNAVAILABLE, gui=True)
    if not instance.owner:
        instance.close()
        return 0
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from dusty.app.theme import apply_theme

    app = QApplication(sys.argv[:1])
    if sys.platform == "darwin":
        _prepare_mac_application(app)
    apply_theme(app)
    window = create_window()
    window.show()
    activation = QTimer(app)
    activation.timeout.connect(
        lambda: _poll_activation(instance, window, activation, activate_window, mac=mac)
    )
    activation.start(100)
    QTimer.singleShot(0, window.initialize)
    set_context("event-loop")
    try:
        exit_code = app.exec()
        request = getattr(window, "removal_request", None)
        if mac and request is not None:
            # Still holding the lease: a launch now only asks this Dusty to come forward.
            _finish_mac_removal(remove_models=request)
        return exit_code
    finally:
        instance.close()


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    from dusty.platform.crash_policy import install_crash_policy

    install_crash_policy()
    raise SystemExit(main())
