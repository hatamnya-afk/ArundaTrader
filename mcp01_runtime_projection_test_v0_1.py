"""Focused tests for MCP-01.2 compact runtime projection."""
from __future__ import annotations

from mcp01_runtime_projection_v0_1 import project_runtime, render_runtime_line, SCHEMA, SCHEMA_VERSION


def _projection(**overrides):
    args = dict(
        cycle_id="RC-test-001",
        emitted_at="2026-10-06T00:00:00+00:00",
        universe_size=20,
        opportunity_ready=8,
        signal_ready=8,
        validation_ready=7,
        fusion_ready=7,
        decision_ready=6,
        risk_ready=6,
        trade_gate_ready=5,
        trade_ready=4,
        order_intents_created=4,
        canonical_order_requests_created=3,
        execution="OFF",
        real_order=False,
        real_trade=False,
        status_counts={"ACTIONABLE": 4, "HOLD": 2},
        failure_reasons={"RISK_BLOCK": 1},
        selected_assets=["BTC/USDT", "ETH/USDT", "BTC/USDT"],
    )
    args.update(overrides)
    return project_runtime(**args)


def test_schema_and_identity_are_preserved():
    p = _projection()
    assert p["schema"] == SCHEMA
    assert p["schema_version"] == SCHEMA_VERSION
    assert p["cycle_id"] == "RC-test-001"
    assert p["emitted_at"] == "2026-10-06T00:00:00+00:00"


def test_counts_and_selection_are_compact_and_deterministic():
    p = _projection()
    assert p["counts"]["universe"] == 20
    assert p["counts"]["decision"] == 6
    assert p["counts"]["trade_ready"] == 4
    assert p["counts"]["canonical_orders"] == 3
    assert p["selection"] == {
        "count": 2,
        "assets": ["BTC/USDT", "ETH/USDT"],
    }


def test_execution_off_cannot_claim_real_activity():
    try:
        _projection(execution="OFF", real_order=True)
    except ValueError as exc:
        assert "OFF execution" in str(exc)
    else:
        raise AssertionError("invalid OFF execution state accepted")


def test_real_trade_requires_real_order():
    try:
        _projection(real_trade=True, real_order=False)
    except ValueError as exc:
        assert "real_order" in str(exc)
    else:
        raise AssertionError("invalid real trade state accepted")


def test_downstream_counts_cannot_exceed_upstream_counts():
    try:
        _projection(trade_ready=6, trade_gate_ready=5)
    except ValueError as exc:
        assert "trade_ready" in str(exc)
    else:
        raise AssertionError("invalid trade gate cardinality accepted")
    try:
        _projection(canonical_order_requests_created=5, order_intents_created=4)
    except ValueError as exc:
        assert "canonical orders" in str(exc)
    else:
        raise AssertionError("invalid order cardinality accepted")


def test_render_is_bounded_management_line():
    line = render_runtime_line(_projection())
    assert line.startswith("RUNTIME cycle=RC-test-001 ")
    assert "decision=6" in line
    assert "trade_ready=4" in line
    assert "orders=3" in line
    assert "EXECUTION=OFF" in line
    assert "REAL_ORDER=False" in line
    assert "REAL_TRADE=False" in line
    assert "\n" not in line


if __name__ == "__main__":
    tests = [v for n, v in sorted(globals().items()) if n.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"MCP01.2 RUNTIME PROJECTION TESTS PASS: {len(tests)}/{len(tests)}")
