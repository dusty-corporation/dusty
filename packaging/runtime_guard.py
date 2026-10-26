"""User runtime hooks execute before PyInstaller's standard runtime hooks."""


def protect_runtime():
    from dusty.privacy.network_guard import install_guard

    install_guard()

    from dusty.platform.crash_policy import install_crash_policy

    install_crash_policy()


protect_runtime()
