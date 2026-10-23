"""Local-TLS adapter for the production guarded GUI audit exercise."""


def main():
    import sys
    from pathlib import Path

    from dusty.app import model_download_check as check
    from dusty.app import model_manager
    from dusty.runtime_paths import RuntimePaths

    port, certificate, resources, user, output = sys.argv[1:]
    command = [sys.executable, str(Path(__file__).with_name("fetch_child.py")), port, certificate]
    model_manager.resolve_fetch_command = lambda: command
    check.resolve_paths = lambda: RuntimePaths(
        Path(resources) / "bin", Path(user) / "models", Path(resources), Path(user)
    )
    return check.run_download_check("tiny", Path(output))


if __name__ == "__main__":
    from dusty.privacy.network_guard import install_guard

    install_guard()
    raise SystemExit(main())
