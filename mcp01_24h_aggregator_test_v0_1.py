"""Focused verification for MCP-01.6 24H Aggregator."""

from mcp01_24h_aggregator_v0_1 import aggregate_24h


def test_aggregates_unique_identities_and_lifecycles():
    report = aggregate_24h(
        period_start="2026-10-05T00:00:00Z",
        period_end="2026-10-06T00:00:00Z",
        cycle_ids=["RC-1", "RC-1", "RC-2"],
        case_projections=[
            {"case_id": "CASE-1", "asset": "BTC", "lifecycle": "CLOSED"},
            {"case_id": "CASE-2", "asset": "ETH", "lifecycle": "TRADE_READY"},
            {"case_id": "CASE-1", "asset": "BTC", "lifecycle": "CLOSED"},
        ],
        trade_projections=[
            {"trade_event_id": "TE-1", "lifecycle": "PROVIDER_RESULT"},
            {"trade_event_id": "TE-2", "lifecycle": "MARKET_OUTCOME"},
            {"trade_event_id": "TE-1", "lifecycle": "PROVIDER_RESULT"},
        ],
        reconciliation_projections=[
            {"state": "PROVIDER_RESULT", "provider": "TOOBIT", "provider_status": "REJECTED", "provider_reason_code": "-1157", "complete": True, "market_outcome": None, "case_outcome": None},
            {"state": "MARKET_OUTCOME", "provider": "TOOBIT", "provider_status": "ACCEPTED", "provider_reason_code": None, "complete": True, "market_outcome": "PROFITABLE", "case_outcome": "CLOSED"},
        ],
        runtime_projections=[
            {"execution": "OFF"},
            {"execution": "OFF"},
        ],
        data_quality_events=[
            {"reason_code": "STALE_MARKET_DATA"},
            {"reason_code": "STALE_MARKET_DATA"},
        ],
    )
    assert report["period"] == {"start": "2026-10-05T00:00:00Z", "end": "2026-10-06T00:00:00Z"}
    assert report["cycles"]["count"] == 2
    assert report["cases"]["unique_count"] == 2
    assert report["cases"]["selected_asset_count"] == 2
    assert report["cases"]["lifecycle_counts"] == {"CLOSED": 2, "TRADE_READY": 1}
    assert report["trades"]["unique_count"] == 2
    assert report["trades"]["lifecycle_counts"] == {"MARKET_OUTCOME": 1, "PROVIDER_RESULT": 2}
    assert report["execution"]["provider_counts"] == {"TOOBIT": 2}
    assert report["execution"]["provider_status_counts"] == {"ACCEPTED": 1, "REJECTED": 1}
    assert report["execution"]["execution_modes_seen"] == ["OFF"]
    assert report["reconciliation"]["records"] == 2
    assert report["reconciliation"]["complete_provider_chains"] == 2
    assert report["reconciliation"]["market_outcomes"] == 1
    assert report["reconciliation"]["case_outcomes"] == 1
    assert report["reconciliation"]["reason_counts"] == {"-1157": 1}
    assert report["data_quality"]["event_count"] == 2
    assert report["data_quality"]["reason_counts"] == {"STALE_MARKET_DATA": 2}
    assert report["runtime"]["projection_count"] == 2


def test_provider_rejection_is_reported_not_dropped():
    report = aggregate_24h(
        period_start="S",
        period_end="E",
        cycle_ids=["RC-1"],
        reconciliation_projections=[
            {"state": "PROVIDER_RESULT", "provider": "TOOBIT", "provider_status": "REJECTED", "provider_reason_code": "-1157", "complete": True, "market_outcome": None, "case_outcome": None},
        ],
    )
    assert report["execution"]["provider_status_counts"] == {"REJECTED": 1}
    assert report["reconciliation"]["reason_counts"] == {"-1157": 1}
    assert report["reconciliation"]["market_outcomes"] == 0


def test_execution_modes_are_observed_without_activation():
    report = aggregate_24h(
        period_start="S",
        period_end="E",
        cycle_ids=["RC-1", "RC-2"],
        runtime_projections=[{"execution": "OFF"}, {"execution": "OFF"}],
    )
    assert report["execution"]["execution_modes_seen"] == ["OFF"]


def test_invalid_cycle_id_is_rejected():
    try:
        aggregate_24h(period_start="S", period_end="E", cycle_ids=["RC-1", ""])
    except ValueError as exc:
        assert "cycle_id" in str(exc)
    else:
        raise AssertionError("invalid cycle_id was not rejected")


def test_invalid_case_lifecycle_is_rejected():
    try:
        aggregate_24h(
            period_start="S",
            period_end="E",
            cycle_ids=["RC-1"],
            case_projections=[{"case_id": "CASE-1", "lifecycle": ""}],
        )
    except ValueError as exc:
        assert "lifecycle" in str(exc)
    else:
        raise AssertionError("invalid lifecycle was not rejected")


def test_invalid_data_quality_reason_is_rejected():
    try:
        aggregate_24h(
            period_start="S",
            period_end="E",
            cycle_ids=["RC-1"],
            data_quality_events=[{"reason_code": ""}],
        )
    except ValueError as exc:
        assert "reason_code" in str(exc)
    else:
        raise AssertionError("invalid data-quality reason was not rejected")


if __name__ == "__main__":
    test_aggregates_unique_identities_and_lifecycles()
    test_provider_rejection_is_reported_not_dropped()
    test_execution_modes_are_observed_without_activation()
    test_invalid_cycle_id_is_rejected()
    test_invalid_case_lifecycle_is_rejected()
    test_invalid_data_quality_reason_is_rejected()
    print("MCP01.6_24H_AGGREGATOR_TESTS=6/6 PASS")
