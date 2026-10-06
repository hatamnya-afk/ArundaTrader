"""Focused MCP-01.3 verification.

No external dependencies and no runtime/provider/DB access.
"""

from mcp01_case_projection_v0_1 import aggregate_cases, assign_case_ids


def event(event_id, event_type, ts, cycle, asset="BTC/USDT", **extra):
    value = {
        "event_id": event_id,
        "event_type": event_type,
        "event_timestamp": ts,
        "cycle_id": cycle,
        "asset": asset,
    }
    value.update(extra)
    return value


def main() -> int:
    first = [
        event("e2", "SELECTED", "2026-10-06T00:00:02Z", "cycle-2", decision_id="D2"),
        event("e1", "NEW", "2026-10-06T00:00:01Z", "cycle-1", decision_id="D1"),
        event("e3", "TRADE_READY", "2026-10-06T00:00:03Z", "cycle-3", decision_id="D2"),
        event("e4", "CLOSED", "2026-10-06T00:00:04Z", "cycle-4", status="REJECTED"),
    ]
    assigned = assign_case_ids(first)
    assert len({e["case_id"] for e in assigned}) == 1
    assert [e["cycle_id"] for e in assigned] == ["cycle-1", "cycle-2", "cycle-3", "cycle-4"]

    projected = aggregate_cases(first)
    assert len(projected) == 1
    case = projected[0]
    assert case["lifecycle"] == "CLOSED"
    assert case["appearance_count"] == 4
    assert case["decision_ids"] == ["D1", "D2"]
    assert case["last_cycle_id"] == "cycle-4"
    assert case["latest_status"] == "REJECTED"

    repeated = [
        event("a1", "SELECTED", "2026-10-06T01:00:00Z", "c1", asset="ETH/USDT", decision_id="D10"),
        event("a2", "TRADE_READY", "2026-10-06T01:00:01Z", "c2", asset="ETH/USDT", decision_id="D11"),
    ]
    repeated_cases = aggregate_cases(repeated)
    assert len(repeated_cases) == 1
    assert repeated_cases[0]["appearance_count"] == 2

    reopened = repeated + [
        event("a3", "CLOSED", "2026-10-06T01:00:02Z", "c3", asset="ETH/USDT", status="DONE"),
        event("a4", "SELECTED", "2026-10-06T01:00:03Z", "c4", asset="ETH/USDT", decision_id="D12"),
    ]
    reopened_cases = aggregate_cases(reopened)
    assert len(reopened_cases) == 2
    assert [c["lifecycle"] for c in reopened_cases] == ["CLOSED", "SELECTED"]

    explicit = [
        event("x1", "SELECTED", "2026-10-06T02:00:00Z", "x1", asset="SOL/USDT", case_id="CASE-EXPLICIT"),
        event("x2", "CLOSED", "2026-10-06T02:00:01Z", "x2", asset="SOL/USDT"),
    ]
    explicit_assigned = assign_case_ids(explicit)
    assert explicit_assigned[0]["case_id"] == "CASE-EXPLICIT"
    assert explicit_assigned[1]["case_id"] == "CASE-EXPLICIT"

    deterministic = [
        event("d1", "SELECTED", "2026-10-06T04:00:00Z", "d1", asset="XRP/USDT", decision_id="DX"),
    ]
    first_id = assign_case_ids(deterministic)[0]["case_id"]
    second_id = assign_case_ids(deterministic)[0]["case_id"]
    assert first_id == second_id
    with_trade = [
        event("t1", "ORDER_ATTEMPTED", "2026-10-06T04:00:00Z", "d1", asset="XRP/USDT", decision_id="DX", trade_event_id="TE-1"),
    ]
    trade_case = aggregate_cases(with_trade)[0]
    assert trade_case["trade_event_ids"] == ["TE-1"]

    conflict = [
        event("z1", "SELECTED", "2026-10-06T03:00:00Z", "z1", asset="BTC/USDT", case_id="CASE-X"),
        event("z2", "SELECTED", "2026-10-06T03:00:01Z", "z2", asset="ETH/USDT", case_id="CASE-X"),
    ]
    try:
        aggregate_cases(conflict)
    except ValueError as exc:
        assert "reused across assets" in str(exc)
    else:
        raise AssertionError("cross-asset case identity conflict was not rejected")

    print("MCP01.3_CASE_PROJECTION_TESTS=6/6 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
