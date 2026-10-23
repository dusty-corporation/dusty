"""User runtime hooks execute before PyInstaller's standard runtime hooks."""

from dusty.privacy.network_guard import install_guard

install_guard()
