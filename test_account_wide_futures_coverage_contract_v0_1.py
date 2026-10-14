import pytest

from account_wide_futures_coverage_contract_v0_1 import validate_account_wide_futures_coverage


def evidence():
    return {
        "account_scope": "TOOBIT:fixture-account", "cycle_id": "fixture-cycle",
        "observed_at": "2026-10-14T18:00:00Z", "provider_endpoint": "fixture-endpoint",
        "provider_request_id": "fixture-request", "provenance": "synthetic fixture only",
        "http_method": "GET", "coverage_scope": "ACCOUNT_WIDE",
        "pagination_complete": True, "pages_received": 2, "pages_total": 2,
        "positions": [
            {"position_id": "fixture-position-1", "allocated_risk_usdt": 5.0},
            {"position_id": "fixture-position-2", "allocated_risk_usdt": 0.0},
        ],
    }


def test_complete_account_wide_get_evidence_passes_contract():
    result = validate_account_wide_futures_coverage(evidence())
    assert result["coverage_state"] == "AVAILABLE"
    assert result["position_count"] == 2
    assert result["provider_completeness_claim"] == "REQUIRES_ENDPOINT_SEMANTICS_VERIFICATION"


@pytest.mark.parametrize(("change", "reason"), [
    ({"coverage_scope": "SYMBOL_SCOPED"}, "FUTURES_ACCOUNT_WIDE_COVERAGE_REQUIRED"),
    ({"pagination_complete": False}, "FUTURES_PAGINATION_COMPLETENESS_UNPROVEN"),
    ({"pages_received": 1}, "FUTURES_PAGINATION_PAGE_COUNT_MISMATCH"),
    ({"http_method": "POST"}, "FUTURES_READ_ONLY_GET_REQUIRED"),
    ({"provider_request_id": ""}, "FUTURES_PROVIDER_REQUEST_ID_MISSING"),
])
def test_incomplete_or_non_read_only_evidence_blocks(change, reason):
    row = evidence()
    row.update(change)
    result = validate_account_wide_futures_coverage(row)
    assert result["coverage_state"] == "BLOCKED"
    assert result["coverage_block_reason"] == reason


def test_duplicate_position_ids_block():
    row = evidence()
    row["positions"][1]["position_id"] = row["positions"][0]["position_id"]
    assert validate_account_wide_futures_coverage(row)["coverage_block_reason"] == "FUTURES_POSITION_ID_DUPLICATE"


def test_missing_position_risk_blocks():
    row = evidence()
    del row["positions"][0]["allocated_risk_usdt"]
    assert validate_account_wide_futures_coverage(row)["coverage_block_reason"] == "FUTURES_POSITION_ALLOCATED_RISK_MISSING"


def test_no_io_or_execution_surface():
    result = validate_account_wide_futures_coverage(evidence())
    assert not {"submit_order", "cancel_order", "database_write", "network_call"} & result.keys()
