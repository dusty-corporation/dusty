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
    args = parser.parse_args(argv)

    if args.check_model_download:
        from pathlib import Path

        from dusty.app.model_download_check import run_download_check

        if not args.out:
            return 2
        return run_download_check(args.model, Path(args.out))

    if args.self_test:
        from dusty.privacy.logging import configure_logger
        from dusty.runtime_paths import resolve_paths
        from dusty.selftest import run_selftest

        paths = resolve_paths()
        configure_logger(paths.user_dir)
        code = run_selftest(paths, args.model, backend=args.backend)
        print(code)
        return 0 if code == "OK" else 1

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
