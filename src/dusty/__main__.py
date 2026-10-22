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
    parser.parse_args(argv)

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    raise SystemExit(main())
