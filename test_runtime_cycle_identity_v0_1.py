"""Focused runtime-cycle identity contract tests."""
from __future__ import annotations

from runtime_cycle_identity_v0_1 import (
    CYCLE_PREFIX,
    SCHEMA_VERSION,
    build_runtime_cycle_id,
)


def test_cycle_id_is_stable_for_same_run_identity():
    a = build_runtime_cycle_id(
        started_at="2026-10-05T12:00:00+00:00",
        process_id=12345,
    )
    b = build_runtime_cycle_id(
        started_at="2026-10-05T12:00:00+00:00",
        process_id=12345,
    )
    assert a == b
    assert a.startswith(CYCLE_PREFIX)


def test_cycle_id_changes_when_run_identity_changes():
    a = build_runtime_cycle_id(
        started_at="2026-10-05T12:00:00+00:00",
        process_id=12345,
    )
    b = build_runtime_cycle_id(
        started_at="2026-10-05T12:00:01+00:00",
        process_id=12345,
    )
    assert a != b


def test_cycle_identity_is_distinct_from_schema_and_not_a_decision_id():
    cycle_id = build_runtime_cycle_id(
        started_at="2026-10-05T12:00:00+00:00",
        process_id=12345,
    )
    assert cycle_id.startswith("RC-")
    assert cycle_id != "d1"
    assert SCHEMA_VERSION


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"RUNTIME CYCLE IDENTITY TESTS PASS: {len(tests)}/{len(tests)}")
