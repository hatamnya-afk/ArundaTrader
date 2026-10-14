import pytest

from authoritative_portfolio_risk_ledger_contract_v0_1 import (
    build_authoritative_portfolio_risk_ledger_observation,
)


def valid_ledger():
    return {
        "ledger_state": "AVAILABLE",
        "ledger_validation": "VALID",
        "ledger_id": "portfolio-ledger-001",
        "ledger_version": "v1",
        "ledger_source": "APPROVED_ACCOUNT_WIDE_PORTFOLIO_LEDGER",
        "account_scope": "TOOBIT:SPOT_AND_FUTURES:ACCOUNT",
        "coverage_scope": "ACCOUNT_WIDE",
        "asset_scope": "USDT",
        "observed_at": "2026-10-14T18:00:00Z",
        "provenance": "explicit authoritative ledger snapshot",
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
    }


def test_missing_authoritative_ledger_blocks_without_defaults():
    result = build_authoritative_portfolio_risk_ledger_observation(None)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "AUTHORITATIVE_ACCOUNT_WIDE_PORTFOLIO_RISK_LEDGER_REQUIRED"
    assert result["allocated_risk"] is None
    assert result["concurrent_positions"] is None
    assert result["portfolio_capital"] is None


def test_explicit_account_wide_ledger_is_normalized():
    result = build_authoritative_portfolio_risk_ledger_observation(valid_ledger())
    assert result["portfolio_state"] == "AVAILABLE"
    assert result["portfolio_validation"] == "VALID"
    assert result["coverage_scope"] == "ACCOUNT_WIDE"
    assert result["ledger_id"] == "portfolio-ledger-001"
    assert result["portfolio_capital"] == 10000.0
    assert result["usable_capital"] == 8000.0
    assert result["allocated_risk"] == 250.0
    assert result["concurrent_positions"] == 2


def test_symbol_scoped_provider_positions_are_not_an_account_wide_ledger():
    row = valid_ledger()
    row["coverage_scope"] = "SYMBOL_SCOPED"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_ACCOUNT_WIDE_COVERAGE_REQUIRED"


@pytest.mark.parametrize("field,reason", [
    ("ledger_id", "PORTFOLIO_LEDGER_ID_MISSING"),
    ("ledger_version", "PORTFOLIO_LEDGER_VERSION_MISSING"),
    ("ledger_source", "PORTFOLIO_LEDGER_SOURCE_MISSING"),
    ("account_scope", "PORTFOLIO_LEDGER_ACCOUNT_SCOPE_MISSING"),
    ("asset_scope", "PORTFOLIO_LEDGER_ASSET_SCOPE_MISSING"),
    ("observed_at", "PORTFOLIO_LEDGER_TIMESTAMP_MISSING"),
    ("provenance", "PORTFOLIO_LEDGER_PROVENANCE_MISSING"),
])
def test_missing_ledger_metadata_blocks(field, reason):
    row = valid_ledger()
    row[field] = ""
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == reason


def test_non_authoritative_source_and_invalid_risk_fields_block():
    row = valid_ledger()
    row["ledger_source"] = "TOOBIT_FUTURES_POSITIONS_GET"
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_SOURCE_INVALID"

    row = valid_ledger()
    row["allocated_risk"] = float("nan")
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_ALLOCATED_RISK_INVALID"


def test_usable_capital_cannot_exceed_portfolio_capital():
    row = valid_ledger()
    row["usable_capital"] = 10001
    result = build_authoritative_portfolio_risk_ledger_observation(row)
    assert result["portfolio_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "PORTFOLIO_LEDGER_USABLE_CAPITAL_INVALID"


def test_ledger_contract_has_no_execution_side_effect_surface():
    result = build_authoritative_portfolio_risk_ledger_observation(valid_ledger())
    forbidden = {
        "order_id", "api_request", "signature", "execution", "submitted",
        "trade_id", "withdrawal", "execution_authorization", "order_write",
    }
    assert forbidden.isdisjoint(result)
