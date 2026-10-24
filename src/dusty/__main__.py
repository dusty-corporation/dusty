"""Launch Dusty's offline app and development entry points."""


def create_window():
    """Create the desktop window; native preparation starts after it is shown."""
    from dusty.app.window import MainWindow

    return MainWindow()


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from dusty import __version__

    parser = argparse.ArgumentParser(prog="dusty")
    parser.add_argument("--version", action="version", version=f"Dusty {__version__}")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--backend", choices=("auto", "cpu", "vulkan"), default="auto")
    parser.add_argument("--headless-batch", nargs="+", metavar="FILE")
    parser.add_argument("--out")
    parser.add_argument("--check-model-download", action="store_true", help=argparse.SUPPRESS)
    for flag in (
        "probe-vulkan",
        "probe-vulkan-child",
        "installer-test",
        "installer-clear",
        "installer-pass",
        "installer-prepare",
        "model-size",
        "installer-status",
    ):
        parser.add_argument("--" + flag, action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--uninstall-data", choices=("keep-models", "remove-models"), help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)

    if args.probe_vulkan_child or args.probe_vulkan:
        from pathlib import Path

        from dusty.runtime_paths import resolve_paths

        if not args.out:
            return 2
        paths = resolve_paths()
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

    if args.check_model_download:
        from pathlib import Path

        from dusty.app.model_download_check import run_download_check

        if not args.out:
            return 2
        return run_download_check(args.model, Path(args.out))

    if args.self_test or args.installer_test:
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
        if not args.out:
            parser.error("--out is required with --headless-batch")
        from pathlib import Path

        from dusty.devcli import transcribe

        return transcribe(
            [Path(value) for value in args.headless_batch],
            Path(args.out),
            model=args.model,
            backend=args.backend,
            formats=("txt",),
        )

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from dusty.app.theme import apply_theme

    app = QApplication(sys.argv[:1])
    apply_theme(app)
    window = create_window()
    window.show()
    QTimer.singleShot(0, window.initialize)
    return app.exec()


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    raise SystemExit(main())
