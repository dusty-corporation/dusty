"""Set downloader error-mode mitigations before standard frozen runtime hooks."""

from dusty_fetch.crash_policy import install_crash_policy

install_crash_policy()
