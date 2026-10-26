"""PM-approved aggregate must fail on any byte, scope or attribution change."""

import hashlib

import pytest

from tools import mingw_runtime as policy
from tools.check_licenses import allowed_license


@pytest.fixture
def aggregate(tmp_path, monkeypatch):
    contents = {name: name.encode() for name in policy.BINARY_SHA256}
    notice = b"exact synthetic runtime notice"
    monkeypatch.setattr(
        policy,
        "BINARY_SHA256",
        {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    )
    monkeypatch.setattr(policy, "NOTICE_SHA256", hashlib.sha256(notice).hexdigest())
    contents.update(dict.fromkeys(policy.NOTICES, notice))
    contents["THIRD_PARTY_NOTICES.md"] = b"Notices\n" + notice
    rows = []
    for name, data in contents.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rows.append(
            {
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "components": [policy.COMPONENT] if name in policy.BINARY_SHA256 else ["dusty"],
            }
        )
    inventory = {
        "components": {
            policy.COMPONENT: {
                "name": policy.COMPONENT,
                "license": policy.LICENSE,
                "version": "11.0.1",
                "linkage": "static",
            }
        },
        "files": rows,
    }
    return tmp_path, inventory


def test_aggregate_exception_is_exact_and_not_globally_allowed(aggregate):
    bundle, inventory = aggregate
    assert policy.approved(bundle, inventory)
    assert not allowed_license(policy.COMPONENT, policy.LICENSE)
    assert not allowed_license("anything", policy.LICENSE)
    assert not allowed_license(policy.COMPONENT, "ZPL-2.1")


@pytest.mark.parametrize("name", [*policy.BINARY_SHA256, *policy.NOTICES])
def test_changed_bytes_fail_even_with_forged_inventory_hash(aggregate, name):
    bundle, inventory = aggregate
    path = bundle / name
    path.write_bytes(path.read_bytes() + b"changed")
    for item in inventory["files"]:
        if item["path"] == name:
            item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not policy.approved(bundle, inventory)


@pytest.mark.parametrize(
    "change", ["extra", "missing", "name", "version", "license", "linkage", "notices"]
)
def test_runtime_scope_changes_fail(aggregate, change):
    bundle, inventory = aggregate
    component = inventory["components"][policy.COMPONENT]
    if change == "extra":
        inventory["files"].append({"path": "other.exe", "components": [policy.COMPONENT]})
    elif change == "missing":
        inventory["files"].pop(0)
    elif change == "notices":
        (bundle / "THIRD_PARTY_NOTICES.md").write_text("missing runtime text")
    else:
        component[change] = "unapproved"
    assert not policy.approved(bundle, inventory)
