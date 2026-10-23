"""Tie the live negative CI case to the production installer's upload condition."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_production_upload_depends_on_complete_gates_and_matches_negative_ci():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    jobs = dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)", workflow, re.M | re.S))
    production = jobs["packaging-spike"]
    negative = jobs["installer-upload-regression"]
    assert "needs: [checks, offline, installer-upload-regression]" in production

    def condition(job):
        return re.search(r"id: installer_upload\n\s+if: (.+)", job).group(1)

    expected = (
        "success() && steps.installer_licenses.outcome == 'success' && "
        "steps.installer_acceptance.outcome == 'success'"
    )
    assert condition(production) == condition(negative) == expected
    assert production.index("id: installer_licenses") < production.index("id: installer_upload")
    assert "continue-on-error" not in production
    assert "steps.installer_upload.outcome }}' -ne 'skipped'" in negative
    assert (
        "id: installer_licenses\n        continue-on-error: true\n        run: exit 1" in negative
    )
