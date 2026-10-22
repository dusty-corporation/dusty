"""Restore Windows batch sleep-prevention state, including on exceptions."""

import sys

import pytest

from dusty.platform import power


@pytest.mark.skipif(sys.platform != "win32", reason="Windows execution-state API")
def test_batch_power_state_is_restored_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def set_state(flags: int) -> int:
        calls.append(flags)
        return power.ES_CONTINUOUS | 2

    monkeypatch.setattr(power, "_set_execution_state", set_state)
    with pytest.raises(RuntimeError), power.prevent_sleep():
        raise RuntimeError("Batch failed")
    assert calls == [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED, power.ES_CONTINUOUS | 2]
