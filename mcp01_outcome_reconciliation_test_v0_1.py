"""Focused verification for MCP-01.5 Outcome Reconciliation."""

from mcp01_outcome_reconciliation_v0_1 import reconcile_outcomes


def event(event_type, **extra):
    return {
        "event_type": event_type,
        "event_timestamp": extra.pop("event_timestamp", "2026-10-06T07:00:00Z"),
        "cycle_id": extra.pop("cycle_id", "C-1"),
        **extra,
    }


def test_full_chain_reconciles():
    rows = reconcile_outcomes([
        event("TRADE_READY", case_id="CASE-1", decision_id="D-1", asset="BTC", direction="LONG"),
        event("ORDER_ATTEMPTED", case_id="CASE-1", decision_id="D-1", trade_event_id="TE-1", asset="BTC", direction="LONG"),
        event("PROVIDER_RESULT", case_id="CASE-1", decision_id="D-1", trade_event_id="TE-1", provider="TOOBIT", status="ACCEPTED", asset="BTC", direction="LONG"),
        event("MARKET_OUTCOME", case_id="CASE-1", decision_id="D-1", trade_event_id="TE-1", status="PROFITABLE", asset="BTC", direction="LONG"),
        event("CLOSED", case_id="CASE-1", decision_id="D-1", trade_event_id="TE-1", status="CLOSED", asset="BTC", direction="LONG"),
    ])
    assert len(rows) == 1
    row = rows[0]
    assert row["case_id"] == "CASE-1"
    assert row["decision_id"] == "D-1"
    assert row["trade_event_id"] == "TE-1"
    assert row["states_seen"] == ["DECISION", "ORDER", "PROVIDER_RESULT", "MARKET_OUTCOME", "CASE_OUTCOME"]
    assert row["state"] == "CASE_OUTCOME"
    assert row["provider"] == "TOOBIT"
    assert row["provider_status"] == "ACCEPTED"
    assert row["market_outcome"] == "PROFITABLE"
    assert row["case_outcome"] == "CLOSED"
    assert row["complete"] is True


def test_real_provider_rejection_is_valid_terminal_evidence():
    rows = reconcile_outcomes([
        event("TRADE_READY", case_id="CASE-2", decision_id="D-2", asset="BTC", direction="LONG"),
        event("ORDER_ATTEMPTED", case_id="CASE-2", decision_id="D-2", trade_event_id="TE-2", asset="BTC", direction="LONG"),
        event("PROVIDER_RESULT", case_id="CASE-2", decision_id="D-2", trade_event_id="TE-2", provider="TOOBIT", status="REJECTED", reason_code="-1157", asset="BTC", direction="LONG"),
    ])
    row = rows[0]
    assert row["trade_event_id"] == "TE-2"
    assert row["provider_status"] == "REJECTED"
    assert row["provider_reason_code"] == "-1157"
    assert row["complete"] is True
    assert row["market_outcome"] is None


def test_multiple_trade_events_remain_distinct():
    rows = reconcile_outcomes([
        event("TRADE_READY", case_id="CASE-3", decision_id="D-3", asset="BTC"),
        event("ORDER_ATTEMPTED", case_id="CASE-3", decision_id="D-3", trade_event_id="TE-3A", asset="BTC"),
        event("PROVIDER_RESULT", case_id="CASE-3", decision_id="D-3", trade_event_id="TE-3A", provider="TOOBIT", status="REJECTED"),
        event("ORDER_ATTEMPTED", case_id="CASE-3", decision_id="D-3", trade_event_id="TE-3B", asset="BTC"),
        event("PROVIDER_RESULT", case_id="CASE-3", decision_id="D-3", trade_event_id="TE-3B", provider="TOOBIT", status="ACCEPTED"),
    ])
    assert len(rows) == 2
    assert {row["trade_event_id"] for row in rows} == {"TE-3A", "TE-3B"}


def test_identity_conflict_is_rejected():
    try:
        reconcile_outcomes([
            event("ORDER_ATTEMPTED", case_id="CASE-4", decision_id="D-4", trade_event_id="TE-4", asset="BTC"),
            event("PROVIDER_RESULT", case_id="CASE-4", decision_id="D-4X", trade_event_id="TE-4", provider="TOOBIT", status="REJECTED"),
        ])
    except ValueError as exc:
        assert "identity conflict" in str(exc)
    else:
        raise AssertionError("identity conflict was not rejected")


def test_missing_trade_identity_is_rejected():
    try:
        reconcile_outcomes([event("PROVIDER_RESULT", case_id="CASE-5", provider="TOOBIT", status="REJECTED")])
    except ValueError as exc:
        assert "trade_event_id" in str(exc)
    else:
        raise AssertionError("missing trade_event_id was not rejected")


def test_provider_conflict_is_rejected():
    try:
        reconcile_outcomes([
            event("PROVIDER_RESULT", case_id="CASE-6", trade_event_id="TE-6", provider="TOOBIT", status="REJECTED"),
            event("MARKET_OUTCOME", case_id="CASE-6", trade_event_id="TE-6", provider="KUCOIN", status="PROFITABLE"),
        ])
    except ValueError as exc:
        assert "provider conflict" in str(exc)
    else:
        raise AssertionError("provider conflict was not rejected")


if __name__ == "__main__":
    test_full_chain_reconciles()
    test_real_provider_rejection_is_valid_terminal_evidence()
    test_multiple_trade_events_remain_distinct()
    test_identity_conflict_is_rejected()
    test_missing_trade_identity_is_rejected()
    test_provider_conflict_is_rejected()
    print("MCP01.5_OUTCOME_RECONCILIATION_TESTS=6/6 PASS")
