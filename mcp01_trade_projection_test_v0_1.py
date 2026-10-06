"""Focused verification for MCP-01.4 Trade Projection."""

from mcp01_trade_projection_v0_1 import aggregate_trades, project_trade


def event(event_type, trade_event_id="TE-1", cycle_id="C-1", timestamp="2026-10-06T07:00:00Z", **extra):
    return {"event_type": event_type, "trade_event_id": trade_event_id, "cycle_id": cycle_id, "event_timestamp": timestamp, **extra}


def test_full_lifecycle_aggregates_once():
    rows = aggregate_trades([
        event("ORDER_ATTEMPTED", decision_id="D-1", case_id="CASE-1", asset="BTC", direction="LONG"),
        event("PROVIDER_RESULT", provider="TOOBIT", status="REJECTED", reason_code="-1157", cycle_id="C-2", timestamp="2026-10-06T07:00:01Z"),
        event("MARKET_OUTCOME", case_id="CASE-1", cycle_id="C-3", timestamp="2026-10-06T07:00:02Z"),
    ])
    assert len(rows) == 1
    row = rows[0]
    assert row["trade_event_id"] == "TE-1"
    assert row["case_id"] == "CASE-1"
    assert row["decision_id"] == "D-1"
    assert row["asset"] == "BTC"
    assert row["direction"] == "LONG"
    assert row["lifecycle"] == "MARKET_OUTCOME"
    assert row["evidence_count"] == 3
    assert row["providers"] == ["TOOBIT"]
    assert row["latest_status"] == "REJECTED"
    assert row["latest_reason_code"] == "-1157"


def test_repeated_trade_event_id_is_reconciled():
    rows = aggregate_trades([
        event("PROVIDER_RESULT", provider="TOOBIT"),
        event("PROVIDER_RESULT", provider="TOOBIT", cycle_id="C-2", timestamp="2026-10-06T07:01:00Z"),
    ])
    assert rows[0]["evidence_count"] == 2
    assert rows[0]["providers"] == ["TOOBIT"]


def test_multiple_trade_events_are_distinct():
    rows = aggregate_trades([
        event("ORDER_ATTEMPTED", trade_event_id="TE-2", cycle_id="C-2", decision_id="D-2"),
        event("ORDER_ATTEMPTED", trade_event_id="TE-1", decision_id="D-1"),
    ])
    assert [row["trade_event_id"] for row in rows] == ["TE-1", "TE-2"]


def test_identity_conflict_is_rejected():
    try:
        aggregate_trades([
            event("ORDER_ATTEMPTED", decision_id="D-1"),
            event("PROVIDER_RESULT", decision_id="D-2", provider="TOOBIT"),
        ])
    except ValueError as exc:
        assert "identity conflict" in str(exc)
    else:
        raise AssertionError("identity conflict was not rejected")


def test_invalid_lifecycle_is_rejected_by_projector():
    try:
        project_trade(trade_event_id="TE-1", first_cycle_id="C-1", last_cycle_id="C-1", lifecycle="SELECTED", evidence_count=1)
    except ValueError as exc:
        assert "unsupported lifecycle" in str(exc)
    else:
        raise AssertionError("invalid lifecycle was not rejected")


def test_provider_result_requires_trade_identity():
    try:
        aggregate_trades([event("PROVIDER_RESULT", trade_event_id=None, provider="TOOBIT")])
    except ValueError as exc:
        assert "trade_event_id" in str(exc)
    else:
        raise AssertionError("missing trade_event_id was not rejected")


if __name__ == "__main__":
    test_full_lifecycle_aggregates_once()
    test_repeated_trade_event_id_is_reconciled()
    test_multiple_trade_events_are_distinct()
    test_identity_conflict_is_rejected()
    test_invalid_lifecycle_is_rejected_by_projector()
    test_provider_result_requires_trade_identity()
    print("MCP01.4_TRADE_PROJECTION_TESTS=6/6 PASS")
