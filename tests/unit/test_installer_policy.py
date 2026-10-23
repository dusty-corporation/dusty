"""An approved installer tool must not bypass redistribution policy review."""

from tools.check_installer_licenses import check
from tools.check_licenses import allowed_license


def test_inno_wrapper_license_is_narrowly_approved():
    assert check() == []
    assert allowed_license("inno-setup-installer", "InnoSetup", installer_wrapper=True)
    assert not allowed_license("inno-setup-installer", "InnoSetup")
    assert not allowed_license("other-app-component", "InnoSetup", installer_wrapper=True)
    assert not allowed_license(
        "inno-setup-installer", "InnoSetup OR UNKNOWN", installer_wrapper=True
    )
