"""Launch Dusty's offline app and development entry points."""


def create_window():
    """Create the M0 shell window."""
    from PySide6.QtWidgets import QMainWindow

    window = QMainWindow()
    window.setWindowTitle("Dusty")
    window.resize(800, 600)
    return window


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
    args = parser.parse_args(argv)

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

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    raise SystemExit(main())
