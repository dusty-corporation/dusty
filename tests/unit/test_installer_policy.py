"""An approved installer tool must not bypass redistribution policy review."""

from tools.check_installer_licenses import check


def test_inno_wrapper_license_fails_closed_pending_pm():
    assert check() == [
        "Inno Setup 6.7.3: InnoSetup is not allowlisted; ISSUE-017 needs PM decision"
    ]
