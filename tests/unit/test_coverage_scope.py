"""Audit F-13: safety modules must remain inside the strict 85 percent gate."""

from tools.measure_coverage import PACKAGES


def test_strict_coverage_includes_cleanup_and_process_boundaries():
    assert {
        "work_area.py",
        "installer_cleanup.py",
        "installer_upgrade.py",
        "platform/win_process.py",
    } <= set(PACKAGES)
